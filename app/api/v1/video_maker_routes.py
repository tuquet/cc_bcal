import os
import subprocess
import shutil
from pathlib import Path

import structlog
from flask import Blueprint, jsonify, abort, current_app

from app.extensions import db
from app.models.script import Script
from app.settings import settings
from app.utils import get_project_path


video_maker_bp = Blueprint('video_maker', __name__)
log = structlog.get_logger()


@video_maker_bp.route('/scripts/<int:script_id>/prepare-folder', methods=['POST'])
def prepare_script_folder(script_id):
    """Create the project directory structure for a given script.

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
        # Ensure we pass a Path for root_dir to avoid .parent on a string
        root_dir = Path(current_app.root_path).parent
        project_path = Path(get_project_path(script.script_data, root_dir)).resolve()

        # Create the project directory structure
        project_path.mkdir(parents=True, exist_ok=True)

        # Mark the script as having a prepared folder and persist to DB
        try:
            script.has_folder = True
            db.session.add(script)
            db.session.commit()
        except Exception as db_e:
            # If DB commit fails, roll back but we still return success for folder creation
            db.session.rollback()
            log.error("folder.mark_has_folder.failed", script_id=script_id, error=str(db_e))

        # Try to refresh the script from the session so we can return updated values
        try:
            db.session.refresh(script)
        except Exception:
            try:
                script = db.session.get(Script, script_id)
            except Exception:
                script = None

        response_payload = {"message": "Project folder created successfully", "path": str(project_path)}
        if script:
            try:
                response_payload["script"] = script.to_dict()
            except Exception:
                # ignore serialization issues and still return path
                pass

        log.info("folder.prepared", script_id=script_id, path=str(project_path))
        return jsonify(response_payload)
    except Exception as e:
        log.error("folder.prepare.failed", script_id=script_id, error=str(e))
        return jsonify({"error": f"Failed to create project folder: {e}"}), 500


@video_maker_bp.route('/scripts/<int:script_id>/open-folder', methods=['POST'])
def open_script_folder(script_id):
    """Attempt to open the project folder for a given script on the server host.

    NOTE: This opens the folder on the server where the backend runs. Browsers cannot
    open arbitrary server-side file:// paths, so this route is intended for trusted
    server environments (e.g., local development or an admin machine).

    Security: the resolved path is validated to be inside settings.PROJECT_FOLDER.

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
        description: Folder opened successfully (or command executed)
      404:
        description: Script or folder not found
      403:
        description: Forbidden (path outside project root)
      500:
        description: Error running open command
    """
    script = db.session.get(Script, script_id)
    if not script:
        return jsonify({"error": "Script not found"}), 404

    try:
        root_dir = Path(current_app.root_path).parent
        project_path = Path(get_project_path(script.script_data, root_dir)).resolve()
    except Exception as e:
        log.error("folder.resolve.failed", script_id=script_id, error=str(e))
        return jsonify({"error": "Failed to resolve project path"}), 500

    projects_root = Path(settings.PROJECT_FOLDER).resolve()
    if not project_path.exists():
        return jsonify({"error": "Project path not found"}), 404

    # Ensure the resolved project_path is inside the configured projects root
    try:
        if not project_path.is_relative_to(projects_root):
            log.warning("folder.open.forbidden", script_id=script_id, path=str(project_path))
            return jsonify({"error": "Access forbidden: Path is outside the project directory."}), 403
    except AttributeError:
        # Fallback for older Python where is_relative_to may not exist
        try:
            project_path.relative_to(projects_root)
        except Exception:
            log.warning("folder.open.forbidden", script_id=script_id, path=str(project_path))
            return jsonify({"error": "Access forbidden: Path is outside the project directory."}), 403

    try:
        if os.name == 'nt':
            # Windows
            os.startfile(str(project_path))
        else:
            opener = shutil.which('xdg-open') or shutil.which('open')
            if opener:
                subprocess.Popen([opener, str(project_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                log.info("folder.open.noop", script_id=script_id, path=str(project_path))
                return jsonify({"message": "Project path exists but no opener is available on server.", "path": str(project_path)})

        log.info("folder.opened", script_id=script_id, path=str(project_path))
        return jsonify({"message": "Project folder open command executed", "path": str(project_path)})
    except Exception as e:
        log.error("folder.open.failed", script_id=script_id, error=str(e))
        return jsonify({"error": f"Failed to open project folder: {e}"}), 500


    @video_maker_bp.route('/scripts/<int:script_id>/project-path', methods=['GET'])
    def get_script_project_path(script_id):
        """Return the computed project path for a script and whether it exists on disk.

        Security: ensure the resolved path is inside settings.PROJECT_FOLDER.
        """
        script = db.session.get(Script, script_id)
        if not script:
            return jsonify({"error": "Script not found"}), 404

        try:
            root_dir = Path(current_app.root_path).parent
            project_path = Path(get_project_path(script.script_data, root_dir)).resolve()
        except Exception as e:
            log.error("project_path.resolve.failed", script_id=script_id, error=str(e))
            return jsonify({"error": "Failed to resolve project path"}), 500

        projects_root = Path(settings.PROJECT_FOLDER).resolve()
        try:
            if not project_path.is_relative_to(projects_root):
                log.warning("project_path.forbidden", script_id=script_id, path=str(project_path))
                return jsonify({"error": "Access forbidden: Path is outside the project directory."}), 403
        except AttributeError:
            try:
                project_path.relative_to(projects_root)
            except Exception:
                log.warning("project_path.forbidden", script_id=script_id, path=str(project_path))
                return jsonify({"error": "Access forbidden: Path is outside the project directory."}), 403

        exists = project_path.exists()
        return jsonify({"path": str(project_path), "exists": exists})


@video_maker_bp.route('/projects', defaults={'subpath': ''})
@video_maker_bp.route('/projects/<path:subpath>')
def list_project_files(subpath):
    """List files and directories within the main projects folder.

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
    projects_root = Path(settings.PROJECT_FOLDER).resolve()
    target_path = (projects_root / subpath).resolve()

    # Prevent path traversal outside projects_root
    try:
        if not target_path.is_relative_to(projects_root):
            abort(403, "Access forbidden: Path is outside the project directory.")
    except AttributeError:
        try:
            target_path.relative_to(projects_root)
        except Exception:
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