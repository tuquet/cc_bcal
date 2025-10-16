import queue
import threading
import json
import redis
from datetime import datetime, timezone
from pathlib import Path
import contextlib

# These are initialized by init_tasks
redis_client = None
JOB_QUEUE = queue.Queue()
BACKGROUND_JOBS = {}
REDIS_CHANNEL = 'job_updates'

def job_worker(app):
    """A dedicated worker thread that processes jobs from the JOB_QUEUE one by one."""
    while True:
        try:
            job = JOB_QUEUE.get()  # This will block until a job is available
            target_func = job.get('target')
            args = job.get('args', ())
            if callable(target_func):
                with app.app_context():
                    target_func(*args)
        except Exception as e:
            # Use app logger if available, otherwise print
            if app:
                app.logger.exception("Error in job worker thread.")
            else:
                print(f"Error in job worker thread: {e}")

def init_tasks(app):
    """Initializes the task runner background thread and Redis client."""
    global redis_client
    redis_client = redis.Redis(
        host=app.config.get('REDIS_HOST', 'localhost'),
        port=app.config.get('REDIS_PORT', 6379),
        db=app.config.get('REDIS_DB', 0),
        decode_responses=True
    )
    try:
        redis_client.ping() # Check connection
        app.logger.info("Redis connection successful.")
    except redis.exceptions.ConnectionError as e:
        app.logger.error(f"Redis connection failed: {e}")

    # Start the single job worker thread
    threading.Thread(target=job_worker, args=(app,), daemon=True).start()
    app.logger.info("Job worker thread started.")

# --- Job Functions (moved from main.py) ---
# Note: These functions are executed by the worker and have an active app context.

def _run_generate_images(script_id: int, script_path_str: str, job_id: str):
    from flask import current_app
    from .database import db
    from .models.models import Script
    from .utils.utils import asset_check_once
    from scripts.generate_scenes_image import generate_images

    try:
        BACKGROUND_JOBS[job_id].update({'status': 'running', 'last_update': datetime.now(timezone.utc).isoformat()})
        redis_client.publish(REDIS_CHANNEL, json.dumps({'job_id': job_id, 'script_id': script_id, 'data': BACKGROUND_JOBS[job_id]}))
        
        job_opts = BACKGROUND_JOBS[job_id].get('options', {}) or {}
        out_dir = job_opts.get('out_dir')
        if out_dir:
            out_dir = Path(out_dir)

        result = generate_images(
            Path(script_path_str),
            output_dir=out_dir,
            headless=job_opts.get('headless', False),
            chrome_exe=job_opts.get('chrome_exe'),
            user_data_dir=Path(job_opts['user_data_dir']) if job_opts.get('user_data_dir') else None,
            timeout=job_opts.get('timeout', 240),
        )

        BACKGROUND_JOBS[job_id].update({'status': 'done', 'finished_at': datetime.now(timezone.utc).isoformat(), 'result': result})
        asset_check_once()
        script = db.session.get(Script, script_id)
        if script:
            BACKGROUND_JOBS[job_id]['final_script_status'] = script.status
            BACKGROUND_JOBS[job_id]['final_asset_statuses'] = {'audio': script.audio_status, 'images': script.images_status, 'transcript': script.transcript_status}
        db.session.commit()
        redis_client.publish(REDIS_CHANNEL, json.dumps({'job_id': job_id, 'script_id': script_id, 'data': BACKGROUND_JOBS[job_id]}))
    except Exception as e:
        current_app.logger.exception(f"Job '{job_id}' failed in _run_generate_images")
        BACKGROUND_JOBS[job_id].update({'status': 'error', 'finished_at': datetime.now(timezone.utc).isoformat(), 'error': str(e)})
        redis_client.publish(REDIS_CHANNEL, json.dumps({'job_id': job_id, 'script_id': script_id, 'data': BACKGROUND_JOBS[job_id]}))

def _run_transcript(script_id: int, script_path_str: str, job_id: str):
    from flask import current_app
    from .database import db
    from .models.models import Script
    from scripts.run_whisperx_local import main as run_whisperx

    try:
        BACKGROUND_JOBS[job_id].update({'status': 'running', 'last_update': datetime.now(timezone.utc).isoformat()})
        redis_client.publish(REDIS_CHANNEL, json.dumps({'job_id': job_id, 'script_id': script_id, 'data': BACKGROUND_JOBS[job_id]}))
        
        script_file = Path(script_path_str)
        ep_dir = script_file.parent if script_file.is_file() else script_file

        audio_candidates = [ep_dir / 'audio.mp3', ep_dir / 'audio.wav']
        audio_path = next((p for p in audio_candidates if p.exists()), None)

        if not audio_path:
            raise FileNotFoundError("Audio file (audio.mp3 or audio.wav) not found.")

        out_path = ep_dir / f"{audio_path.stem}.whisperx.json"
        whisperx_args = ['--audio', str(audio_path), '--output', str(out_path)]
        return_code = run_whisperx(whisperx_args)

        if return_code != 0 and not out_path.exists():
            raise Exception(f"run_whisperx_local.py failed with exit code {return_code}")

        data = json.loads(out_path.read_text(encoding='utf-8'))
        BACKGROUND_JOBS[job_id].update({'status': 'done', 'finished_at': datetime.now(timezone.utc).isoformat(), 'result': {'ok': True, 'transcript': data}})

        script = db.session.get(Script, script_id)
        if script:
            script.transcript_status = 'present'
            script.duration = data.get('duration')
            BACKGROUND_JOBS[job_id]['final_script_status'] = script.status
            BACKGROUND_JOBS[job_id]['final_asset_statuses'] = { 'audio': script.audio_status, 'images': script.images_status, 'transcript': script.transcript_status }
        db.session.commit()
        redis_client.publish(REDIS_CHANNEL, json.dumps({'job_id': job_id, 'script_id': script_id, 'data': BACKGROUND_JOBS[job_id]}))
    except Exception as e:
        current_app.logger.exception(f"Job '{job_id}' failed in _run_transcript")
        BACKGROUND_JOBS[job_id].update({'status': 'error', 'finished_at': datetime.now(timezone.utc).isoformat(), 'error': str(e)})
        redis_client.publish(REDIS_CHANNEL, json.dumps({'job_id': job_id, 'script_id': script_id, 'data': BACKGROUND_JOBS[job_id]}))

def _run_generate_capcut(script_id: int, job_id: str, ratio: str = '9:16'):
    from flask import current_app
    from .database import db
    from .models.models import Script
    from .utils.utils import get_project_path
    from scripts.audio_align_scenes import run_pipeline
    from scripts.make_capcut_template import CapCutGenerator

    try:
        BACKGROUND_JOBS[job_id].update({'status': 'aligning', 'last_update': datetime.now(timezone.utc).isoformat()})
        redis_client.publish(REDIS_CHANNEL, json.dumps({'job_id': job_id, 'script_id': script_id, 'data': BACKGROUND_JOBS[job_id]}))
        
        script_path_str = BACKGROUND_JOBS[job_id].get('script')
        align_result = run_pipeline(script_files=[Path(script_path_str)], align_only=True)

        if not align_result.get('ok'):
            raise Exception(align_result.get('message', 'Alignment step failed.'))
        
        script = db.session.get(Script, script_id)
        if script:
            updated_script_path = Path(script_path_str)
            if updated_script_path.exists():
                aligned_data = json.loads(updated_script_path.read_text(encoding='utf-8'))
                script.scenes = aligned_data.get('scenes', script.scenes)
                script.duration = aligned_data.get('duration', script.duration)
                db.session.commit()

        BACKGROUND_JOBS[job_id].update({'status': 'generating_video', 'last_update': datetime.now(timezone.utc).isoformat()})
        redis_client.publish(REDIS_CHANNEL, json.dumps({'job_id': job_id, 'script_id': script_id, 'data': BACKGROUND_JOBS[job_id]}))
        
        script_data_from_db = script.script_data
        project_folder = get_project_path(script.script_data)

        generator = CapCutGenerator(project_folder, script_data_from_db, ratio=ratio)
        generator.run()

        BACKGROUND_JOBS[job_id].update({'status': 'done', 'finished_at': datetime.now(timezone.utc).isoformat(), 'result': {'ok': True, 'output': 'Generator run completed.'}})

        script = db.session.get(Script, script_id)
        if script:
            script.status = 'finish'
            BACKGROUND_JOBS[job_id]['final_script_status'] = script.status
        db.session.commit()
        redis_client.publish(REDIS_CHANNEL, json.dumps({'job_id': job_id, 'script_id': script_id, 'data': BACKGROUND_JOBS[job_id]}))
    except Exception as e:
        current_app.logger.exception(f"Job '{job_id}' failed in _run_generate_capcut")
        BACKGROUND_JOBS[job_id].update({'status': 'error', 'finished_at': datetime.now(timezone.utc).isoformat(), 'error': str(e)})
        redis_client.publish(REDIS_CHANNEL, json.dumps({'job_id': job_id, 'script_id': script_id, 'data': BACKGROUND_JOBS[job_id]}))

def _run_align_scenes(script_id: int, script_path_str: str, job_id: str):
    from flask import current_app
    from .database import db
    from .models.models import Script
    from .utils.utils import asset_check_once
    from scripts.audio_align_scenes import run_pipeline

    try:
        BACKGROUND_JOBS[job_id].update({'status': 'running', 'last_update': datetime.now(timezone.utc).isoformat()})
        redis_client.publish(REDIS_CHANNEL, json.dumps({'job_id': job_id, 'script_id': script_id, 'data': BACKGROUND_JOBS[job_id]}))

        result = run_pipeline(script_files=[Path(script_path_str)], align_only=True)

        if not result.get('ok'):
            raise Exception(result.get('message', 'Alignment script failed.'))

        BACKGROUND_JOBS[job_id].update({'status': 'done', 'finished_at': datetime.now(timezone.utc).isoformat(), 'result': result})

        asset_check_once()
        script = db.session.get(Script, script_id)
        if script:
            BACKGROUND_JOBS[job_id]['final_script_status'] = script.status
            BACKGROUND_JOBS[job_id]['final_asset_statuses'] = {'audio': script.audio_status, 'images': script.images_status, 'transcript': script.transcript_status}
        db.session.commit()
        redis_client.publish(REDIS_CHANNEL, json.dumps({'job_id': job_id, 'script_id': script_id, 'data': BACKGROUND_JOBS[job_id]}))
    except Exception as e:
        current_app.logger.exception(f"Job '{job_id}' failed in _run_align_scenes")
        BACKGROUND_JOBS[job_id].update({'status': 'error', 'finished_at': datetime.now(timezone.utc).isoformat(), 'error': str(e)})
        redis_client.publish(REDIS_CHANNEL, json.dumps({'job_id': job_id, 'script_id': script_id, 'data': BACKGROUND_JOBS[job_id]}))
