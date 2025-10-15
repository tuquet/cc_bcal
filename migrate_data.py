import os
import json
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if project_root not in sys.path:
    sys.path.append(project_root)

from main import app
from database import db
from models import Script

DATA_FOLDER = os.path.join(project_root, 'data')

def migrate():
    with app.app_context():
        db.create_all()
        print("Bắt đầu quá trình di chuyển dữ liệu...")
        for filename in os.listdir(DATA_FOLDER):
            if filename.endswith('.json'):
                file_path = os.path.join(DATA_FOLDER, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                alias = data.get('meta', {}).get('alias')
                if not alias:
                    print(f"⚠️  Bỏ qua {filename}: thiếu 'meta.alias'.")
                    continue

                if Script.query.filter_by(alias=alias).first():
                    print(f"⏩ Bỏ qua {filename}: Alias '{alias}' đã tồn tại.")
                else:
                    new_script = Script()
                    new_script.script_data = data
                    new_script.status = 'new'
                    db.session.add(new_script)
                    print(f"✅ Đã thêm {filename} (Alias: {alias}) vào database.")
        db.session.commit()
        print("\n🎉 Di chuyển dữ liệu hoàn tất!")

if __name__ == '__main__':
    migrate()
