"""Trình chạy test tiện lợi cho môi trường dev.

Usage:
    python tests\run.py        # chạy tất cả test với -q
    python tests\run.py -v     # chạy verbose
"""
import sys
import pytest


def main(argv=None):
    argv = argv or sys.argv[1:]
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
