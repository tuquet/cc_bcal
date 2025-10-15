# small runner to invoke asset_check_once from app_core
import sys, os
repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo not in sys.path:
    sys.path.insert(0, repo)
from app_core import asset_check_once

if __name__ == '__main__':
    s = asset_check_once()
    print('summary:', s)
