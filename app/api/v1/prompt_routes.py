from flask import request, jsonify, Blueprint, current_app
from app.extensions import db
from app.models.prompt import Prompt
from app.services import prompt_service
from app.api.pagination import paginate_query, has_pagination_args
from app.api.swagger_helpers import with_pagination, with_example_file


prompts_bp = Blueprint("prompts", __name__)


@prompts_bp.route("/prompts", methods=["POST"])
@with_example_file("api/examples/prompt_example.json")
def create_prompt():
    """Create a new prompt.

    Accepts JSON: {name: str, content: str}
    """
    payload = request.get_json() or {}
    try:
        saved = prompt_service.save_prompt(name=payload.get("name"), content=payload.get("content"))
        return _serialize_prompt(saved), 201
    except ValueError as e:
        return _err(e, 400)
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(e)
        return _err(e, 500)


@prompts_bp.route("/prompts", methods=["GET"])
@with_pagination
def get_prompts():
    """List prompts. Returns legacy mapping when no pagination args provided."""
    try:
        args = request.args or {}

        # If the client did not provide any pagination-related params, keep old cached behavior
        if not has_pagination_args(args):
            # legacy behavior: return raw mapping filename->content
            # Use ensure_ascii=False so Unicode characters are not escaped.
            import json as _json
            data = prompt_service.get_all_prompts()
            fmt = (args.get("format") or "array").lower()
            if fmt == "map":
                return current_app.response_class(
                    _json.dumps(data, ensure_ascii=False), mimetype="application/json"
                )
            # default: array (REST-friendly) — include id, name, content
            # Build from DB so we include the primary key id
            prompts_from_db = Prompt.query.order_by(Prompt.name).all()
            arr = [{"id": p.id, "name": p.name, "content": p.content} for p in prompts_from_db]
            return current_app.response_class(
                _json.dumps(arr, ensure_ascii=False), mimetype="application/json"
            )

        # Build base query and use the shared paginate helper
        base_q = Prompt.query

        def _serialize(p: "Prompt"):
            if hasattr(p, "to_dict"):
                return p.to_dict()
            return {"id": p.id, "name": p.name, "content": p.content}

        result = paginate_query(
            base_q,
            Prompt,
            args,
            serialize=_serialize,
            allowed_sort_fields=("id", "name"),
            default_sort="name",
        )
        return _ok(result)
    except Exception as e:
        current_app.logger.exception(e)
        return _err(e, 500)


@prompts_bp.route("/prompts/<int:prompt_id>", methods=["PUT"])
@with_example_file("api/examples/prompt_example.json")
def update_prompt(prompt_id):
    payload = request.get_json() or {}
    try:
        updated = prompt_service.update_prompt_by_id(prompt_id, payload.get("name"), payload.get("content"))
        if not updated:
            return _err("Prompt not found", 404)
        return _ok({"id": updated.id, "name": updated.name, "content": updated.content})
    except ValueError as e:
        return _err(e, 400)
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(e)
        return _err(e, 500)


@prompts_bp.route("/prompts/<int:prompt_id>", methods=["GET"])
def get_prompt(prompt_id):
    try:
        prompt = prompt_service.get_prompt_by_id(prompt_id)
        if not prompt:
            return _err("Prompt not found", 404)
        return _ok(prompt)
    except Exception as e:
        current_app.logger.exception(e)
        return _err(e, 500)


@prompts_bp.route("/prompts/<int:prompt_id>", methods=["DELETE"])
def delete_prompt(prompt_id):
    try:
        res = prompt_service.delete_prompt_by_id(prompt_id)
        # Service may return a Flask response tuple (response, status) or a Response
        # object when the item isn't found; detect and forward it directly.
        if isinstance(res, tuple):
            return res
        if hasattr(res, "status_code"):
            return res
        if isinstance(res, dict) and res.get("id"):
            deleted_id = res["id"]
        elif isinstance(res, int):
            deleted_id = res
        elif res is True:
            deleted_id = prompt_id
        else:
            deleted_id = prompt_id
        return _ok({"id": deleted_id})
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(e)
        return _err(e, 500)


def _ok(data, status=200):
    return jsonify({"code": 0, "data": data}), status


def _err(msg, status=400):
    return jsonify({"code": 1, "error": str(msg)}), status


def _serialize_prompt(p: "Prompt"):
    return {"id": p.id, "name": p.name, "content": p.content}


# Backwards-compatible alias used by older clients/tests
@prompts_bp.route("/save_prompt", methods=["POST"])
def save_prompt_alias():
    payload = request.get_json() or {}
    try:
        saved = prompt_service.save_prompt(name=payload.get("name"), content=payload.get("content"))
        return jsonify({"ok": True, "id": saved.id})
    except ValueError as e:
        return _err(e, 400)
    except Exception as e:
        return _err(e, 500)
    
