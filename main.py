from app_core import app, ensure_db_columns, start_asset_checker_thread, start_generator_thread
from flask import request, jsonify, Response, stream_with_context

# Import DB/models to ensure they're available for Flask context if needed
from database import db  # noqa: F401
from models import Script  # noqa: F401

# Import routes module which registers all endpoints on the app
import routes  # noqa: F401
import threading
from pathlib import Path
import os
import shutil
from datetime import datetime, timezone
import time
import subprocess
import sys
import json
import contextlib


# Background jobs registry (in-memory)
BACKGROUND_JOBS: dict = {}


def _run_generate_images(script_path_str: str, job_id: str):
    import importlib.util
    try:
        # mark started
        BACKGROUND_JOBS[job_id].update({'status': 'started', 'started_at': datetime.now(timezone.utc).isoformat()})

        script_file = Path(__file__).parent / "scripts" / "generate_scenes_image.py"
        spec = importlib.util.spec_from_file_location("gen_images", str(script_file))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        generate_images = getattr(mod, 'generate_images')

        # options may have been stored on the job entry
        job_opts = BACKGROUND_JOBS[job_id].get('options', {}) or {}

        # call generate_images with supported args if provided
        # ensure types: Path for script, Path for output_dir if present
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
    except Exception as e:
        BACKGROUND_JOBS[job_id].update({'status': 'error', 'finished_at': datetime.now(timezone.utc).isoformat(), 'error': str(e)})


def _run_transcript(script_path_str: str, job_id: str):
    try:
        BACKGROUND_JOBS[job_id].update({'status': 'started', 'started_at': datetime.now(timezone.utc).isoformat()})

        # determine episode dir and audio path
        script_file = Path(script_path_str)
        if script_file.is_file():
            ep_dir = script_file.parent
        else:
            ep_dir = script_file

        # prefer audio.mp3 then audio.wav
        audio_candidates = [ep_dir / 'audio.mp3', ep_dir / 'audio.wav']
        audio_path = None
        for p in audio_candidates:
            if p.exists():
                audio_path = p
                break
        if not audio_path:
            BACKGROUND_JOBS[job_id].update({'status': 'error', 'finished_at': datetime.now(timezone.utc).isoformat(), 'error': 'audio file not found'})
            return

        # Prefer Docker-based WhisperX if 'docker' is available; fall back to local script otherwise
        import shutil
        repo_root = Path.cwd()
        # WhisperX output uses the audio basename, e.g. audio.mp3 -> audio.whisperx.json
        out_path = ep_dir / f"{audio_path.stem}.whisperx.json"

        # Prefer local runner if present, otherwise try Docker, finally fall back to whisperx script
        local_runner = Path(__file__).parent / 'scripts' / 'run_whisperx_local.py'
        docker_exe = shutil.which('docker')

        if local_runner.exists():
            # Use local runner wrapper
            cmd = [sys.executable, str(local_runner), '--audio', str(audio_path), '--output', str(out_path)]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')

            # Poll for output while process runs
            while True:
                try:
                    if out_path.exists():
                        try:
                            data = json.loads(out_path.read_text(encoding='utf-8'))
                            segs = data.get('segments') or []
                            BACKGROUND_JOBS[job_id].update({
                                'status': 'running',
                                'last_update': datetime.now(timezone.utc).isoformat(),
                                'transcript_exists': True,
                                'transcript_segments': len(segs),
                            })
                        except Exception:
                            BACKGROUND_JOBS[job_id].update({'status': 'running', 'last_update': datetime.now(timezone.utc).isoformat()})
                except Exception:
                    pass

                if proc.poll() is not None:
                    break
                time.sleep(2)

            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                BACKGROUND_JOBS[job_id].update({'status': 'error', 'finished_at': datetime.now(timezone.utc).isoformat(), 'error': stderr or stdout})
                return

        elif docker_exe:
            # Run the prebuilt container (matches scripts/audio_align_scenes.py behavior)
            user_cache = Path.home() / '.cache'
            user_cache.mkdir(exist_ok=True)

            # Decide which directories to mount. If audio/output are under repo_root, mount repo_root
            # and use /workspace/<relpath>. Otherwise mount the parent directories and use external mount points.
            mounts = []
            container_audio = None
            container_json = None

            try:
                rel_audio = audio_path.relative_to(repo_root)
                # audio is inside repo_root
                mounts.append((repo_root, '/workspace'))
                container_audio = '/workspace/' + rel_audio.as_posix()
            except Exception:
                # audio is outside repo_root; mount its parent to /external_audio
                mounts.append((audio_path.parent, '/external_audio'))
                container_audio = '/external_audio/' + audio_path.name

            try:
                rel_out = out_path.relative_to(repo_root)
                # out path inside repo_root; if not already mounting repo_root, mount it
                if not any(m[1] == '/workspace' for m in mounts):
                    mounts.append((repo_root, '/workspace'))
                container_json = '/workspace/' + rel_out.as_posix()
            except Exception:
                # out path outside repo_root; mount its parent to /external_output
                if not any(m[1] == '/external_output' for m in mounts):
                    mounts.append((out_path.parent, '/external_output'))
                container_json = '/external_output/' + out_path.name

            # Build docker args with mounts
            docker_args = [docker_exe, 'run', '--rm']
            for host_dir, container_dir in mounts:
                docker_args.extend(['-v', f'{host_dir}:' + container_dir])
            docker_args.extend([
                '-v', f'{user_cache}:/root/.cache',
                '-e', 'HF_HOME=/root/.cache/huggingface',
                '-e', 'TRANSFORMERS_CACHE=/root/.cache/huggingface',
                '-e', 'TORCH_HOME=/root/.cache/torch',
                'cc_bcal-whisperx',
                '--audio', container_audio,
                '--output', container_json,
            ])

            # Start docker process and poll for progress. Use Popen so we can check for the
            # transcript file while the container is running and update job status periodically.
            proc = subprocess.Popen(docker_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')

            # Periodically check for the output file and update job status
            while True:
                # If transcript JSON exists, try to read and report basic info
                try:
                    if out_path.exists():
                        try:
                            data = json.loads(out_path.read_text(encoding='utf-8'))
                            segs = data.get('segments') or []
                            BACKGROUND_JOBS[job_id].update({
                                'status': 'running',
                                'last_update': datetime.now(timezone.utc).isoformat(),
                                'transcript_exists': True,
                                'transcript_segments': len(segs),
                            })
                        except Exception:
                            # file might be partially written; ignore parsing errors
                            BACKGROUND_JOBS[job_id].update({'status': 'running', 'last_update': datetime.now(timezone.utc).isoformat()})
                except Exception:
                    pass

                # Check if process finished
                if proc.poll() is not None:
                    break

                time.sleep(2)

            # Collect final output
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                BACKGROUND_JOBS[job_id].update({'status': 'error', 'finished_at': datetime.now(timezone.utc).isoformat(), 'error': stderr or stdout})
                return
        else:
            # Fallback: run the local whisperx_align.py which requires whisper & whisperx installed
            whisper_script = Path(__file__).parent / 'whisperx' / 'whisperx_align.py'
            # Fallback: run the local whisperx script but poll for output similarly
            cmd = [sys.executable, str(whisper_script), '--audio', str(audio_path), '--output', str(out_path)]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
            while True:
                try:
                    if out_path.exists():
                        try:
                            data = json.loads(out_path.read_text(encoding='utf-8'))
                            segs = data.get('segments') or []
                            BACKGROUND_JOBS[job_id].update({
                                'status': 'running',
                                'last_update': datetime.now(timezone.utc).isoformat(),
                                'transcript_exists': True,
                                'transcript_segments': len(segs),
                            })
                        except Exception:
                            BACKGROUND_JOBS[job_id].update({'status': 'running', 'last_update': datetime.now(timezone.utc).isoformat()})
                except Exception:
                    pass

                if proc.poll() is not None:
                    break
                time.sleep(2)

            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                BACKGROUND_JOBS[job_id].update({'status': 'error', 'finished_at': datetime.now(timezone.utc).isoformat(), 'error': stderr or stdout})
                return

        # read output
        try:
            data = json.loads(out_path.read_text(encoding='utf-8'))
        except Exception:
            data = {'segments': []}

        BACKGROUND_JOBS[job_id].update({'status': 'done', 'finished_at': datetime.now(timezone.utc).isoformat(), 'result': {'ok': True, 'transcript': data}})
    except Exception as e:
        BACKGROUND_JOBS[job_id].update({'status': 'error', 'finished_at': datetime.now(timezone.utc).isoformat(), 'error': str(e)})


def _run_generate_capcut(script_path_str: str, job_id: str, ratio: str = '9:16'):
    try:
        BACKGROUND_JOBS[job_id].update({'status': 'started', 'started_at': datetime.now(timezone.utc).isoformat()})

        run_step = Path(__file__).parent / 'run_step_4_5.py'
        cmd = [sys.executable, str(run_step), str(script_path_str), '--ratio', ratio]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if proc.returncode != 0:
            BACKGROUND_JOBS[job_id].update({'status': 'error', 'finished_at': datetime.now(timezone.utc).isoformat(), 'error': proc.stderr or proc.stdout})
            return

        BACKGROUND_JOBS[job_id].update({'status': 'done', 'finished_at': datetime.now(timezone.utc).isoformat(), 'result': {'ok': True, 'output': proc.stdout}})
    except Exception as e:
        BACKGROUND_JOBS[job_id].update({'status': 'error', 'finished_at': datetime.now(timezone.utc).isoformat(), 'error': str(e)})


def _run_audio_align(script_path_str: str, job_id: str):
    """Run the audio-align pipeline (align_only=True) from scripts/audio_align_scenes.py as a background job."""
    try:
        BACKGROUND_JOBS[job_id].update({'status': 'started', 'started_at': datetime.now(timezone.utc).isoformat()})
        # Dynamically load the audio_align_scenes module to avoid import-time side effects
        import importlib.util
        script_file = Path(__file__).parent / 'scripts' / 'audio_align_scenes.py'
        spec = importlib.util.spec_from_file_location('audio_align_scenes', str(script_file))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        run_pipeline = getattr(mod, 'run_pipeline')

        # Determine episode dir for log placement
        script_file_obj = Path(script_path_str)
        ep_dir = script_file_obj.parent if script_file_obj.is_file() else script_file_obj
        logs_dir = ep_dir / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / f"{job_id}_audio_align.log"

        # Run pipeline with stdout/stderr redirected to the log file
        result = None
        try:
            with open(log_path, 'w', encoding='utf-8', errors='replace') as fh:
                with contextlib.redirect_stdout(fh), contextlib.redirect_stderr(fh):
                    print(f"--- Audio Align Job {job_id} START {datetime.now(timezone.utc).isoformat()} ---")
                    result = run_pipeline(script_files=[Path(script_path_str)], align_only=True)
                    print(f"--- Audio Align Job {job_id} END {datetime.now(timezone.utc).isoformat()} ---")
        except Exception as inner_e:
            # ensure exception is written to the log
            try:
                with open(log_path, 'a', encoding='utf-8', errors='replace') as fh:
                    fh.write(f"Exception during audio_align: {inner_e}\n")
            except Exception:
                pass
            raise

        BACKGROUND_JOBS[job_id].update({'status': 'done', 'finished_at': datetime.now(timezone.utc).isoformat(), 'result': result, 'log': str(log_path)})
    except Exception as e:
        # try to write the error into the log file if available
        try:
            if 'log_path' in locals():
                with open(log_path, 'a', encoding='utf-8', errors='replace') as fh:
                    fh.write(f"Unhandled exception: {e}\n")
        except Exception:
            pass
        BACKGROUND_JOBS[job_id].update({'status': 'error', 'finished_at': datetime.now(timezone.utc).isoformat(), 'error': str(e), 'log': str(log_path) if 'log_path' in locals() else None})


# API to trigger image generation for a project script file (background)
@app.route('/api/generate_images', methods=['POST'])
def api_generate_images():
    payload = request.get_json() or {}
    script_path = payload.get('script_json_path')
    if not script_path:
        return jsonify({'error': 'script_json_path is required'}), 400

    # Resolve script path: accept absolute or repo-relative paths
    script_path_obj = Path(script_path)
    if not script_path_obj.is_absolute():
        script_path_obj = (Path(__file__).parent / script_path_obj).resolve()

    if not script_path_obj.exists():
        return jsonify({'error': f'script_json_path not found: {script_path_obj}'}), 400

    # Accept optional generation options
    opts = {
        'headless': bool(payload.get('headless', False)),
        'chrome_exe': payload.get('chrome_exe'),
        'out_dir': payload.get('out_dir'),
        'user_data_dir': payload.get('user_data_dir'),
        'timeout': int(payload.get('timeout', 240)),
    }

    job_id = f"job_{len(BACKGROUND_JOBS) + 1}" # Consider a more robust job_id generation
    BACKGROUND_JOBS[job_id] = {'status': 'queued', 'queued_at': datetime.now(timezone.utc).isoformat(), 'script': str(script_path_obj), 'options': opts}
    t = threading.Thread(target=_run_generate_images, args=(str(script_path_obj), job_id), daemon=True)
    t.start()
    return jsonify({'job_id': job_id, 'status': 'queued'})


@app.route('/api/generate_images/status/<job_id>', methods=['GET'])
def api_generate_images_status(job_id):
    info = BACKGROUND_JOBS.get(job_id)
    if not info:
        return jsonify({'error': 'job not found'}), 404
    return jsonify(info)


@app.route('/api/transcribe/status/<job_id>', methods=['GET'])
def api_transcribe_status(job_id):
    info = BACKGROUND_JOBS.get(job_id)
    if not info:
        return jsonify({'error': 'job not found'}), 404
    return jsonify(info)


@app.route('/api/transcribe', methods=['POST'])
def api_transcribe():
    payload = request.get_json() or {}
    script_path = payload.get('script_json_path')
    if not script_path:
        return jsonify({'error': 'script_json_path is required'}), 400

    script_path_obj = Path(script_path)
    if not script_path_obj.is_absolute():
        script_path_obj = (Path(__file__).parent / script_path_obj).resolve()

    if not script_path_obj.exists():
        return jsonify({'error': f'script_json_path not found: {script_path_obj}'}), 400

    job_id = f"job_{len(BACKGROUND_JOBS) + 1}"
    BACKGROUND_JOBS[job_id] = {'status': 'queued', 'queued_at': datetime.now(timezone.utc).isoformat(), 'script': str(script_path_obj)}
    t = threading.Thread(target=_run_transcript, args=(str(script_path_obj), job_id), daemon=True)
    t.start()
    return jsonify({'job_id': job_id, 'status': 'queued'})


@app.route('/api/generate_capcut', methods=['POST'])
def api_generate_capcut():
    payload = request.get_json() or {}
    script_path = payload.get('script_json_path')
    ratio = payload.get('ratio', '9:16')
    if not script_path:
        return jsonify({'error': 'script_json_path is required'}), 400

    script_path_obj = Path(script_path)
    if not script_path_obj.is_absolute():
        script_path_obj = (Path(__file__).parent / script_path_obj).resolve()

    if not script_path_obj.exists():
        return jsonify({'error': f'script_json_path not found: {script_path_obj}'}), 400

    job_id = f"job_{len(BACKGROUND_JOBS) + 1}"
    BACKGROUND_JOBS[job_id] = {'status': 'queued', 'queued_at': datetime.now(timezone.utc).isoformat(), 'script': str(script_path_obj), 'ratio': ratio}
    t = threading.Thread(target=_run_generate_capcut, args=(str(script_path_obj), job_id, ratio), daemon=True)
    t.start()
    return jsonify({'job_id': job_id, 'status': 'queued'})


@app.route('/api/audio_align', methods=['POST'])
def api_audio_align():
    payload = request.get_json() or {}
    script_path = payload.get('script_json_path')
    if not script_path:
        return jsonify({'error': 'script_json_path is required'}), 400

    script_path_obj = Path(script_path)
    if not script_path_obj.is_absolute():
        script_path_obj = (Path(__file__).parent / script_path_obj).resolve()

    if not script_path_obj.exists():
        return jsonify({'error': f'script_json_path not found: {script_path_obj}'}), 400

    job_id = f"job_{len(BACKGROUND_JOBS) + 1}"
    BACKGROUND_JOBS[job_id] = {'status': 'queued', 'queued_at': datetime.now(timezone.utc).isoformat(), 'script': str(script_path_obj)}
    t = threading.Thread(target=_run_audio_align, args=(str(script_path_obj), job_id), daemon=True)
    t.start()
    return jsonify({'job_id': job_id, 'status': 'queued'})


@app.route('/api/audio_align/status/<job_id>', methods=['GET'])
def api_audio_align_status(job_id):
    info = BACKGROUND_JOBS.get(job_id)
    if not info:
        return jsonify({'error': 'job not found'}), 404
    return jsonify(info)


@app.route('/api/open_folder', methods=['POST'])
def api_open_folder():
    payload = request.get_json() or {}
    script_path = payload.get('script_json_path')
    if not script_path:
        return jsonify({'error': 'script_json_path is required'}), 400

    script_path_obj = Path(script_path)
    if not script_path_obj.is_absolute():
        script_path_obj = (Path(__file__).parent / script_path_obj).resolve()

    if not script_path_obj.exists():
        return jsonify({'error': f'script_json_path not found: {script_path_obj}'}), 400

    folder = script_path_obj.parent
    try:
        # Windows: os.startfile
        if sys.platform.startswith('win'):
            os.startfile(str(folder))
        else:
            # try xdg-open / open
            try:
                import subprocess
                if shutil.which('xdg-open'):
                    subprocess.Popen(['xdg-open', str(folder)])
                elif shutil.which('open'):
                    subprocess.Popen(['open', str(folder)])
                else:
                    return jsonify({'error': 'no method to open folder found on host'}), 500
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'ok': True, 'folder': str(folder)})


@app.route('/api/jobs/stream')
def api_jobs_stream():
    """Server-Sent Events endpoint that streams job updates as JSON messages.

    Each event will be a JSON object with {'job_id': ..., 'data': {...}}.
    Clients can subscribe and update the UI in realtime.
    """
    def event_stream():
        import json
        last_states = {}
        while True:
            try:
                # compare current BACKGROUND_JOBS to last_states and yield diffs
                for jid, info in list(BACKGROUND_JOBS.items()):
                    s = json.dumps(info, default=str, ensure_ascii=False)
                    if last_states.get(jid) != s:
                        last_states[jid] = s
                        payload = json.dumps({'job_id': jid, 'data': info}, ensure_ascii=False)
                        yield f"data: {payload}\n\n"
            except GeneratorExit:
                break
            except Exception:
                # on error, yield a heartbeat so client knows server still alive
                try:
                    yield 'data: {"heartbeat": true}\n\n'
                except Exception:
                    pass
            time.sleep(1)

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream')


def main():
    # Ensure DB tables exist and app is ready
    with app.app_context():
        db.create_all()
    try:
        ensure_db_columns()
    except Exception:
        pass
    try:
        start_asset_checker_thread()
    except Exception:
        pass
    try:
        start_generator_thread()
    except Exception:
        pass
    app.run(debug=True, port=5001)


if __name__ == '__main__':
    main()

