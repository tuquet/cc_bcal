#!/usr/bin/env python3
"""
Generate project folders from scripts stored in the database.

This script should be run from the repository root. It imports the Flask app
defined in `main.py` to obtain the DB bindings and model definitions.

Behavior:
 - Find all Script rows with status == 'new'
 - For each, create episode folder, content.txt and capcut-api.json (using generation_params if present)
 - If creation succeeds for a script, set its status to 'prepared' and commit immediately
 - If creation fails for a script, leave its status as-is and continue

Usage:
    python scripts/generate_from_db.py [--force] [--limit N]

"""
import argparse
import json
import sys
from pathlib import Path

# Import app and DB models from main so we can reuse the same DB config
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app  # noqa: E402
from database import db  # noqa: E402
from models import Script  # noqa: E402
from utils import get_project_path  # noqa: E402


def process_script_item(repo_root: Path, script: Script, force: bool = False) -> bool:
    """Create folder/files for one Script. Return True on success."""
    try:
        data = script.script_data
        # In the DB-backed model, script_data already shapes meta, scenes etc.
        episode_path = get_project_path(data, repo_root)
        episode_path.mkdir(parents=True, exist_ok=True)

        # content.txt
        content_txt_path = episode_path / "content.txt"
        script_texts = [scene.get('narration', '') for scene in data.get('scenes', []) if scene.get('narration')]
        txt_content = "\n\n".join(script_texts)
        def _display(p: Path) -> str:
            try:
                return str(p.relative_to(repo_root))
            except Exception:
                return str(p)

        if content_txt_path.exists() and not force:
            print(f"⏩ Bỏ qua content.txt (tồn tại): {_display(content_txt_path)}")
        else:
            content_txt_path.write_text(txt_content, encoding='utf-8')
            print(f"✍️  Đã ghi: {_display(content_txt_path)}")

        # capcut-api.json
        script_json_path = episode_path / "capcut-api.json"
        generation_params = data.get('generation_params')
        payload = data.copy()
        if generation_params:
            payload['generation_params'] = generation_params

        if script_json_path.exists() and not force:
            print(f"⏩ Bỏ qua capcut-api.json (tồn tại): {_display(script_json_path)}")
        else:
            with open(script_json_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            print(f"📝 Đã ghi: {_display(script_json_path)}")

        return True
    except Exception as e:
        print(f"❌ Lỗi khi xử lý script id={script.id} alias={script.alias}: {e}")
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description='Tạo projects từ DB (Script.status == new)')
    parser.add_argument('--force', action='store_true', help='Ghi đè file nếu đã tồn tại')
    parser.add_argument('--limit', type=int, default=0, help='Giới hạn số script xử lý (0 = không giới hạn)')
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]

    # Run inside Flask app context so SQLAlchemy is configured
    with app.app_context():

        query = Script.query.filter_by(status='new').order_by(Script.id)
        if args.limit and args.limit > 0:
            query = query.limit(args.limit)

        new_scripts = query.all()
        if not new_scripts:
            print('Không tìm thấy script status=new trong database.')
            return 0

        print(f'Tìm thấy {len(new_scripts)} script mới.')

        processed = 0
        for s in new_scripts:
            print(f"Xử lý id={s.id} alias={s.alias} ...")
            ok = process_script_item(repo_root, s, force=args.force)
            if ok:
                try:
                    s.status = 'prepared'
                    db.session.add(s)
                    db.session.commit()
                    print(f"✅ Đã chuyển trạng thái id={s.id} -> prepared")
                except Exception as e:
                    db.session.rollback()
                    print(f"❌ Không thể cập nhật DB cho id={s.id}: {e}")
            else:
                print(f"⚠️  Bỏ qua cập nhật trạng thái cho id={s.id} do lỗi xử lý")
            processed += 1

        print(f"Hoàn thành. Đã xử lý {processed} script(s).")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
