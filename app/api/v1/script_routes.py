from flask import request, jsonify, Blueprint, current_app
from app.services.script_service import (
    create_script,
    list_scripts,
    get_script_by_id,
    update_script,
    delete_script,
    NotFoundError,
    ConflictError,
    BadRequestError,
)
from app.api.swagger_helpers import with_pagination, with_example_file
import json
import os
import subprocess
import shutil
from pathlib import Path

import structlog
from flask import abort

from app.extensions import db
from app.models.script import Script
from app.settings import settings
from app.services.script_service import (
    compute_project_path_for_script,
    prepare_project_folder,
    open_project_folder,
    get_project_path_info,
)

log = structlog.get_logger()
scripts_bp = Blueprint("scripts", __name__)

@scripts_bp.route("/scripts", methods=["POST"])
@with_example_file("api/examples/script_example.json")
def create_script_api():
    """Create a new script.

    ---
    tags:
      - Scripts
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            alias:
              type: string
              description: Unique short identifier for the script
            title:
              type: string
            genre:
              type: string
            logline:
              type: string
            setting:
              type: object
              properties:
                time:
                  type: string
                location:
                  type: string
            characters:
              type: array
              items:
                type: object
                properties:
                  name:
                    type: string
                  role:
                    type: string
                  description:
                    type: string
            acts:
              type: array
              items:
                type: object
                properties:
                  act_number:
                    type: integer
                  summary:
                    type: string
                  scenes:
                    type: array
                    items:
                      type: object
                      properties:
                        scene_number:
                          type: integer
                        location:
                          type: string
                        time:
                          type: string
                        action:
                          type: string
                        dialogues:
                          type: array
                          items:
                            type: object
                            properties:
                              character:
                                type: string
                              line:
                                type: string
            themes:
              type: array
              items:
                type: string
            tone:
              type: string
            notes:
              type: string
          # example is loaded from external JSON file via @with_example_file
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              alias:
                type: string
              title:
                type: string
              genre:
                type: string
              logline:
                type: string
              setting:
                type: object
                properties:
                  time:
                    type: string
                  location:
                    type: string
              characters:
                type: array
                items:
                  type: object
                  properties:
                    name:
                      type: string
                    role:
                      type: string
                    description:
                      type: string
              acts:
                type: array
                items:
                  type: object
                  properties:
                    act_number:
                      type: integer
                    summary:
                      type: string
                    scenes:
                      type: array
                      items:
                        type: object
                        properties:
                          scene_number:
                            type: integer
                          location:
                            type: string
                          time:
                            type: string
                          action:
                            type: string
                          dialogues:
                            type: array
                            items:
                              type: object
                              properties:
                                character:
                                  type: string
                                line:
                                  type: string
              themes:
                type: array
                items:
                  type: string
              tone:
                type: string
              notes:
                type: string
          # example loaded from external JSON file via @with_example_file
    responses:
      201:
        description: Script created
      400:
        description: Bad request
      409:
        description: Conflict
    """

    data = request.get_json() or {}

    # Ensure the client sent a JSON object
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    try:
        script = create_script(data)
        return jsonify(script.to_dict()), 201
    except BadRequestError as e:
        return jsonify({"error": str(e)}), 400
    except ConflictError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        current_app.logger.error(f"Failed to create script: {e}")
        return jsonify({"error": str(e)}), 500

@scripts_bp.route("/scripts", methods=["GET"])
@with_pagination
def get_scripts_api():
    """Get all scripts.
    Supports optional pagination via query parameters: page/pageSize, sortBy, sortOrder.

    ---
    tags:
      - Scripts
    parameters:
      - in: query
        name: include_narration
        schema:
          type: boolean
        description: Include full narration text in output
    responses:
      200:
        description: A list of scripts with optional pagination.
    """

    # If no pagination args were provided, return the simple list form expected by tests
    from app.api.pagination import has_pagination_args

    if not has_pagination_args(request.args):
        # return list of scripts (serialize each)
        scripts_q = Script.query.order_by(Script.updated_at.desc()).all()
        scripts = [s.to_dict() for s in scripts_q]
        return jsonify(scripts)

    # For paginated responses we do not include narration by default.
    resp = list_scripts(request.args, False)
    return jsonify(resp)

@scripts_bp.route("/scripts/<int:script_id>", methods=["GET"])
def get_script_api(script_id):
    """Get a script by id.

    ---
    tags:
      - Scripts
    responses:
      200:
        description: Script found
      404:
        description: Script not found
    """

    try:
        script = get_script_by_id(script_id)
    except NotFoundError:
        return jsonify({"error": "Script not found"}), 404

    data = script.to_dict()
    return jsonify(data)

@scripts_bp.route("/scripts/<int:script_id>", methods=["PUT"])
def update_script_api(script_id):
    """Update a script.

    ---
    tags:
      - Scripts
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
    responses:
      200:
        description: Script updated
      400:
        description: Bad request
      404:
        description: Script not found
    """

    data = request.get_json() or {}
    if not data:
        return jsonify({"error": "No data provided."}), 400

    try:
        script = update_script(script_id, data)
        return jsonify(script.to_dict())
    except NotFoundError:
        return jsonify({"error": "Script not found"}), 404
    except ConflictError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        current_app.logger.error(f"Failed to update script: {e}")
        return jsonify({"error": str(e)}), 500


@scripts_bp.route("/scripts/<int:script_id>", methods=["DELETE"])
def delete_script_api(script_id):
    """Delete a script.

    ---
    tags:
      - Scripts
    responses:
      200:
        description: Deleted
      404:
        description: Not found
    """

    try:
        delete_script(script_id)
        return jsonify({"message": "Script deleted successfully."})
    except NotFoundError:
        return jsonify({"error": "Script not found"}), 404
    except Exception as e:
        current_app.logger.error(f"Failed to delete script: {e}")
        return jsonify({"error": str(e)}), 500


@scripts_bp.route("/scripts/<int:script_id>/full-text", methods=["GET"])
def get_script_full_text(script_id):
    """Return the script full narration as labeled plain text.
    ---
    tags:
      - Scripts
    """

    try:
        script = get_script_by_id(script_id)
    except NotFoundError:
        return jsonify({"error": "Script not found"}), 404

    try:
        # Try to parse acts (may be stored as JSON string)
        acts_raw = script.acts
        try:
            acts = (
                json.loads(acts_raw)
                if isinstance(acts_raw, str) and acts_raw.strip()
                else (acts_raw or [])
            )
        except Exception:
            acts = []

        # Parse characters for possible lookups
        characters_raw = script.characters
        try:
            characters = (
                json.loads(characters_raw)
                if isinstance(characters_raw, str) and characters_raw.strip()
                else (characters_raw or [])
            )
        except Exception:
            characters = []

        # Build character lookup so we can prefer character.role when labeling
        char_lookup: dict = {}
        if isinstance(characters, list):
            for c in characters:
                try:
                    cid = c.get("id")
                except Exception:
                    cid = None
                if cid is not None:
                    char_lookup[str(cid)] = c
                if isinstance(c.get("name"), str) and c.get("name").strip():
                    char_lookup[c.get("name")] = c
                if isinstance(c.get("alias"), str) and c.get("alias").strip():
                    char_lookup[c.get("alias")] = c
                if isinstance(c.get("role"), str) and c.get("role").strip():
                    # also index by role in case dialogues reference role
                    char_lookup[c.get("role")] = c

        # Build mapping to ensure consistent Speaker N labels for unknown keys
        speaker_map: dict = {}
        next_speaker = 1

        def label_for(key):
            nonlocal next_speaker
            # If key is an object that looks like a character, extract id/name/role
            if isinstance(key, dict):
                if key.get("role"):
                    return key.get("role")
                if key.get("name"):
                    return key.get("name")
                if key.get("alias"):
                    return key.get("alias")
                key = key.get("id") or None

            if key is None:
                k = "__unknown__"
            else:
                k = str(key)

            # Prefer character role/name/alias when available
            if k in char_lookup:
                ch = char_lookup[k]
                return (
                    ch.get("role")
                    or ch.get("name")
                    or ch.get("alias")
                    or f"Speaker {next_speaker}"
                )

            if k in speaker_map:
                return speaker_map[k]

            label = f"Speaker {next_speaker}"
            speaker_map[k] = label
            next_speaker += 1
            return label

        lines = []
        if isinstance(acts, list) and len(acts) > 0:
            for act in acts:
                for scene in act.get("scenes") or []:
                    for dlg in scene.get("dialogues") or []:
                        # dialogue content may be under 'line' or 'text' or 'content'
                        content = (
                            dlg.get("line")
                            or dlg.get("text")
                            or dlg.get("content")
                            or ""
                        )
                        if not content or not str(content).strip():
                            continue
                        speaker_key = (
                            dlg.get("character")
                            or dlg.get("speaker")
                            or dlg.get("role")
                        )
                        label = label_for(speaker_key)
                        lines.append(f"{label}: {str(content).strip()}")

        # Fallback to model full_text when no structured acts present
        if not lines:
            fallback = script.full_text or ""
            if fallback and str(fallback).strip():
                # return fallback as-is
                return (
                    str(fallback),
                    200,
                    {"Content-Type": "text/plain; charset=utf-8"},
                )

        text = "\n\n".join(lines)
        return (text, 200, {"Content-Type": "text/plain; charset=utf-8"})
    except Exception as e:
        current_app.logger.error(
            f"Failed to generate full text for script {script_id}: {e}"
        )
        return jsonify({"error": "Failed to generate full text"}), 500


@scripts_bp.route("/scripts/<int:script_id>/prepare-folder", methods=["POST"])
def prepare_script_folder(script_id):
    """
    Create the project directory structure for a given script.
    ---
    tags:
      - Scripts
    """
    try:
        result = prepare_project_folder(script_id, Path(current_app.root_path).parent)
        resp = {
            "message": "Project folder created successfully",
            "path": result["path"],
        }
        if result.get("script"):
            try:
                resp["script"] = result["script"].to_dict()
            except Exception:
                pass
        return jsonify(resp)
    except NotFoundError:
        return jsonify({"error": "Script not found"}), 404
    except Exception as e:
        log.error("folder.prepare.failed", script_id=script_id, error=str(e))
        return jsonify({"error": f"Failed to create project folder: {e}"}), 500


@scripts_bp.route("/scripts/<int:script_id>/open-folder", methods=["POST"])
def open_script_folder(script_id):
    """Attempt to open the project folder for a given script on the server host.
    ---
    tags:
      - Scripts
    """
    script = db.session.get(Script, script_id)
    if not script:
        return jsonify({"error": "Script not found"}), 404

    try:
        result = open_project_folder(script_id, Path(current_app.root_path).parent)
        return jsonify(result)
    except NotFoundError:
        return jsonify({"error": "Script not found"}), 404
    except PermissionError:
        return (
            jsonify(
                {"error": "Access forbidden: Path is outside the project directory."}
            ),
            403,
        )
    except FileNotFoundError:
        return jsonify({"error": "Project path not found"}), 404
    except Exception as e:
        log.error("folder.open.failed", script_id=script_id, error=str(e))
        return jsonify({"error": f"Failed to open project folder: {e}"}), 500

@scripts_bp.route("/scripts/<int:script_id>/project-path", methods=["GET"])
def get_script_project_path(script_id):
    """Return the computed project path for a script and whether it exists on disk.
    ---
    tags:
      - Scripts
    """
    script = db.session.get(Script, script_id)
    if not script:
        return jsonify({"error": "Script not found"}), 404

    try:
        info = get_project_path_info(script_id, Path(current_app.root_path).parent)
        return jsonify(info)
    except NotFoundError:
        return jsonify({"error": "Script not found"}), 404
    except PermissionError:
        return (
            jsonify(
                {"error": "Access forbidden: Path is outside the project directory."}
            ),
            403,
        )
    except Exception as e:
        log.error("project_path.resolve.failed", script_id=script_id, error=str(e))
        return jsonify({"error": "Failed to resolve project path"}), 500
