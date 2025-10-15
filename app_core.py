import os
import sys
import json
from pathlib import Path
import threading
import time
from flask import Flask
from sqlalchemy import text

# Set project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database import db
from models import Script
from utils import get_project_path

# Templates are in ./templates
TEMPLATE_DIR = os.path.join(project_root, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)
DATABASE_PATH = os.path.join(project_root, 'database.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-very-secret-key-change-this'
app.config['JSON_AS_ASCII'] = False

# Simple UI settings stored in a JSON file in project root
SETTINGS_PATH = os.path.join(project_root, 'settings.json')


def load_config() -> dict:
    try:
        p = Path(SETTINGS_PATH)
        if p.exists():
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_config(cfg: dict):
    p = Path(SETTINGS_PATH)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


@app.context_processor
def inject_config():
    return {'config': load_config()}

# Init db
db.init_app(app)


def _safe_display(p: Path) -> str:
    try:
        return str(p.relative_to(project_root))
    except Exception:
        return str(p)


def asset_check_once():
    """Check audio and images for all scripts and update statuses."""
    summary = { 'checked': 0, 'skipped': 0, 'audio_present': 0, 'audio_missing': 0, 'images_ok': 0, 'images_partial': 0, 'images_missing': 0, 'changed': 0 }
    lines = []
    with app.app_context():
        scripts = Script.query.order_by(Script.id).all()
        for s in scripts:
            if getattr(s, 'status', None) == 'finish':
                summary['skipped'] += 1
                lines.append(f"id={s.id} alias={s.alias} | SKIPPED (status=finish)")
                continue
            summary['checked'] += 1
            # track whether this script had any status changes that require a DB commit
            changed = False
            try:
                data = s.script_data
                episode_path = get_project_path(data, Path(project_root))
                if not isinstance(episode_path, Path):
                    episode_path = Path(episode_path)

                # flexible audio detection
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

                if not matched_audio:
                    audio_dir = episode_path / 'audio'
                    if audio_dir.exists():
                        for ext in exts:
                            found = list(audio_dir.glob(ext))
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

                if matched_audio:
                    audio_status = 'present'
                    matched_rel = _safe_display(matched_audio)
                    summary['audio_present'] += 1
                else:
                    audio_status = 'missing'
                    matched_rel = ''
                    summary['audio_missing'] += 1

                # transcript detection: look for audio.whisperx.json or *.whisperx.json
                transcript_status = 'missing'
                transcript_file = None
                if episode_path.exists():
                    # common filename
                    t1 = episode_path / 'audio.whisperx.json'
                    if t1.exists():
                        transcript_file = t1
                    else:
                        # any whisperx json in folder
                        found_t = list(episode_path.glob('*.whisperx.json'))
                        if found_t:
                            transcript_file = found_t[0]
                if not transcript_file and episode_path.parent.exists():
                    # sometimes transcript placed in parent
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

                # Persist transcript_status on the Script model if changed
                if getattr(s, 'transcript_status', None) != transcript_status:
                    s.transcript_status = transcript_status
                    changed = True

                # images check
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

                # don't reset 'changed' here; preserve earlier transcript changes
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
                    db.session.add(s)
                    db.session.commit()
                    app.logger.info(f"Updated asset status for id={s.id}: audio={audio_status}, images={images_status}")

            except Exception as e:
                app.logger.exception(f"Error checking assets for script id={s.id}: {e}")
                lines.append(f"id={s.id} alias={s.alias} | ERROR: {e}")

    # write log
    try:
        logs_dir = os.path.join(project_root, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        asset_log = os.path.join(logs_dir, 'asset_check.log')
        from datetime import datetime
        ts = datetime.utcnow().isoformat() + 'Z'
        with open(asset_log, 'ab') as f:
            header = f"[{ts}] Asset check: checked={summary['checked']} skipped={summary.get('skipped',0)} changed={summary['changed']} audio_present={summary['audio_present']} audio_missing={summary['audio_missing']} images_ok={summary['images_ok']} images_partial={summary['images_partial']} images_missing={summary['images_missing']}\n"
            f.write(header.encode('utf-8'))
            for L in lines:
                f.write((L + "\n").encode('utf-8'))
            f.write(b"\n")
    except Exception:
        app.logger.exception('Failed to write asset_check.log')

    return summary


def generator_run_once():
    """Run the generate_from_db.py script once (writes to logs/generate_from_db.log)."""
    script_path = os.path.join(project_root, 'scripts', 'generate_from_db.py')
    if not os.path.exists(script_path):
        app.logger.error(f"Generator script not found: {script_path}")
        return

    logs_dir = os.path.join(project_root, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, 'generate_from_db.log')

    env = os.environ.copy()
    existing = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = project_root + (os.pathsep + existing if existing else '')
    env['PYTHONIOENCODING'] = 'utf-8'

    try:
        with open(log_path, 'ab') as logf:
            import subprocess, sys as _sys
            proc = subprocess.run([_sys.executable, '-u', script_path], cwd=project_root, stdout=logf, stderr=subprocess.STDOUT, env=env)
        if proc.returncode == 0:
            app.logger.info('Generator run completed successfully')
        else:
            app.logger.error(f'Generator run failed (exit code={proc.returncode})')
    except Exception as e:
        app.logger.exception(f'Failed to run generator: {e}')


def ensure_db_columns():
    try:
        with app.app_context():
            conn = db.engine.connect()
            try:
                res = conn.execute(text("PRAGMA table_info('scripts')"))
                existing = [row[1] for row in res.fetchall()]
                to_add = []
                if 'audio_status' not in existing:
                    to_add.append("ALTER TABLE scripts ADD COLUMN audio_status TEXT")
                if 'images_status' not in existing:
                    to_add.append("ALTER TABLE scripts ADD COLUMN images_status TEXT")
                if 'transcript_status' not in existing:
                    to_add.append("ALTER TABLE scripts ADD COLUMN transcript_status TEXT")
                for stmt in to_add:
                    try:
                        conn.execute(text(stmt))
                        app.logger.info(f"Applied DB migration: {stmt}")
                    except Exception as e:
                        app.logger.exception(f"Failed to apply migration '{stmt}': {e}")
            finally:
                conn.close()
    except Exception:
        app.logger.exception('Failed to ensure DB columns')


def start_asset_checker_thread():
    def _asset_check_loop():
        while True:
            try:
                asset_check_once()
            except Exception:
                app.logger.exception('Asset checker loop failed')
            time.sleep(60)
    t = threading.Thread(target=_asset_check_loop, daemon=True)
    t.start()


def start_generator_thread():
    def _generator_loop():
        while True:
            try:
                generator_run_once()
            except Exception:
                app.logger.exception('Generator loop failed')
            time.sleep(60)
    t = threading.Thread(target=_generator_loop, daemon=True)
    t.start()
