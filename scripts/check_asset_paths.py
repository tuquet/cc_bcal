# Quick checker for episode paths and audio presence
import sys, os, json, sqlite3
from pathlib import Path
# ensure repo root in sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
from utils import get_project_path

DB = os.path.join(repo_root, 'database.db')
conn = sqlite3.connect(DB)
cur = conn.cursor()
# adjust ids to check if you want
ids = [1,2,3]
for id_ in ids:
    # Select columns that exist in the current schema
    cur.execute('SELECT id, title, alias, status, duration, meta, scenes, audio_status, images_status FROM scripts WHERE id=?', (id_,))
    row = cur.fetchone()
    if not row:
        print(f'script id={id_} not found in DB')
        continue
    sid, title, alias, status, duration, meta_json, scenes_json, audio_status, images_status = row
    try:
        meta = json.loads(meta_json) if meta_json else {}
    except Exception as e:
        print(f'script id={sid} meta parse error: {e}')
        meta = {}
    try:
        scenes = json.loads(scenes_json) if scenes_json else []
    except Exception as e:
        print(f'script id={sid} scenes parse error: {e}')
        scenes = []

    data = {
        'id': sid,
        'meta': meta,
        'scenes': scenes,
        'duration': duration,
        'audio_status': audio_status,
        'images_status': images_status,
    }

    path = get_project_path(data, Path(repo_root))
    print('---')
    print('id=', sid)
    print('title=', title)
    print('alias=', alias)
    print('status=', status)
    print('resolved path=', path)
    print('path exists=', path.exists())
    audio = path / 'audio.mp3'
    print('audio path=', audio)
    print('audio exists=', audio.exists())
    # list audio files in folder
    if path.exists():
        mp3s = list(path.glob('*.mp3'))
        print('mp3 files in folder:', [str(p.name) for p in mp3s])
        # recursive search for any audio files in subtree
        rmp3s = list(path.rglob('*.mp3'))
        if rmp3s:
            print('mp3 files recursive:', [str(p.relative_to(repo_root)) for p in rmp3s])
        else:
            print('no mp3 found recursively under this folder')
        # also check parent folder for audio
        parent_mp3s = list(path.parent.glob('*.mp3'))
        if parent_mp3s:
            print('mp3 files in parent folder:', [str(p.relative_to(repo_root)) for p in parent_mp3s])
        # also list subfolders top-level
        items = list(path.iterdir())
        print('top-level items:', [p.name for p in items])
    else:
        print('folder not present, skipping listing')
conn.close()
print('done')
