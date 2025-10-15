#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def main():
    """
    Sets up episode directories and files from raw data JSONs.
    This script replaces `setup-episodes.mjs`.
    """
    repo_root = Path(__file__).parent
    data_dir = repo_root / "data"
    episodes_dir = repo_root / "episodes"
    template_path = repo_root / "assets" / "video-template.json"

    # 1. Load all raw data JSON files
    json_files = sorted(list(data_dir.glob("*.json")))

    if not json_files:
        print("❌ Không tìm thấy dữ liệu JSON nào để xử lý trong thư mục 'data/'", file=sys.stderr)
        sys.exit(1)

    print(f"🎬 Tổng cộng có {len(json_files)} tập để xử lý\n")

    # 2. Load the video template
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            video_template = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Lỗi khi đọc file video-template.json: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Create the main episodes directory
    if not episodes_dir.exists():
        episodes_dir.mkdir(parents=True)
        print(f"📁 Đã tạo thư mục chung: {episodes_dir}")

    # 4. Process each data file
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            item = json.load(f)

        folder_name = f"{item.get('id')}.{item.get('meta', {}).get('alias', 'untitled')}"
        episode_path = episodes_dir / folder_name

        # Create episode directory
        # Use exist_ok=True to avoid race conditions and simplify code
        episode_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Đảm bảo thư mục tồn tại: {episode_path.relative_to(repo_root)}")

        # Create content.txt
        content_txt_path = episode_path / "content.txt"
        if not content_txt_path.exists():
            script_texts = [
                scene.get("narration", "") for scene in item.get("scenes", []) if scene.get("narration")
            ]
            txt_content = "\n\n".join(script_texts)
            content_txt_path.write_text(txt_content, encoding='utf-8')
            print(f"✍️  Đã tạo file: {content_txt_path.relative_to(repo_root)}")
        else:
            print(f"⏩ Bỏ qua, file đã tồn tại: {content_txt_path.relative_to(repo_root)}")

        # Create capcut-api.json
        script_json_path = episode_path / "capcut-api.json"
        if not script_json_path.exists():
            item["generation_params"] = video_template
            with open(script_json_path, 'w', encoding='utf-8') as f:
                json.dump(item, f, indent=2, ensure_ascii=False)
            print(f"📝 Đã tạo file: {script_json_path.relative_to(repo_root)}")
        else:
            print(f"⏩ Bỏ qua, file đã tồn tại: {script_json_path.relative_to(repo_root)}")
        print("-" * 20)

    print("\n🎉 Hoàn thành tạo cấu trúc thư mục và file!")

if __name__ == "__main__":
    main()