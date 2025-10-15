#!/usr/bin/env python3
"""
Small wrapper to run the local whisperx_align.py with the current Python interpreter.
This lets the rest of the code call a consistent script path regardless of Docker.

Usage:
  python scripts/run_whisperx_local.py --audio /path/to/audio.mp3 --output /path/to/out.json [--require-gpu]

It forwards arguments to whisperx/whisperx_align.py and returns the same exit code.
"""
import sys
import os
import subprocess
from pathlib import Path

def main(argv):
    repo_root = Path(__file__).resolve().parent.parent
    whisperx_script = repo_root / 'whisperx' / 'whisperx_align.py'
    if not whisperx_script.exists():
        print(f"Local whisperx script not found: {whisperx_script}")
        return 2

    # Parse optional --gpu-index from argv (remove it before forwarding).
    argv_mod = list(argv)
    gpu_index = None
    if '--gpu-index' in argv_mod:
        i = argv_mod.index('--gpu-index')
        try:
            gpu_index = argv_mod[i+1]
            argv_mod.pop(i)
            argv_mod.pop(i)
        except Exception:
            gpu_index = None

    # If CUDA is available, prefer GPU and require it unless user explicitly omitted
    try:
        import torch
        cuda_ok = torch.cuda.is_available() and torch.cuda.device_count() > 0
    except Exception:
        cuda_ok = False

    if gpu_index is not None:
        print(f'[run_whisperx_local] user requested GPU index {gpu_index}, setting CUDA_VISIBLE_DEVICES')
        argv_mod.append('--require-gpu')
    else:
        if cuda_ok and '--require-gpu' not in argv_mod:
            print('[run_whisperx_local] CUDA available, auto-adding --require-gpu')
            argv_mod.append('--require-gpu')

    cmd = [sys.executable, str(whisperx_script)] + argv_mod
    print("Running local whisperx:", " ".join(cmd))

    # Ensure the child Python process uses UTF-8 for stdout/stderr on Windows
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    if gpu_index is not None:
        env['CUDA_VISIBLE_DEVICES'] = str(gpu_index)

    # Prepare logs directory and timestamped log file
    logs_dir = repo_root / 'logs'
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    from datetime import datetime
    base_name = 'whisperx'
    if '--audio' in argv and len(argv) > argv.index('--audio')+1:
        try:
            base_name = Path(argv[argv.index('--audio')+1]).stem
        except Exception:
            base_name = 'whisperx'
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    log_path = logs_dir / f"{base_name}.{ts}.transcribe.log"
    print('[run_whisperx_local] logging transcription stdout/stderr to', log_path)

    try:
        with open(log_path, 'w', encoding='utf-8') as lf:
            lf.write('COMMAND: ' + ' '.join(cmd) + '\n')
            lf.flush()
            try:
                proc = subprocess.run(cmd, check=False, env=env, stdout=lf, stderr=subprocess.STDOUT)
                return proc.returncode
            except FileNotFoundError as e:
                print('Failed to execute Python or script:', e)
                lf.write('\nERROR: Failed to execute: ' + str(e) + '\n')
                return 3
            except Exception as e:
                print('Unexpected error running whisperx:', e)
                lf.write('\nERROR: Unexpected error: ' + str(e) + '\n')
                return 4
    except Exception as e:
        print('Failed to open log file for writing:', e)
        try:
            proc = subprocess.run(cmd, check=False, env=env)
            return proc.returncode
        except Exception as e:
            print('Failed to run whisperx:', e)
            return 4

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
