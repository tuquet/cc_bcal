import os, json, sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent
settings = repo_root / 'settings.json'
if not settings.exists():
    print('settings.json not found')
    sys.exit(1)
try:
    cfg = json.loads(settings.read_text(encoding='utf-8'))
    proj = cfg.get('project_folder')
    if not proj:
        print('project_folder not set in settings.json')
        sys.exit(1)
    # resolve absolute if necessary
    p = Path(proj)
    if not p.is_absolute():
        p = (repo_root / proj).resolve()
    print('searching under', str(p))
    count = 0
    for dirpath, dirnames, filenames in os.walk(str(p)):
        for f in filenames:
            if f.lower().endswith(('.mp3', '.m4a', '.wav')):
                print(os.path.join(dirpath, f))
                count += 1
                if count >= 200:
                    print('...stopping after 200 matches')
                    sys.exit(0)
    print('total found', count)
except Exception as e:
    print('error reading settings.json:', e)
    sys.exit(1)
