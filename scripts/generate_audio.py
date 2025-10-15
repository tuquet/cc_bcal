import argparse
import json
import sys
from pathlib import Path

import requests

from services.ai33 import AI33Service
from utils import get_project_path


def download_file(url: str, destination: Path):
    """Tải file từ URL và lưu vào đường dẫn đích."""
    try:
        print(f"📥 Đang tải file từ: {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ Đã tải file thành công: {destination}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi tải file: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Tạo file audio.mp3 từ content.txt bằng dịch vụ TTS.")
    parser.add_argument("script_file", type=Path, help="Đường dẫn đến file kịch bản JSON (ví dụ: data/1.json).")
    parser.add_argument("service", nargs='?', default="elevenlabs", choices=["minimax", "elevenlabs"], help="Dịch vụ TTS để sử dụng (mặc định: elevenlabs).")
    parser.add_argument("--voice-id", default="3VnrjnYrskPMDsapTr8X", help="ID của giọng nói để sử dụng cho TTS (mặc định: 3VnrjnYrskPMDsapTr8X).")
    parser.add_argument("--force", action="store_true", help="Buộc tạo lại audio ngay cả khi file đã tồn tại.")
    args = parser.parse_args()

    # --- 1. Xác định đường dẫn ---
    if not args.script_file.exists():
        print(f"❌ Lỗi: File kịch bản không tồn tại: {args.script_file}", file=sys.stderr)
        sys.exit(1)

    with open(args.script_file, 'r', encoding='utf-8') as f:
        script_data = json.load(f)

    project_path = get_project_path(script_data)
    content_path = project_path / "content.txt"
    audio_output_path = project_path / "audio.mp3"

    if not content_path.exists():
        print(f"❌ Không tìm thấy file 'content.txt' trong: {project_path}", file=sys.stderr)
        sys.exit(1)

    if audio_output_path.exists() and not args.force:
        print(f"⏩ Bỏ qua, file audio.mp3 đã tồn tại. Sử dụng --force để tạo lại.")
        sys.exit(0)

    # --- 2. Đọc nội dung và khởi tạo service ---
    text_content = content_path.read_text(encoding='utf-8')
    if not text_content.strip():
        print("❌ File content.txt rỗng, không có gì để tạo audio.", file=sys.stderr)
        sys.exit(1)

    try:
        service = AI33Service()
    except ValueError as e:
        print(f"❌ Lỗi khởi tạo service: {e}", file=sys.stderr)
        sys.exit(1)

    # --- 3. Gửi yêu cầu TTS và xử lý kết quả ---
    try:
        task_id = None
        print(f"🚀 Đang gửi yêu cầu TTS đến dịch vụ '{args.service}'...")
        if args.service == "minimax":
            task_id = service.minimax_tts(text=text_content, voice_id=args.voice_id)
        elif args.service == "elevenlabs":
            task_id = service.elevenlabs_tts(text=text_content, voice_id=args.voice_id)

        if not task_id:
            raise Exception("Không nhận được task_id từ API.")

        print(f"✅ Yêu cầu đã được gửi với Task ID: {task_id}")

        print("\n⏳ Bắt đầu thăm dò kết quả...")
        result = service.poll_for_result(task_id)

        audio_url = result.get("metadata", {}).get("audio_url")
        if audio_url:
            download_file(audio_url, audio_output_path)
            print("\n🎉 Hoàn thành tạo file audio.mp3!")
        else:
            print("❌ Không tìm thấy 'audio_url' trong kết quả trả về.", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"\n💥 Đã xảy ra lỗi trong quá trình tạo audio: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
