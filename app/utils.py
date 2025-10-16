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
from app.models.script import Script


# --- Config/Settings Helpers ---

def _get_settings_path() -> Path:
    """Returns the absolute path to the settings.json file."""
    # current_app.root_path is the 'app' directory, so its parent is the project root.
    return current_app.root_path.parent / 'settings.json'

def load_config() -> dict:
    """Loads the UI settings from settings.json."""
    try:
        p = _get_settings_path()
        if p.exists():
            with p.open('r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_config(cfg: dict):
    """Saves the UI settings to settings.json."""
    p = _get_settings_path()
    with p.open('w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# --- Project Path Helper ---

def get_project_path(script_data: Dict[str, Any], root_dir: Path = None) -> Path:
    """
    Determines the full path for a project folder based on script data.
    """
    if root_dir is None:
        root_dir = current_app.root_path.parent

    cfg = load_config()
    proj_folder = cfg.get('project_folder')

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

def asset_check_once():
    """Check audio and images for all scripts and update statuses."""
    project_root = current_app.root_path.parent
    summary = { 'checked': 0, 'skipped': 0, 'audio_present': 0, 'audio_missing': 0, 'images_ok': 0, 'images_partial': 0, 'images_missing': 0, 'changed': 0 }
    lines = []
    scripts = Script.query.order_by(Script.id).all()
    for s in scripts:
        if getattr(s, 'status', None) == 'finish':
            summary['skipped'] += 1
            lines.append(f"id={s.id} alias={s.alias} | SKIPPED (status=finish)")
            continue
        summary['checked'] += 1
        changed = False
        try:
            data = s.script_data
            episode_path = get_project_path(data, Path(project_root))
            if not isinstance(episode_path, Path):
                episode_path = Path(episode_path)

            audio_status = 'missing'
            matched_audio = None
            exts = ('*.mp3', '*.m4a', '*.wav')

            for ext in exts:
                candidate = episode_path / ext.replace('*', 'audio')
                if candidate.exists():
                    matched_audio = candidate
                    break
            
            if not matched_audio and episode_path.exists():
                for ext in exts:
                    found = list(episode_path.glob(ext))
                    if found:
                        matched_audio = found[0]
                        break

            if not matched_audio and episode_path.parent.exists():
                for ext in exts:
                    found = list(episode_path.parent.glob(ext))
                    if found:
                        matched_audio = found[0]
                        break

            if not matched_audio:
                alias = (data.get('meta') or {}).get('alias') or ''
                patterns = [f"{data.get('id')}*.mp3", f"{alias}*.mp3"]
                for pat in patterns:
                    found = list(episode_path.parent.rglob(pat))
                    if found:
                        matched_audio = found[0]
                        break

            if not matched_audio:
                audio_status = 'missing'
                matched_rel = ''
                summary['audio_missing'] += 1
            else:
                audio_status = 'present'
                matched_rel = _safe_display(matched_audio)
                summary['audio_present'] += 1

            transcript_status = 'missing'
            transcript_file = None
            if episode_path.exists():
                t1 = episode_path / 'audio.whisperx.json'
                if t1.exists():
                    transcript_file = t1
                else:
                    found_t = list(episode_path.glob('*.whisperx.json'))
                    if found_t:
                        transcript_file = found_t[0]
            if not transcript_file and episode_path.parent.exists():
                found_t = list(episode_path.parent.glob('*.whisperx.json'))
                if found_t:
                    transcript_file = found_t[0]

            if transcript_file:
                transcript_status = 'present'
                summary.setdefault('transcript_present', 0)
                summary['transcript_present'] += 1
                t_rel = _safe_display(transcript_file)
            else:
                summary.setdefault('transcript_missing', 0)
                summary['transcript_missing'] += 1
                t_rel = ''

            if getattr(s, 'transcript_status', None) != transcript_status:
                s.transcript_status = transcript_status
                changed = True

            img_count = 0
            candidates = [episode_path, episode_path / 'images']
            for c in candidates:
                if c.exists():
                    for ext in ('*.png', '*.jpg', '*.jpeg'):
                        img_count += len(list(c.glob(ext)))

            scenes_count = len(data.get('scenes', []) or [])
            if img_count == 0:
                images_status = 'missing'
                summary['images_missing'] += 1
            elif img_count >= scenes_count and scenes_count > 0:
                images_status = 'ok'
                summary['images_ok'] += 1
            else:
                images_status = 'partial'
                summary['images_partial'] += 1

            if getattr(s, 'audio_status', None) != audio_status:
                s.audio_status = audio_status
                changed = True
            if getattr(s, 'images_status', None) != images_status:
                s.images_status = images_status
                changed = True

            display = _safe_display(episode_path)
            ma = matched_rel if 'matched_rel' in locals() and matched_rel else '-'
            lines.append(f"id={s.id} alias={s.alias} | audio={audio_status} audio_path={ma} images={images_status} (imgs={img_count} scenes={scenes_count}) path={display}")

            if changed:
                summary['changed'] += 1
                current_app.logger.info(f"Updated asset status for id={s.id}: audio={audio_status}, images={images_status}")

        except Exception as e:
            current_app.logger.exception(f"Error checking assets for script id={s.id}: {e}")
            lines.append(f"id={s.id} alias={s.alias} | ERROR: {e}")

    # Log the summary and details using the application logger
    current_app.logger.info(
        "Asset check summary",
        extra={
            "type": "asset_check_summary",
            "summary": summary
        }
    )
    for line in lines:
        current_app.logger.info(line, extra={"type": "asset_check_detail"})

    return summary


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
                script_texts = [line.get('text', '') for scene in script.scenes for line in scene.get('lines', []) if line.get('text')]
                txt_content = "\n\n".join(script_texts)
                content_txt_path.write_text(txt_content, encoding='utf-8')

                script_json_path = episode_path / "capcut-api.json"
                script_json_path.write_text(json.dumps(script.script_data, indent=2, ensure_ascii=False), encoding='utf-8')

                tts_json_path = episode_path / "content.json"
                all_lines = [line for scene in script.scenes for line in scene.get('lines', [])]
                tts_json_path.write_text(json.dumps(all_lines, indent=2, ensure_ascii=False), encoding='utf-8')

                script.status = 'prepared'
                db.session.add(script)
                processed_count += 1
            except Exception as e:
                current_app.logger.exception(f"Generator run: Failed to process script id={script.id}. Error: {e}")
        db.session.commit()
        current_app.logger.info(f"Generator run: Finished. Processed {processed_count} scripts.")
