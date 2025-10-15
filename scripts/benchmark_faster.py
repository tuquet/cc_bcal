#!/usr/bin/env python3
"""
Simple benchmark harness to compare faster-whisper vs whisper in this repo.
Usage: python scripts/benchmark_faster.py --audio /path/to/audio.mp3 --mode small --runs 1
"""
import argparse
import time
import subprocess
from pathlib import Path
import sys

p = argparse.ArgumentParser()
p.add_argument('--audio', required=True)
p.add_argument('--runs', type=int, default=1)
p.add_argument('--model', default='small')
p.add_argument('--use-faster', action='store_true')
p.add_argument('--faster-compute-type', default='float16')
args = p.parse_args()

audio = args.audio
runs = args.runs
model = args.model
use_faster = args.use_faster
fct = args.faster_compute_type

print('Benchmark settings:', args)

for i in range(runs):
    out = Path(audio).with_suffix(f'.bench.{model}.run{i}.json')
    cmd = [sys.executable, 'scripts/run_whisperx_local.py', '--audio', audio, '--output', str(out), '--whisper-model', model]
    if use_faster:
        cmd += ['--use-faster', '--faster-compute-type', fct]
    print('\nRun', i+1, 'cmd:', ' '.join(cmd))
    t0 = time.time()
    proc = subprocess.run(cmd)
    t1 = time.time()
    print('Exit', proc.returncode, 'Elapsed', t1-t0)

print('Done')
