from flask import request, jsonify, Blueprint, current_app
from app.extensions import db
from app.models.prompt import Prompt
from app.services import prompt_service

prompts_bp = Blueprint("prompts", __name__)


def _ok(data, status=200):
    return jsonify({"code": 0, "data": data}), status


def _err(msg, status=400):
    return jsonify({"code": 1, "error": str(msg)}), status

def _serialize_prompt(p: "Prompt"):
    return {
        "id": p.id,
        "name": p.name,
        "content": p.content,
    }


@prompts_bp.route("/prompts", methods=["GET"])
def api_get_prompts():
    try:
        return _ok(prompt_service.get_all_prompts())
    except Exception as e:
        current_app.logger.exception(e)
        return _err(e, 500)


@prompts_bp.route("/prompts", methods=["POST"])
def api_save_prompt():
    payload = request.get_json() or {}
    try:
        saved = prompt_service.save_prompt(
            name=payload.get("name"), content=payload.get("content")
        )
        return _serialize_prompt(saved), 201
    except ValueError as e:
        return _err(e, 400)
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(e)
        return _err(e, 500)


@prompts_bp.route("/prompts/<int:prompt_id>", methods=["PUT"])
def api_update_prompt(prompt_id):
    payload = request.get_json() or {}
    try:
        updated = prompt_service.update_prompt_by_id(
            prompt_id, payload.get("name"), payload.get("content")
        )
        if not updated:
            return _err("Prompt not found", 404)
        return _ok({"id": updated.id, "name": updated.name, "content": updated.content})
    except ValueError as e:
        return _err(e, 400)
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(e)
        return _err(e, 500)


@prompts_bp.route("/prompts/<int:prompt_id>", methods=["DELETE"])
def api_delete_prompt(prompt_id):
    try:
        res = prompt_service.delete_prompt_by_id(prompt_id)
        # handle various service return shapes (id, dict with id, True, or a Flask response)
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