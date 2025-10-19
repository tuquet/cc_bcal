"""Helpers to reduce repetitive Flasgger/Swagger doc declarations.

Provides a small decorator to mark view functions that should get
common swagger extras injected automatically (for example pagination
query-parameters). An `apply_swagger_extras(app)` function will mutate
the view function __doc__ before Flasgger builds the spec.
"""
from typing import Callable
from collections import OrderedDict
import textwrap
import yaml
import json
import os
from pathlib import Path


PAGINATION_YAML = """
parameters:
  - in: query
    name: page
    schema:
      type: integer
    description: Page number (1-based)
  - in: query
    name: pageSize
    schema:
      type: integer
    description: Number of items per page
  - in: query
    name: sortBy
    schema:
      type: string
    description: Field to sort by
  - in: query
    name: sortOrder
    schema:
      type: string
    description: Sort order (asc|desc)
"""


def with_pagination(func: Callable) -> Callable:
    """Decorator to mark a view function as supporting pagination.

    The decorator simply sets an attribute on the function object. The
    `apply_swagger_extras` helper should be run (once) after all
    blueprints are registered and before Flasgger is initialized so the
    docstrings are updated in-place.
    """

    setattr(func, "__add_pagination__", True)
    return func


def with_example_file(path: str):
    """Decorator to attach an external example file path to a view function.

    The path may be absolute or relative to the Flask app root. When
    `apply_swagger_extras` runs it will load the JSON and inject it into
    the operation's requestBody (and legacy body parameter if present).
    """

    def _decorator(func: Callable) -> Callable:
        setattr(func, "__swagger_example_file__", path)
        return func

    return _decorator


def apply_swagger_extras(app):
    """Scan registered view functions and inject pagination YAML for
    those marked with `__add_pagination__`.

    This mutates the function __doc__ by appending the YAML block.
    Keep the mutation idempotent by checking for a marker string.
    """

    marker = "# __pagination_injected__"

    def _get_attr_from_wrapped(obj, name):
        """Try to find attribute `name` on obj or on its __wrapped__ chain."""
        cur = obj
        for _ in range(10):
            if cur is None:
                return None
            if hasattr(cur, name):
                return getattr(cur, name)
            cur = getattr(cur, "__wrapped__", None)
        return None

    for endpoint, view in list(app.view_functions.items()):
        # skip flask internals
        if endpoint.startswith("static"):
            continue

        fn = view

        # view can be a function or a wrapper; check attributes on it
        try:
            doc = fn.__doc__ or ""

            if marker in doc:
                # already injected
                continue

            # load external example if provided (support decorated/wrapped functions)
            example_file = _get_attr_from_wrapped(fn, "__swagger_example_file__")
            example_obj = None
            if example_file:
                p = Path(example_file)
                candidate_paths = []
                # if absolute, try it directly
                if p.is_absolute():
                    candidate_paths.append(p)
                else:
                    # common candidates: relative to Flask app root, project root (parent), or app/api/examples
                    candidate_paths.append(Path(app.root_path) / example_file)
                    candidate_paths.append(Path(app.root_path).parent / example_file)
                    # fallback: try app root + 'api/examples/<name>' if user passed just filename or subpath
                    candidate_paths.append(Path(app.root_path) / "api" / "examples" / p.name)

                loaded = False
                for cand in candidate_paths:
                    try:
                        if not cand.exists():
                            continue
                        with open(cand, "r", encoding="utf-8") as fh:
                            example_obj = json.load(fh)
                        loaded = True
                        break
                    except Exception:
                        # try next candidate
                        continue

                if not loaded:
                    # Log once that we couldn't find the example file so developer can adjust path
                    try:
                        app.logger.debug(
                            "swagger_helpers: example file not found",
                            extra={"requested": example_file, "candidates": [str(x) for x in candidate_paths]},
                        )
                    except Exception:
                        pass

            has_pagination = bool(_get_attr_from_wrapped(fn, "__add_pagination__"))

            # default existing parts
            pre = doc
            existing_yaml = {}

            if "---" in doc:
                sep = doc.find("---")
                pre = doc[:sep]
                yaml_part = doc[sep + 4 :]
                yaml_part = textwrap.dedent(yaml_part)
                try:
                    existing_yaml = yaml.safe_load(yaml_part) or {}
                except Exception:
                    # If existing YAML fails to parse, keep it as plain text under a
                    # fallback `_raw` key to avoid breaking YAML merging.
                    existing_yaml = {"_raw": yaml_part}

            # Start building final mapping to dump as YAML
            final = dict(existing_yaml) if isinstance(existing_yaml, dict) else {}

            # Merge pagination parameters if required
            if has_pagination:
                pag_dict = yaml.safe_load(PAGINATION_YAML) or {}
                pag_params = pag_dict.get("parameters", [])
                existing_params = final.get("parameters", [])

                # merge while avoiding duplicates (by (in,name))
                seen = set()
                merged = []
                for p in pag_params + existing_params:
                    key = (p.get("in"), p.get("name"))
                    if key in seen:
                        continue
                    seen.add(key)
                    merged.append(p)

                if merged:
                    final["parameters"] = merged

            # Inject example into requestBody (prefer existing requestBody)
            if example_obj is not None:
                rb = final.get("requestBody", {})
                content = rb.get("content", {})
                app_json = content.get("application/json", {})
                app_json["example"] = example_obj
                content["application/json"] = app_json
                rb["content"] = content
                rb.setdefault("required", True)
                final["requestBody"] = rb

                # Also inject example into Swagger 2.0 style 'parameters' body schema
                # so older Flasgger/Swagger UI builds will show the example in the Try-it-out editor.
                params = final.get("parameters", []) or []
                body_param = None
                for pp in params:
                    if pp.get("in") == "body":
                        body_param = pp
                        break

                # determine schema source (prefer existing body param schema, else requestBody schema)
                schema_src = None
                if body_param is not None:
                    schema_src = body_param.get("schema", {})
                else:
                    # try to extract schema from requestBody.application/json.schema
                    try:
                        schema_src = rb.get("content", {}).get("application/json", {}).get("schema")
                    except Exception:
                        schema_src = None

                if schema_src is None:
                    schema_src = {"type": "object"}

                # attach example to schema source
                try:
                    schema_src["example"] = example_obj
                except Exception:
                    pass

                # if we had a body parameter, update it; otherwise create one
                if body_param is not None:
                    body_param["schema"] = schema_src
                else:
                    new_body_param = {
                        "in": "body",
                        "name": "body",
                        "required": True,
                        "schema": schema_src,
                    }
                    params.append(new_body_param)
                    final["parameters"] = params

            # If we had no YAML and neither pagination nor example, skip mutation
            if not (has_pagination or example_obj or ("---" in doc)):
                continue

            dumped = yaml.safe_dump(final, sort_keys=False)
            fn.__doc__ = pre.rstrip() + "\n\n---\n" + marker + "\n" + dumped

        except Exception:
            # be defensive: don't break app startup if anything goes wrong
            continue
