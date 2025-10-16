import os
from pathlib import Path
import structlog
from flask import Blueprint, jsonify, abort

from app.extensions import db
from app.models.script import Script
from app.settings import settings
from app.utils import get_project_path

video_maker_bp = Blueprint('video_maker', __name__)
log = structlog.get_logger()

@video_maker_bp.route('/scripts/<int:script_id>/prepare-folder', methods=['POST'])
def prepare_script_folder(script_id):
    """
    Creates the project directory structure for a given script.
    ---
    tags:
      - Video Maker
    parameters:
      - name: script_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Folder structure created successfully.
        schema:
          type: object
          properties:
            message:
              type: string
            path:
              type: string
    """
    script = db.session.get(Script, script_id)
    if not script:
        return jsonify({"error": "Script not found"}), 404

    try:
        project_path = get_project_path(script.script_data)
        project_path.mkdir(parents=True, exist_ok=True)
        log.info("folder.prepared", script_id=script_id, path=str(project_path))
        return jsonify({"message": "Project folder created successfully", "path": str(project_path)})
    except Exception as e:
        log.error("folder.prepare.failed", script_id=script_id, error=str(e))
        return jsonify({"error": f"Failed to create project folder: {e}"}), 500

@video_maker_bp.route('/projects', defaults={'subpath': ''})
@video_maker_bp.route('/projects/<path:subpath>')
def list_project_files(subpath):
    """
    Lists files and directories within the main projects folder.
    ---
    tags:
      - Video Maker
    parameters:
      - name: subpath
        in: path
        type: string
        required: false
        description: The sub-path within the main project folder.
    responses:
      200:
        description: A list of files and directories.
    """
    projects_root = Path(settings.PROJECT_FOLDER)
    target_path = (projects_root / subpath).resolve()

    # Security check: Ensure the target path is within the projects_root
    if not target_path.is_relative_to(projects_root.resolve()):
        abort(403, "Access forbidden: Path is outside the project directory.")

    if not target_path.exists():
        return jsonify({"error": "Path not found"}), 404

    items = []
    for item in sorted(target_path.iterdir()):
        items.append({
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
            "path": str(item.relative_to(projects_root))
        })
    
    return jsonify(items)