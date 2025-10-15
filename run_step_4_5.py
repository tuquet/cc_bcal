#!/usr/bin/env python3
"""
Wrapper to run alignment (4_process_align_scenes.py) then CapCut draft generation (5_process_video_capcut.py)
Usage: python run_episode.py data/68.json [--dry-run] [--require-gpu/--no-gpu] [--ratio 9:16]
"""
import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd_args):
    print("\n$", " ".join(cmd_args))
    res = subprocess.run(cmd_args)
    return res.returncode


def main():
    parser = argparse.ArgumentParser(description='Run align then CapCut for single episode script JSON')
    parser.add_argument('script_file', type=Path, help='Path to script JSON (e.g., data/68.json)')
    parser.add_argument('--dry-run', action='store_true', help='Pass --dry-run to alignment (skips Docker) and skip save in CapCut')
    parser.add_argument('--force', action='store_true', help='Pass --force to alignment to force reprocessing')
    parser.add_argument('--require-gpu', action='store_true', default=False, help='Pass --require-gpu to alignment')
    parser.add_argument('--no-gpu', dest='require_gpu', action='store_false', help='Disable GPU for alignment')
    parser.add_argument('--ratio', choices=['9:16', '16:9'], default='9:16', help='Ratio for CapCut')

    args = parser.parse_args()

    if not args.script_file.exists():
        print(f"Error: script file not found: {args.script_file}")
        sys.exit(2)

    # Step 1: run alignment (use same script file as input)
    align_cmd = [sys.executable, str(Path(__file__).parent / '4_process_align_scenes.py'), str(args.script_file)]
    if args.dry_run:
        align_cmd.append('--dry-run')
    if args.force:
        align_cmd.append('--force')
    if args.require_gpu:
        align_cmd.append('--require-gpu')
    else:
        align_cmd.append('--no-gpu')

    rc = run_command(align_cmd)
    if rc != 0:
        print(f"Alignment failed with exit code {rc}")
        sys.exit(rc)

    # Step 2: run CapCut draft generation
    capcut_cmd = [sys.executable, str(Path(__file__).parent / '5_process_video_capcut.py'), str(args.script_file), '--ratio', args.ratio]
    if args.dry_run:
        capcut_cmd.append('--dry-run')

    rc = run_command(capcut_cmd)
    if rc != 0:
        print(f"CapCut generation failed with exit code {rc}")
        sys.exit(rc)

    print('\nAll steps completed successfully.')


if __name__ == '__main__':
    main()
