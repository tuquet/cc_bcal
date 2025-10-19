import os
import json
from pathlib import Path
from typing import Any, Dict
from flask import current_app
from datetime import datetime
import sys
import subprocess

# Imports from the new structure
from app.extensions import db
from app.settings import settings
from app.services.setting_service import get_all_settings_as_dict, update_settings
from app.models.script import Script


# --- Config/Settings Helpers ---

def load_config() -> dict:
    """DEPRECATED: Use the `settings` object from `app.settings` instead."""
    return get_all_settings_as_dict()

def save_config(cfg: dict):
    """Saves a dictionary of settings to the database."""
    update_settings(cfg)
    db.session.commit()
    # Reload the global settings object after saving
    settings.load()

# --- Project Path Helper ---

def get_project_path(script_data: Dict[str, Any], root_dir: Path = None) -> Path:
    """
    Determines the full path for a project folder based on script data.
    """
    if root_dir is None:
        root_dir = current_app.root_path.parent

    proj_folder = settings.PROJECT_FOLDER

    if proj_folder:
        proj_path = Path(proj_folder)
        projects_root = proj_path if proj_path.is_absolute() else (root_dir / proj_folder).resolve()
    else:
        projects_root = (root_dir / "projects").resolve()

    meta = script_data.get("meta", {})
    video_type = (meta.get("series") or meta.get("video_type", "general")).replace(" ", "-").lower()
    alias = meta.get("alias", "untitled")
    project_id = script_data.get("id")
    folder_name = f"{project_id}.{alias}"

    return projects_root / video_type / folder_name

# --- Background Task Logic (from old app_core) ---

def _safe_display(p: Path) -> str:
    """Safely display a path relative to the project root."""
    try:
        return str(p.relative_to(current_app.root_path.parent))
    except Exception:
        return str(p)

def generator_run_once():
    """Run the generate_from_db.py script once."""
    project_root = current_app.root_path.parent
    with current_app.app_context():
        new_scripts = Script.query.filter_by(status='new').order_by(Script.id).all()
        if not new_scripts:
            current_app.logger.info('Generator run: No new scripts to process.')
            return

        current_app.logger.info(f'Generator run: Found {len(new_scripts)} new scripts to process.')
        processed_count = 0
        for script in new_scripts:
            try:
                episode_path = get_project_path(script.script_data, Path(project_root))
                episode_path.mkdir(parents=True, exist_ok=True)

                content_txt_path = episode_path / "content.txt"
                script_texts = [line.get('text', '') for scene in script.scenes for line in scene.get('dialogues', []) if line.get('text')]
                txt_content = "\n\n".join(script_texts)
                content_txt_path.write_text(txt_content, encoding='utf-8')

                script_json_path = episode_path / "capcut-api.json"
                script_json_path.write_text(json.dumps(script.script_data, indent=2, ensure_ascii=False), encoding='utf-8')

                tts_json_path = episode_path / "content.json"
                all_dialogues = [line for scene in script.scenes for line in scene.get('dialogues', [])]
                tts_json_path.write_text(json.dumps(all_dialogues, indent=2, ensure_ascii=False), encoding='utf-8')

                script.status = 'prepared'
                db.session.add(script)
                processed_count += 1
            except Exception as e:
                current_app.logger.exception(f"Generator run: Failed to process script id={script.id}. Error: {e}")
