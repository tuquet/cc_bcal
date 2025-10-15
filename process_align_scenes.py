#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


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
    print(f"  -> Wrote SRT: {srt_path.relative_to(Path.cwd())} ({idx - 1} segments)")


def run_whisperx_job(job: dict, dry_run: bool, require_gpu: bool) -> dict:
    """Runs a single WhisperX job in a Docker container."""
    mp3_path = job['mp3']
    json_path = job['whisperx_json']
    repo_root = Path.cwd()

    print(f"Processing: {mp3_path.relative_to(repo_root)}")
    if dry_run:
        print("  -> Dry run, skipping Docker execution.")
        return {'ok': True, 'job': job, 'note': 'dry-run'}

    user_cache = Path.home() / '.cache'
    user_cache.mkdir(exist_ok=True)

    container_audio = '/workspace/' + mp3_path.relative_to(repo_root).as_posix()
    container_json = '/workspace/' + json_path.relative_to(repo_root).as_posix()

    docker_args = [
        'docker', 'run', '--rm',
        '-v', f'{repo_root}:/workspace',
        '-v', f'{user_cache}:/root/.cache',
        '-e', 'HF_HOME=/root/.cache/huggingface',
        '-e', 'TRANSFORMERS_CACHE=/root/.cache/huggingface',
        '-e', 'TORCH_HOME=/root/.cache/torch',
    ]
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

        # Check if timings already exist
        if all(isinstance(s.get('start'), (int, float)) and isinstance(s.get('end'), (int, float)) for s in script_data.get('scenes', [])):
            print("  -> Skipping: File already has timing information for all scenes.")
            return

        null_count = 0
        for i, scene in enumerate(script_data.get('scenes', [])):
            start_time, end_time = find_scene_times(scene.get('narration', ''), segments)
            scene['start'] = start_time
            scene['end'] = end_time
            if start_time is None or end_time is None:
                null_count += 1
            
            # Add absolute image path
            image_file = episode_dir / f"{i + 1}.png"
            scene['image'] = str(image_file.resolve())

        # Get audio duration with ffprobe
        try:
            import ffmpeg_downloader as ffd
            command = [ffd.ffprobe_path, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)]
            duration_str = subprocess.check_output(command, text=True, stderr=subprocess.PIPE).strip()
            script_data['duration'] = float(duration_str)
        except (subprocess.CalledProcessError, ValueError) as e:
            print(f"  -> Warning: Could not get audio duration with ffprobe. Error: {e}", file=sys.stderr)

        with open(script_json_path, 'w', encoding='utf-8') as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)

        print(f"  -> Successfully aligned and updated: {script_json_path.relative_to(Path.cwd())}")
        if null_count > 0:
            print(f"  -> Warning: {null_count} scene(s) could not be aligned.", file=sys.stderr)

    except Exception as e:
        print(f"  -> Failed to process {episode_dir.name}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Run WhisperX batch processing and scene alignment.")
    parser.add_argument('projects', nargs='*', help="Specific episode directory names to process (e.g., '11.la-rung-vo-thuong'). If none, all projects are scanned.")
    parser.add_argument('--force', action='store_true', help="Force reprocessing even if output files exist.")
    parser.add_argument('--dry-run', action='store_true', help="List files to be processed without running Docker.")
    parser.add_argument('--parallel', type=int, default=1, help="Number of parallel jobs to run.")
    parser.add_argument('--require-gpu', action='store_true', default=True, help="Run Docker with GPU support (default).")
    parser.add_argument('--no-gpu', dest='require_gpu', action='store_false', help="Run Docker without GPU support.")
    
    args = parser.parse_args()

    repo_root = Path.cwd()
    episodes_root = repo_root / 'projects'

    if not episodes_root.is_dir():
        print(f"Error: 'projects' directory not found at {episodes_root}", file=sys.stderr)
        sys.exit(1)

    target_episode_dirs = []
    if args.projects:
        for ep_name in args.projects:
            ep_dir = episodes_root / ep_name
            if ep_dir.is_dir():
                target_episode_dirs.append(ep_dir)
            else:
                print(f"Warning: Specified episode directory not found: {ep_dir}", file=sys.stderr)
    else:
        target_episode_dirs = [d for d in episodes_root.iterdir() if d.is_dir()]

    if not target_episode_dirs:
        print("No episode directories found to process.", file=sys.stderr)
        sys.exit(0)

    # --- 1. Build WhisperX job list ---
    work = []
    for ep_dir in target_episode_dirs:
        audio_files = list(ep_dir.glob('*.mp3'))
        if not audio_files:
            continue
        
        mp3_path = audio_files[0]
        base_name = mp3_path.stem
        whisperx_json_path = ep_dir / f"{base_name}.whisperx.json"

        if whisperx_json_path.exists() and not args.force:
            print(f"Skipping (output exists): {mp3_path.relative_to(repo_root)}")
            continue
        
        work.append({'mp3': mp3_path, 'whisperx_json': whisperx_json_path, 'dir': ep_dir})

    if not work:
        print("Nothing to do for transcription.")
    else:
        print(f"--- Starting Transcription ({len(work)} files) ---")
        if args.require_gpu and args.parallel > 1:
            print("Warning: --require-gpu with parallel > 1 may overload a single GPU.", file=sys.stderr)

        # --- 2. Run WhisperX jobs in parallel ---
        results = []
        with ThreadPoolExecutor(max_workers=args.parallel) as executor:
            futures = {executor.submit(run_whisperx_job, job, args.dry_run, args.require_gpu): job for job in work}
            for future in as_completed(futures):
                results.append(future.result())

        successes = [r for r in results if r['ok']]
        failures = [r for r in results if not r['ok']]

        print("\n--- Transcription Summary ---")
        print(f"  Total:   {len(results)}")
        print(f"  Success: {len(successes)}")
        print(f"  Failed:  {len(failures)}")

        if failures:
            print("\nFailed jobs details:")
            for res in failures:
                job_path = res['job']['mp3'].relative_to(repo_root)
                print(f" - {job_path}: {res.get('error', 'Unknown error')}")
            # Do not proceed to alignment if transcription failed
            sys.exit(1)

    # --- 3. Run Scene Alignment ---
    print("\n--- Starting Scene Alignment ---")
    # Align all projects that were targeted, regardless of whether they were transcribed in this run
    for ep_dir in target_episode_dirs:
        align_episode_scenes(ep_dir)

    print("\n--- Pipeline finished successfully ---")


if __name__ == "__main__":
    main()