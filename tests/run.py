"""Trình chạy test tiện lợi cho môi trường dev.

Usage:
    python tests\run.py        # chạy tất cả test với -q
    python tests\run.py -v     # chạy verbose
"""
import sys
import pytest
from pathlib import Path

# Ensure project root is on sys.path so imports work when running this script directly
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def run_seed_prompts():
    # Import lazily to avoid app import side-effects when not seeding
    try:
        from app.seeds.seed_prompts import run as seed_run
    except Exception as e:
        print(f'Could not import seed_prompts: {e}')
        return 2

    # run with create_tables_if_missing=True for local/dev
    result = seed_run()
    print('seed_prompts result:', result)
    return 0


def main(argv=None):
    argv = argv or sys.argv[1:]
    # Support seed option
    if '--seed-prompts' in argv:
        return run_seed_prompts()
    # mặc định dùng -q để output ngắn gọn
    args = ['-q']
    if '-v' in argv or '--verbose' in argv:
        args = []
    # cho phép chuyển thêm args vào pytest
    extra = [a for a in argv if a not in ('-v', '--verbose')]
    args.extend(extra)

    # Chạy pytest và trả về exit code
    return pytest.main(args)


if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
