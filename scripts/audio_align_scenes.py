#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from utils import get_project_path


def to_srt_timestamp(sec: float) -> str:
    """Converts seconds to SRT time format HH:MM:SS,ms."""
    s = float(sec or 0)
    h = int(s / 3600)
    m = int((s % 3600) / 60)
    sec_i = int(s % 60)
    ms = round((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{sec_i:02d},{ms:03d}"


def write_srt_from_json(whisperx_json_path: Path):
    """
    Converts a .whisperx.json file to a .srt file with smart segment splitting.
    This function replicates the logic from `write-srt-from-outjson.mjs`.
    """
    if not whisperx_json_path.exists():
        print(f"  -> Error: WhisperX JSON file not found: {whisperx_json_path}", file=sys.stderr)
        return

    # Settings from the original script
    PAUSE_THRESHOLD = 0.6  # seconds
    MAX_SEGMENT_DURATION = 6.0  # seconds
    MAX_WORDS = 10

    with open(whisperx_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    segments = data.get('segments', [])
    srt_lines = []
    idx = 1

    for seg in segments:
        words = seg.get('words')
        if words and isinstance(words, list) and len(words) > 0:
            # Split segment by words based on timing
            groups = []
            current_group = []
            for i, word in enumerate(words):
                if not current_group:
                    current_group.append(word)
                    continue

                prev_word = current_group[-1]
                gap = word.get('start', 0) - prev_word.get('end', 0)
                cur_start = current_group[0].get('start', 0)
                cur_end = word.get('end', 0)
                cur_dur = cur_end - cur_start

                if gap >= PAUSE_THRESHOLD or len(current_group) >= MAX_WORDS or cur_dur >= MAX_SEGMENT_DURATION:
                    groups.append(current_group)
                    current_group = [word]
                else:
                    current_group.append(word)

            if current_group:
                groups.append(current_group)

            for group in groups:
                start_time = group[0].get('start')
                end_time = group[-1].get('end')
                text = ' '.join(w.get('word', '') for w in group).strip()
                if start_time is not None and end_time is not None and text:
                    srt_lines.append(str(idx))
                    srt_lines.append(f"{to_srt_timestamp(start_time)} --> {to_srt_timestamp(end_time)}")
                    srt_lines.append(text)
                    srt_lines.append('')
                    idx += 1
        else:
            # Fallback for segments without word timings
            start_time = seg.get('start')
            end_time = seg.get('end')
            text = (seg.get('text') or '').strip()
            if start_time is not None and end_time is not None and text:
                srt_lines.append(str(idx))
                srt_lines.append(f"{to_srt_timestamp(start_time)} --> {to_srt_timestamp(end_time)}")
                srt_lines.append(text)
                srt_lines.append('')
                idx += 1

    srt_content = '\n'.join(srt_lines)
    srt_path = whisperx_json_path.with_suffix('.srt')
    srt_path.write_text(srt_content, encoding='utf-8')
    try:
        display_srt = srt_path.relative_to(Path.cwd())
    except Exception:
        display_srt = srt_path
    print(f"  -> Wrote SRT: {display_srt} ({idx - 1} segments)")


def run_whisperx_job(job: dict, dry_run: bool, require_gpu: bool) -> dict:
    """Runs a single WhisperX job in a Docker container."""
    mp3_path = job['mp3']
    json_path = job['whisperx_json']
    repo_root = Path.cwd()

    try:
        display_path = mp3_path.relative_to(repo_root)
    except Exception:
        display_path = mp3_path
    print(f"Processing: {display_path}")
    if dry_run:
        print("  -> Dry run, skipping Docker execution.")
        return {'ok': True, 'job': job, 'note': 'dry-run'}

    user_cache = Path.home() / '.cache'
    user_cache.mkdir(exist_ok=True)

    # Compute container paths for audio and json.
    # If files are inside the repo root we can mount the repo as /workspace and use relative paths.
    extra_mounts = []
    try:
        rel_audio = mp3_path.relative_to(repo_root).as_posix()
        container_audio = '/workspace/' + rel_audio
    except Exception:
        # mp3_path is outside repo_root: mount its parent directory under /external/<n>
        parent = mp3_path.parent
        mount_point = '/external/audio'
        extra_mounts.append((str(parent), mount_point))
        container_audio = f"{mount_point}/{mp3_path.name}"

    try:
        rel_json = json_path.relative_to(repo_root).as_posix()
        container_json = '/workspace/' + rel_json
    except Exception:
        parent_j = json_path.parent
        mount_point_j = '/external/json'
        # Avoid re-adding same mount
        if (str(parent_j), mount_point_j) not in extra_mounts:
            extra_mounts.append((str(parent_j), mount_point_j))
        container_json = f"{mount_point_j}/{json_path.name}"

    docker_args = [
        'docker', 'run', '--rm',
        '-v', f'{repo_root}:/workspace',
        '-v', f'{user_cache}:/root/.cache',
        '-e', 'HF_HOME=/root/.cache/huggingface',
        '-e', 'TRANSFORMERS_CACHE=/root/.cache/huggingface',
        '-e', 'TORCH_HOME=/root/.cache/torch',
    ]

    # Add any extra mounts needed for files outside the repo
    for host_dir, mount_point in extra_mounts:
        docker_args.extend(['-v', f'{host_dir}:{mount_point}'])
    if require_gpu:
        docker_args.extend(['--gpus', 'all'])

    docker_args.extend([
        'cc_bcal-whisperx',
        '--audio', container_audio,
        '--output', container_json,
    ])
    if require_gpu:
        docker_args.append('--require-gpu')

    try:
        # Using DEVNULL for stdout/stderr to keep the main output clean, like the original script
        subprocess.run(docker_args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Convert JSON to SRT
        write_srt_from_json(json_path)
        
        return {'ok': True, 'job': job}
    except subprocess.CalledProcessError as e:
        print(f"  -> Docker exited with code {e.returncode} for {mp3_path.name}", file=sys.stderr)
        return {'ok': False, 'job': job, 'error': f"Docker exited with code {e.returncode}"}
    except Exception as e:
        print(f"  -> An unexpected error occurred for {mp3_path.name}: {e}", file=sys.stderr)
        return {'ok': False, 'job': job, 'error': str(e)}


def get_words(text: str) -> list[str]:
    """Normalizes and splits text into words."""
    if not text:
        return []
    return re.sub(r'[.,\':?"“\'”]', '', text.lower()).strip().split()


def calculate_similarity(arr1: list[str], arr2: list[str]) -> float:
    """Calculates Jaccard similarity between two arrays of words."""
    set1 = set(arr1)
    set2 = set(arr2)
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0


def find_scene_times(narration: str, segments: list[dict]) -> tuple[float | None, float | None]:
    """Finds the best matching block of segments for a given narration."""
    narration_words = get_words(narration)
    if not narration_words:
        return None, None

    best_match = {'start': None, 'end': None, 'score': 0}

    for i in range(len(segments)):
        for j in range(i, len(segments)):
            candidate_segments = segments[i : j + 1]
            candidate_words = [word for s in candidate_segments for word in get_words(s.get('text', ''))]

            if not candidate_words:
                continue

            score = calculate_similarity(narration_words, candidate_words)
            length_ratio = min(len(narration_words), len(candidate_words)) / max(len(narration_words), len(candidate_words))
            final_score = score * length_ratio

            if final_score > best_match['score']:
                best_match = {
                    'start': candidate_segments[0].get('start'),
                    'end': candidate_segments[-1].get('end'),
                    'score': final_score,
                }

    return (best_match['start'], best_match['end']) if best_match['score'] > 0.5 else (None, None)


def align_episode_scenes(episode_dir: Path):
    """
    Aligns scenes in capcut-api.json with timings from the whisperx.json file.
    This function replicates the logic from `align-scenes.mjs`.
    """
    try:
        print(f"\nAligning scenes for episode: {episode_dir.name}")
        script_json_path = episode_dir / 'capcut-api.json'
        audio_path = episode_dir / 'audio.mp3'

        if not script_json_path.exists() or not audio_path.exists():
            print(f"  -> Skipping: Missing capcut-api.json or audio.mp3 in {episode_dir.name}", file=sys.stderr)
            return

        whisper_files = list(episode_dir.glob('*.whisperx.json'))
        if not whisper_files:
            print(f"  -> Skipping: No .whisperx.json file found in {episode_dir.name}", file=sys.stderr)
            return

        whisper_path = whisper_files[0]
        with open(script_json_path, 'r', encoding='utf-8') as f:
            script_data = json.load(f)
        with open(whisper_path, 'r', encoding='utf-8') as f:
            whisper_data = json.load(f)

        segments = whisper_data.get('segments', [])

        null_count = 0
        for i, scene in enumerate(script_data.get('scenes', [])):
            start_time, end_time = find_scene_times(scene.get('narration', ''), segments)
            # Round start/end to nearest integer seconds when available, preserve None
            scene['start'] = int(round(start_time)) if start_time is not None else None
            scene['end'] = int(round(end_time)) if end_time is not None else None
            if start_time is None or end_time is None:
                null_count += 1
            
            # Add absolute image path if the file exists; otherwise set to None and warn
            image_file = episode_dir / f"{i + 1}.png"
            if image_file.exists():
                scene['image'] = str(image_file.resolve().as_posix())
            else:
                # Use empty string to avoid 'undefined' in frontends that render this value
                scene['image'] = ''
                print(f"  -> Warning: image file not found for scene {i + 1}: {image_file}", file=sys.stderr)

        # Get audio duration robustly with multiple fallbacks:
        # 1) imageio_ffmpeg.get_ffprobe_exe(), 2) system 'ffprobe' (PATH),
        # 3) imageio_ffmpeg.get_ffmpeg_exe() and parse stderr, 4) system 'ffmpeg' and parse stderr
        duration_obtained = False
        duration_value = None

        # Helper to run a command and return stdout
        def _run_cmd(cmd):
            try:
                return subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE).strip()
            except Exception:
                return None

        # Try imageio_ffmpeg.get_ffprobe_exe()
        try:
            import imageio_ffmpeg
            ffprobe_path = getattr(imageio_ffmpeg, 'get_ffprobe_exe', None)
            if callable(ffprobe_path):
                path = ffprobe_path()
            else:
                path = None
            if path:
                out = _run_cmd([path, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)])
                if out:
                    duration_value = float(out)
                    duration_obtained = True
        except ImportError:
            path = None

        # Try system ffprobe
        if not duration_obtained:
            import shutil
            sys_ffprobe = shutil.which('ffprobe')
            if sys_ffprobe:
                out = _run_cmd([sys_ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)])
                if out:
                    try:
                        duration_value = float(out)
                        duration_obtained = True
                    except ValueError:
                        duration_obtained = False

        # Try imageio_ffmpeg.get_ffmpeg_exe() and parse stderr for Duration
        if not duration_obtained:
            try:
                import imageio_ffmpeg
                get_ffmpeg = getattr(imageio_ffmpeg, 'get_ffmpeg_exe', None)
                if callable(get_ffmpeg):
                    ffmpeg_path = get_ffmpeg()
                else:
                    ffmpeg_path = None
                if ffmpeg_path:
                    # ffmpeg writes duration info to stderr when probing
                    proc = subprocess.run([ffmpeg_path, '-i', str(audio_path)], capture_output=True, text=True)
                    stderr = proc.stderr or ''
                    m = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', stderr)
                    if m:
                        h, mm, ss = m.groups()
                        duration_value = int(h) * 3600 + int(mm) * 60 + float(ss)
                        duration_obtained = True
            except ImportError:
                pass

        # Try system ffmpeg probe
        if not duration_obtained:
            import shutil
            sys_ffmpeg = shutil.which('ffmpeg')
            if sys_ffmpeg:
                proc = subprocess.run([sys_ffmpeg, '-i', str(audio_path)], capture_output=True, text=True)
                stderr = proc.stderr or ''
                m = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', stderr)
                if m:
                    h, mm, ss = m.groups()
                    duration_value = int(h) * 3600 + int(mm) * 60 + float(ss)
                    duration_obtained = True

        if duration_obtained and duration_value is not None:
            # Round duration to nearest integer seconds
            script_data['duration'] = int(round(float(duration_value)))
            # Ensure the last scene ends exactly at the audio duration
            scenes = script_data.get('scenes')
            if isinstance(scenes, list) and len(scenes) > 0:
                try:
                    scenes[-1]['end'] = script_data['duration']
                except Exception:
                    # If scene structure unexpected, skip silently
                    pass
        else:
            print("  -> Warning: Could not get audio duration (ffprobe/ffmpeg not available).", file=sys.stderr)

        with open(script_json_path, 'w', encoding='utf-8') as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)

        try:
            display_script = script_json_path.relative_to(Path.cwd())
        except Exception:
            display_script = script_json_path
        print(f"  -> Successfully aligned and updated: {display_script}")
        if null_count > 0:
            print(f"  -> Warning: {null_count} scene(s) could not be aligned.", file=sys.stderr)

    except Exception as e:
        print(f"  -> Failed to process {episode_dir.name}: {e}", file=sys.stderr)


def run_pipeline(
    script_files: list[Path] | None = None,
    force: bool = False,
    dry_run: bool = False,
    parallel: int = 1,
    require_gpu: bool = True,
    align_only: bool = False,
    repo_root: Path | None = None,
) -> dict:
    """Run the transcription + alignment pipeline programmatically.

    Returns a dict with summary information and does not call sys.exit so it is
    safe to import and call from other modules (for example `main.py`).

    Keys in the return dict:
    - ok: bool
    - processed_dirs: int
    - transcription: { total, success, failed, failures: [...] } (if align_only is False)
    - aligned: int
    - message: optional
    """
    repo_root = Path.cwd() if repo_root is None else Path(repo_root)
    episodes_root = repo_root / 'projects'

    # If script_files is None we will scan the projects directory, so ensure it exists.
    if script_files is None and not episodes_root.is_dir():
        return {'ok': False, 'message': f"'projects' directory not found at {episodes_root}"}

    target_episode_dirs = []
    if script_files:
        for script_file in script_files:
            if not Path(script_file).exists():
                continue
            try:
                with open(script_file, 'r', encoding='utf-8') as f:
                    ep_dir = get_project_path(json.load(f))
            except (json.JSONDecodeError, KeyError):
                continue

            if ep_dir.is_dir():
                target_episode_dirs.append(ep_dir)
    else:
        target_episode_dirs = [d for d in episodes_root.glob('*/*') if d.is_dir()]

    if not target_episode_dirs:
        return {'ok': True, 'processed_dirs': 0, 'message': 'No episode directories found to process.'}

    transcription_summary = None
    if not align_only:
        # Build WhisperX job list
        work = []
        for ep_dir in target_episode_dirs:
            audio_files = list(ep_dir.glob('*.mp3'))
            if not audio_files:
                continue

            mp3_path = audio_files[0]
            base_name = mp3_path.stem
            whisperx_json_path = ep_dir / f"{base_name}.whisperx.json"

            if whisperx_json_path.exists() and force:
                try:
                    whisperx_json_path.unlink()
                    srt_path = whisperx_json_path.with_suffix('.srt')
                    if srt_path.exists():
                        srt_path.unlink()
                except Exception:
                    pass

            if whisperx_json_path.exists() and not force:
                continue

            work.append({'mp3': mp3_path, 'whisperx_json': whisperx_json_path, 'dir': ep_dir})

        if work:
            results = []
            with ThreadPoolExecutor(max_workers=parallel) as executor:
                futures = {executor.submit(run_whisperx_job, job, dry_run, require_gpu): job for job in work}
                for future in as_completed(futures):
                    results.append(future.result())

            successes = [r for r in results if r.get('ok')]
            failures = [r for r in results if not r.get('ok')]
            transcription_summary = {
                'total': len(results),
                'success': len(successes),
                'failed': len(failures),
                'failures': failures,
            }
            if failures:
                # do not proceed to alignment if transcription failed
                return {'ok': False, 'processed_dirs': len(target_episode_dirs), 'transcription': transcription_summary}
        else:
            transcription_summary = {'total': 0, 'success': 0, 'failed': 0, 'failures': []}

    # Run Scene Alignment for all targeted dirs
    aligned_count = 0
    for ep_dir in target_episode_dirs:
        try:
            align_episode_scenes(ep_dir)
            aligned_count += 1
        except Exception:
            # align_episode_scenes prints its own errors; continue
            pass

    return {
        'ok': True,
        'processed_dirs': len(target_episode_dirs),
        'transcription': transcription_summary,
        'aligned': aligned_count,
    }


def main():
    parser = argparse.ArgumentParser(description="Run WhisperX batch processing and scene alignment.")
    parser.add_argument('script_files', nargs='*', type=Path, help="Path to one or more script JSON files (e.g., 'data/1.json'). If none, all projects are scanned.")
    parser.add_argument('--force', action='store_true', help="Force reprocessing even if output files exist.")
    parser.add_argument('--dry-run', action='store_true', help="List files to be processed without running Docker.")
    parser.add_argument('--parallel', type=int, default=1, help="Number of parallel jobs to run.")
    parser.add_argument('--require-gpu', action='store_true', default=True, help="Run Docker with GPU support (default).")
    parser.add_argument('--no-gpu', dest='require_gpu', action='store_false', help="Run Docker without GPU support.")
    parser.add_argument('--align-only', action='store_true', help="Only run the scene alignment step, skipping transcription.")

    args = parser.parse_args()
    result = run_pipeline(
        script_files=[Path(p) for p in args.script_files] if args.script_files else None,
        force=args.force,
        dry_run=args.dry_run,
        parallel=args.parallel,
        require_gpu=args.require_gpu,
        align_only=args.align_only,
    )

    # Mirror previous behavior for CLI: print summary and set exit code
    if not result.get('ok'):
        msg = result.get('message') or 'One or more jobs failed.'
        print(f"❌ {msg}", file=sys.stderr)
        # If transcription summary present include details
        if isinstance(result.get('transcription'), dict) and result['transcription'].get('failures'):
            for f in result['transcription']['failures']:
                job_path = f['job']['mp3'] if 'job' in f and 'mp3' in f['job'] else None
                print(f" - Failure: {job_path}: {f.get('error')}", file=sys.stderr)
        return 1

    # Success
    print("\n--- Pipeline finished successfully ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
