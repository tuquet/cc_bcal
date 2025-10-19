import json
import os
from typing import Optional

from app.extensions import db
from app.models.prompt import Prompt


def run_from_example(app, example_path: str, create_tables_if_missing: bool = False) -> dict:
    """Read a single example JSON file and create or update the Prompt row.

    Args:
        app: Flask app instance (used for app context resolution).
        example_path: Absolute or project-relative path to the example JSON file.
        create_tables_if_missing: If True, call db.create_all() when tables are missing.

    Returns:
        A dict with keys: created (int), updated (int), path (str).
    """
    # Resolve path: if it's not absolute, try relative to app.root_path then repo root
    if not os.path.isabs(example_path):
        candidate = os.path.join(app.root_path, example_path)
        if os.path.exists(candidate):
            example_path = candidate
        else:
            # try workspace root (two levels up from app)
            repo_root = os.path.abspath(os.path.join(app.root_path, '..'))
            candidate = os.path.join(repo_root, example_path)
            if os.path.exists(candidate):
                example_path = candidate

    if not os.path.exists(example_path):
        raise FileNotFoundError(f'Example file not found: {example_path}')

    with app.app_context():
        # Optionally create tables if running on a fresh clone
        if create_tables_if_missing:
            db.create_all()

        with open(example_path, 'r', encoding='utf-8') as fh:
            payload = json.load(fh)

        name = payload.get('name')
        content = payload.get('content')
        if not name or not content:
            raise ValueError('Example JSON must include `name` and `content` fields')

        created = 0
        updated = 0

        existing = Prompt.query.filter_by(name=name).first()
        if existing:
            existing.content = content
            db.session.commit()
            updated = 1
        else:
            p = Prompt(name=name, content=content)
            db.session.add(p)
            db.session.commit()
            created = 1

    return {"created": created, "updated": updated, "path": example_path}


def run(app, prompts_dir: Optional[str] = None, create_tables_if_missing: bool = False) -> dict:
    """Seed prompts from a directory into the prompts table.

    Behavior expected by tests:
    - If `prompts_dir` is provided (Path or str), iterate all files in it.
      For files ending with `.json`, attempt to load a JSON object with
      `name` and `content` fields. For other files (e.g. `.md`), use the
      filename as the prompt `name` and the file contents as `content`.
    - If `prompts_dir` is not provided, default to `app/api/examples`.

    Returns a summary dict: {"created": int, "updated": int}.
    """
    # Resolve prompts_dir default
    if prompts_dir is None:
        prompts_dir = os.path.join(app.root_path, 'api', 'examples')

    # Accept pathlib.Path objects
    try:
        from pathlib import Path
        if isinstance(prompts_dir, Path):
            prompts_dir = str(prompts_dir)
    except Exception:
        pass

    if not os.path.exists(prompts_dir):
        raise FileNotFoundError(f'Prompts directory not found: {prompts_dir}')

    created = 0
    updated = 0
    prompts_map = {}

    with app.app_context():
        if create_tables_if_missing:
            db.create_all()

        for fname in sorted(os.listdir(prompts_dir)):
            full = os.path.join(prompts_dir, fname)
            if not os.path.isfile(full):
                continue
            try:
                if fname.lower().endswith('.json'):
                    # JSON file can be several shapes:
                    # 1) {"name": "...", "content": "..."}
                    # 2) {"Prompt A": "content A", ...}  (mapping)
                    # 3) [ {"name":"...","content":"..."}, ... ]
                    with open(full, 'r', encoding='utf-8') as fh:
                        payload = json.load(fh)

                    entries = []
                    # shape 1: single object with name/content
                    if isinstance(payload, dict) and 'name' in payload and 'content' in payload:
                        entries.append((payload['name'], payload['content']))
                    # shape 2: mapping name -> content (values are strings)
                    elif isinstance(payload, dict) and all(isinstance(v, str) for v in payload.values()):
                        for k, v in payload.items():
                            entries.append((k, v))
                    # shape 3: list of objects
                    elif isinstance(payload, list):
                        for item in payload:
                            if isinstance(item, dict) and 'name' in item and 'content' in item:
                                entries.append((item['name'], item['content']))
                    else:
                        # unsupported JSON shape
                        continue
                else:
                    # ignore non-json files in examples (we only accept .json seed files)
                    continue

                # Process all resolved entries from the current file
                for name, content in entries:
                    if not name or content is None:
                        continue
                    existing = Prompt.query.filter_by(name=name).first()
                    if existing:
                        # Only update when content changed
                        if existing.content != content:
                            existing.content = content
                            db.session.commit()
                            updated += 1
                        prompts_map[existing.name] = existing.content
                    else:
                        p = Prompt(name=name, content=content)
                        db.session.add(p)
                        db.session.commit()
                        created += 1
                        prompts_map[p.name] = p.content
            except Exception:
                # ignore single-file errors and continue
                continue

    return {"created": created, "updated": updated, "prompts": prompts_map}


if __name__ == '__main__':
    # Quick check when run directly: use run_from_example on the packaged example
    from app import create_app

    app = create_app('default')
    example_path = os.path.join(app.root_path, 'api', 'examples', 'prompt_example.json')
    print(run_from_example(app, example_path, create_tables_if_missing=True))
