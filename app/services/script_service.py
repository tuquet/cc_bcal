import json
from typing import Any
from app.extensions import db
from app.models.script import Script
from app.api.pagination import paginate_query
from pathlib import Path
import os
import subprocess
import shutil
import structlog
from flask import current_app
from app.settings import settings
from app.utils import get_project_path

log = structlog.get_logger()


class ServiceError(Exception):
    pass


class NotFoundError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


class BadRequestError(ServiceError):
    pass


def create_script(data: dict) -> Script:
    meta = data.get('meta') or {}
    alias = meta.get('alias') or data.get('alias')
    title = meta.get('title') or data.get('title')

    if not alias:
        raise BadRequestError("'alias' is required (in meta.alias or top-level alias)")

    if Script.query.filter_by(alias=alias).first():
        raise ConflictError(f"Script with alias '{alias}' already exists.")

    script = Script()
    script.title = title or alias or f"untitled"
    script.alias = alias

    # Populate flattened fields from payload. Require 'acts' (no legacy 'scenes').
    if isinstance(data.get("acts"), list):
        script.acts = json.dumps(data.get("acts"), ensure_ascii=False)

    characters = data.get("characters")
    if characters is not None:
        script.characters = json.dumps(characters, ensure_ascii=False)

    setting = data.get("setting")
    if setting is not None:
        script.setting = json.dumps(setting, ensure_ascii=False)

    genre = data.get("genre")
    if genre is not None:
        # accept list or string
        script.genre = json.dumps(genre, ensure_ascii=False) if isinstance(genre, list) else str(genre)

    themes = data.get("themes")
    if themes is not None:
        script.themes = json.dumps(themes, ensure_ascii=False) if isinstance(themes, list) else str(themes)

    builder = data.get("builder_configs")
    if builder is not None:
        script.builder_configs = json.dumps(builder, ensure_ascii=False)

    db.session.add(script)
    db.session.commit()
    return script


def list_scripts(request_args: Any, include_narration: bool = False):
    def _serialize(s: Script):
        d = s.to_dict()
        if include_narration:
            d['full_text'] = s.full_text
        return d

    resp = paginate_query(
        Script.query,
        Script,
        request_args,
        serialize=_serialize,
        default_sort='updated_at',
        allowed_sort_fields={'id', 'updated_at', 'created_at', 'title', 'alias', 'status', 'duration'},
    )
    return resp


def get_script_by_id(script_id: int) -> Script:
    script = db.session.get(Script, script_id)
    if not script:
        raise NotFoundError('Script not found')
    return script


def update_script(script_id: int, data: dict) -> Script:
    script = db.session.get(Script, script_id)
    if not script:
        raise NotFoundError('Script not found')

    meta = data.get('meta') or {}
    if 'title' in data or 'title' in meta:
        script.title = data.get('title') or meta.get('title') or script.title
    if 'alias' in data or 'alias' in meta:
        new_alias = meta.get('alias') or data.get('alias')
        if new_alias and new_alias != script.alias and Script.query.filter_by(alias=new_alias).first():
            raise ConflictError(f"Script with alias '{new_alias}' already exists.")
        script.alias = new_alias or script.alias

    # Apply same flattened-field population as create
    if isinstance(data.get("acts"), list):
        script.acts = json.dumps(data.get("acts"), ensure_ascii=False)

    characters = data.get("characters")
    if characters is not None:
        script.characters = json.dumps(characters, ensure_ascii=False)

    setting = data.get("setting")
    if setting is not None:
        script.setting = json.dumps(setting, ensure_ascii=False)

    genre = data.get("genre")
    if genre is not None:
        script.genre = json.dumps(genre, ensure_ascii=False) if isinstance(genre, list) else str(genre)

    themes = data.get("themes")
    if themes is not None:
        script.themes = json.dumps(themes, ensure_ascii=False) if isinstance(themes, list) else str(themes)

    builder = data.get("builder_configs")
    if builder is not None:
        script.builder_configs = json.dumps(builder, ensure_ascii=False)

    db.session.commit()
    return script


def delete_script(script_id: int) -> None:
    script = db.session.get(Script, script_id)
    if not script:
        raise NotFoundError('Script not found')
    db.session.delete(script)
    db.session.commit()


def compute_project_path_for_script(script: Script, root_dir: Path | None = None) -> Path:
    """Compute the project path for a script using our utils helper.

    Returns a resolved Path object.
    """
    if root_dir is None:
        root_dir = Path(current_app.root_path).parent
    sd = {"meta": {"alias": script.alias, "title": script.title}, "id": script.id}
    return Path(get_project_path(sd, root_dir)).resolve()


def prepare_project_folder(script_id: int, root_dir: Path | None = None) -> dict:
    """Create the project folder on disk and mark the script as prepared.

    Returns a dict with keys: path (str) and script (Script instance).
    Raises NotFoundError if script not found.
    """
    script = db.session.get(Script, script_id)
    if not script:
        raise NotFoundError('Script not found')

    project_path = compute_project_path_for_script(script, root_dir)
    project_path.mkdir(parents=True, exist_ok=True)

    try:
        script.is_has_folder = True
        db.session.add(script)
        db.session.commit()
    except Exception as db_e:
        db.session.rollback()
        log.error("folder.mark_has_folder.failed", script_id=script_id, error=str(db_e))

    try:
        db.session.refresh(script)
    except Exception:
        try:
            script = db.session.get(Script, script_id)
        except Exception:
            script = None

    return {"path": str(project_path), "script": script}


def open_project_folder(script_id: int, root_dir: Path | None = None) -> dict:
    """Attempt to open the project folder on the server host.

    Returns a dict with message/path or raises NotFoundError.
    """
    script = db.session.get(Script, script_id)
    if not script:
        raise NotFoundError('Script not found')

    project_path = compute_project_path_for_script(script, root_dir)

    projects_root = Path(settings.PROJECT_FOLDER).resolve()
    try:
        if not project_path.is_relative_to(projects_root):
            raise PermissionError('Path outside project root')
    except AttributeError:
        try:
            project_path.relative_to(projects_root)
        except Exception:
            raise PermissionError('Path outside project root')

    if not project_path.exists():
        raise FileNotFoundError('Project path not found')

    try:
        if os.name == 'nt':
            os.startfile(str(project_path))
        else:
            opener = shutil.which('xdg-open') or shutil.which('open')
            if opener:
                subprocess.Popen([opener, str(project_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                return {"message": "Project path exists but no opener is available on server.", "path": str(project_path)}

        return {"message": "Project folder open command executed", "path": str(project_path)}
    except Exception as e:
        log.error("folder.open.failed", script_id=script_id, error=str(e))
        raise


def get_project_path_info(script_id: int, root_dir: Path | None = None) -> dict:
    """Return computed project path and whether it exists on disk."""
    script = db.session.get(Script, script_id)
    if not script:
        raise NotFoundError('Script not found')
    project_path = compute_project_path_for_script(script, root_dir)
    return {"path": str(project_path), "exists": project_path.exists()}