#!/usr/bin/env python3
import argparse
from utils import get_project_path
import json
import re
import subprocess
import os
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import requests

# --- Cấu hình ---
# Port cho API của CapCut. Script gốc dùng 9001, bạn có thể thay đổi nếu cần.
CAPCUT_API_PORT = 9001
CAPCUT_API_BASE_URL = f"http://127.0.0.1:{CAPCUT_API_PORT}"

# Port cho server file cục bộ. Script gốc dùng 9002.
FILE_SERVER_PORT = 9002
FILE_SERVER_BASE_URL = f"http://127.0.0.1:{FILE_SERVER_PORT}"
from socketserver import TCPServer


class FileServerThread(threading.Thread):
    """Chạy một HTTP server đơn giản trong một thread riêng biệt."""

    def __init__(self, directory: Path, port: int):
        super().__init__()
        self.directory = directory
        self.port = port
        self.server: Optional[TCPServer] = None
        self.daemon = True  # Thread sẽ tự thoát khi chương trình chính kết thúc

    def run(self):
        # Thay đổi thư mục làm việc để server phục vụ đúng file
        os.chdir(self.directory)
        handler = SimpleHTTPRequestHandler
        self.server = TCPServer(("", self.port), handler)
        print(f"🔌 Local file server started at {FILE_SERVER_BASE_URL}")
        print(f"   Serving files from: {self.directory.resolve()}")
        self.server.serve_forever()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("🔌 Local file server stopped.")


def call_api(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Gửi request đến CapCut API và trả về kết quả."""
    url = f"{CAPCUT_API_BASE_URL}{endpoint}"
    print(f"📞 Calling API: {endpoint}...")
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()  # Ném lỗi nếu status code là 4xx hoặc 5xx
        result = response.json()
        # The API uses a 'success' boolean field, not a 'code' field.
        if not result.get("success"):
            error_message = result.get('message') or result.get('error', 'Unknown API error')
            raise Exception(f"API Error: {error_message}. Full response: {result}")
        return result
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Failed to connect to CapCut API at {url}. Is CapCut running? Error: {e}") from e


class CapCutGenerator:
    """Lớp quản lý việc tạo video CapCut, tương đương với script Node.js."""

    def __init__(self, episode_dir: Path, ratio: str = "9:16"):
        self.episode_dir = episode_dir.resolve()
        self.ratio = ratio
        self.file_server: Optional[FileServerThread] = None
        self.draft_id: Optional[str] = None
        self.script_data: Optional[Dict[str, Any]] = None
    # store total audio duration in seconds (server API expects seconds)
        self.total_audio_duration_s = 0.0
        self.width = 0
        self.height = 0
        # Server sẽ phục vụ file từ thư mục gốc của dự án
        self.base_serve_dir = self.episode_dir.parent.parent

    def _get_http_path(self, file_path: Path) -> str:
        """Chuyển đổi đường dẫn file cục bộ thành URL HTTP."""
        # Đảm bảo file_path là absolute trước khi tính relative
        abs_file_path = file_path if file_path.is_absolute() else self.base_serve_dir / file_path
        relative_path = abs_file_path.resolve().relative_to(self.base_serve_dir)
        return f"{FILE_SERVER_BASE_URL}/{relative_path.as_posix()}"

    def init(self):
        """Khởi tạo và kiểm tra các file cần thiết."""
        if not self.episode_dir.is_dir():
            raise FileNotFoundError(f"❌ Thư mục episode không tồn tại: {self.episode_dir}")

        script_json_path = self.episode_dir / "capcut-api.json"
        self.audio_path = self.episode_dir / "audio.mp3"

        if not script_json_path.exists():
            raise FileNotFoundError(f"❌ Không tìm thấy file capcut-api.json trong: {self.episode_dir}")
        if not self.audio_path.exists():
            raise FileNotFoundError(f"❌ Không tìm thấy file audio.mp3 trong: {self.episode_dir}")

        with open(script_json_path, 'r', encoding='utf-8') as f:
            self.script_data = json.load(f)

        # Prefer the actual audio file duration (probe) so visuals match audio exactly.
        probed = self._probe_audio_duration(self.audio_path)
        if probed:
            self.total_audio_duration_s = float(probed)
        else:
            # Fallback to capcut-api.json duration if probing fails
            duration_sec = float(self.script_data.get("duration", 0) or 0)
            self.total_audio_duration_s = float(duration_sec)

        dimensions = {
            "9:16": {"width": 1080, "height": 1920},
            "16:9": {"width": 1920, "height": 1080},
        }
        self.width, self.height = dimensions.get(self.ratio, dimensions["16:9"]).values()

    def _probe_audio_duration(self, audio_path: Path) -> Optional[float]:
        """Try multiple methods to get duration (seconds) of audio file.
        Returns float seconds or None.
        """
        # 1) Try imageio_ffmpeg.get_ffprobe_exe()
        try:
            import imageio_ffmpeg
            get_ffprobe = getattr(imageio_ffmpeg, 'get_ffprobe_exe', None)
            if callable(get_ffprobe):
                ffprobe = get_ffprobe()
                if ffprobe:
                    out = subprocess.check_output([ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)], text=True)
                    return float(out.strip())
        except Exception:
            pass

        # 2) Try system ffprobe
        sys_ffprobe = shutil.which('ffprobe')
        if sys_ffprobe:
            try:
                out = subprocess.check_output([sys_ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)], text=True)
                return float(out.strip())
            except Exception:
                pass

        # 3) Try ffmpeg stderr parsing via imageio_ffmpeg.get_ffmpeg_exe()
        try:
            import imageio_ffmpeg
            get_ffmpeg = getattr(imageio_ffmpeg, 'get_ffmpeg_exe', None)
            if callable(get_ffmpeg):
                ffmpeg = get_ffmpeg()
                if ffmpeg:
                    proc = subprocess.run([ffmpeg, '-i', str(audio_path)], capture_output=True, text=True)
                    stderr = proc.stderr or ''
                    m = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', stderr)
                    if m:
                        h, mm, ss = m.groups()
                        return int(h) * 3600 + int(mm) * 60 + float(ss)
        except Exception:
            pass

        # 4) Try system ffmpeg
        sys_ffmpeg = shutil.which('ffmpeg')
        if sys_ffmpeg:
            try:
                proc = subprocess.run([sys_ffmpeg, '-i', str(audio_path)], capture_output=True, text=True)
                stderr = proc.stderr or ''
                m = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', stderr)
                if m:
                    h, mm, ss = m.groups()
                    return int(h) * 3600 + int(mm) * 60 + float(ss)
            except Exception:
                pass

        return None

    def _run_if_enabled(self, module_name: str, action, *args, **kwargs):
        """Helper để chạy một action nếu module được bật."""
        enabled_modules = self.script_data.get("generation_params", {}).get("enabled_modules", [])
        if module_name in enabled_modules:
            action(*args, **kwargs)
        else:
            print(f"⏩ Skipping module '{module_name}'")

    def run(self):
        """Chạy toàn bộ pipeline tạo video."""
        try:
            self.init()
            self.file_server = FileServerThread(self.base_serve_dir, FILE_SERVER_PORT)
            self.file_server.start()
            # Đợi server khởi động
            time.sleep(1)

            print(f"🎬 Creating draft with ratio {self.ratio} ({self.width}x{self.height})")

            # --- BƯỚC 1: TẠO DRAFT ---
            create_draft_response = call_api("/create_draft", {"width": self.width, "height": self.height})
            self.draft_id = create_draft_response.get("output", {}).get("draft_id")
            if not self.draft_id:
                raise ValueError("Không lấy được draft_id từ API")
            print(f"🎉 Draft đã được tạo với ID: {self.draft_id}")

            # --- BƯỚC 2: THÊM AUDIO (luôn chạy) ---
            print("✅ Module 'audio' is enabled. Running...")
            self.add_audio_track()

            # --- BƯỚC 3: THÊM CÁC LỚP HÌNH ẢNH ---
            self._run_if_enabled("background_layer", self.add_background_layer)
            self._run_if_enabled("scene_images", self.add_image_scenes)

            # --- BƯỚC 4: THÊM LOGO & TEXT ---
            self._run_if_enabled("logo", self.add_logo)
            self._run_if_enabled("text_logo", self.add_text_logo)

            # --- BƯỚC 5: THÊM EFFECTS ---
            self._run_if_enabled("fixed_effects", self.add_fixed_effects)
            self._run_if_enabled("random_effects", self.add_random_effects)

            # --- BƯỚC 6: LƯU DRAFT ---
            self.save_draft()

            print("\n\n✨✨✨ PIPELINE HOÀN TẤT! ✨✨✨")

        except Exception as e:
            print("\n💥💥💥 PIPELINE THẤT BẠI! 💥💥💥", file=sys.stderr)
            print(f"Đã xảy ra lỗi trong quá trình thực thi: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            if self.file_server:
                self.file_server.stop()

    # --- Các hàm thêm element, tái tạo logic từ capcut-elements.mjs ---

    def add_audio_track(self):
        # Ensure the audio element duration matches the total audio duration determined from capcut-api.json
        payload = {
            "draft_id": self.draft_id,
            "audio_url": self._get_http_path(self.audio_path),
            "start": 0,
        }
        # Some CapCut API variants expect an explicit 'end' or 'duration' field — include both to be safe
        if getattr(self, 'total_audio_duration_s', None):
            payload["end"] = float(self.total_audio_duration_s)
            payload["duration"] = float(self.total_audio_duration_s)

        call_api("/add_audio", payload)

    def add_background_layer(self):
        params = self.script_data.get("generation_params", {}).get("background_layer", {})
        scenes = self.script_data.get("scenes", [])
        if not scenes or not scenes[0].get("image"):
            print("⏩ Skipping background layer: No scenes or first scene has no image.")
            return

        background_image_path = Path(scenes[0]["image"])
        call_api("/add_video", {
            "draft_id": self.draft_id,
            "video_url": self._get_http_path(background_image_path),
            "start": 0,
            "end": self.total_audio_duration_s,
            "track_name": "background_track",
            "relative_index": -1, # Đặt ở lớp dưới cùng
            "scale_x": params.get("scale", 2.5),
            "scale_y": params.get("scale", 2.5),
            "background_blur": params.get("blur", 3),
        })

    def add_image_scenes(self):
        params = self.script_data.get("generation_params", {}).get("scene_images", {})
        scenes = self.script_data.get("scenes", [])
        
        # Logic "stretch" thời gian giống hệt script Node.js
        valid_scenes = [s for s in scenes if s.get("start") is not None and s.get("end") is not None]
        total_visual_duration_s = sum(s["end"] - s["start"] for s in valid_scenes)

        # stretch_factor: ratio between audio total duration (seconds) and visual total duration (seconds)
        stretch_factor = (self.total_audio_duration_s) / total_visual_duration_s if total_visual_duration_s > 0 else 1

        current_time_s = 0.0
        for i, scene in enumerate(scenes):
            if scene.get("start") is None or scene.get("end") is None or not scene.get("image"):
                print(f"⚠️ Skipping scene {i + 1}: Missing time or image information.")
                continue

            original_duration_s = scene["end"] - scene["start"]
            new_duration_s = original_duration_s * stretch_factor

            call_api("/add_image", {
                "draft_id": self.draft_id,
                "image_url": self._get_http_path(Path(scene["image"])),
                # API expects seconds for start/end
                "start": current_time_s,
                "end": current_time_s + new_duration_s,
                "track_name": "main_track",
                "relative_index": 9, # Đặt trên lớp background
                "scale_x": params.get("scale", 1.2),
                "scale_y": params.get("scale", 1.2),
            })
            current_time_s += new_duration_s

    def add_logo(self):
        params = self.script_data.get("generation_params", {}).get("logo", {})
        logo_path = params.get("path")
        if not logo_path or not Path(logo_path).is_file():
            print(f"⚠️ Logo file not found, skipping: {logo_path}")
            return

        call_api("/add_image", {
            "draft_id": self.draft_id,
            "image_url": self._get_http_path(Path(logo_path)),
            "start": 0,
            "end": self.total_audio_duration_s,
            "track_name": "logo_track",
            "relative_index": 20, # Đặt ở lớp trên cùng
            "scale_x": params.get("scale", 0.1),
            "scale_y": params.get("scale", 0.1),
            "transform_x": params.get("transform_x", 0.9),
            "transform_y": params.get("transform_y", -0.5),
        })

    def add_text_logo(self):
        params = self.script_data.get("generation_params", {}).get("text_logo", {})
        if not params.get("text"):
            print("⏩ Skipping text logo: 'text' property is missing.")
            return

        call_api("/add_text", {
            "type": "text",
            "draft_id": self.draft_id,
            "track_name": "text_logo_track",
            "text": params["text"],
            "start": params.get("start", 0),
            "end": params.get("end", self.total_audio_duration_s),
            "font_size": params.get("font_size", 12),
            "font_color": params.get("font_color", "#FFFFFF"),
            "font_alpha": params.get("font_alpha", 0.6),
            "transform_x": params.get("transform_x", 0),
            "transform_y": params.get("transform_y", 0),
        })

    def add_fixed_effects(self):
        effects = self.script_data.get("generation_params", {}).get("fixed_effects", {}).get("effects", [])
        for effect in effects:
            if not effect.get("effect_type"):
                continue
            call_api("/add_effect", {
                "draft_id": self.draft_id,
                "type": "effect",
                "effect_type": effect["effect_type"],
                "start": 0,
                "end": self.total_audio_duration_s,
                "track_name": effect.get("track_name", "fixed_effect"),
                "relative_index": 1, # Đặt trên lớp nền
                "params": effect.get("params", []),
                "width": self.width,
                "height": self.height,
            })

    def add_random_effects(self):
        # Logic này cần được làm rõ hơn từ API của CapCut
        # Tạm thời bỏ qua vì không có đủ thông tin trong script gốc
        print("⏩ Skipping module 'random_effects': Logic not implemented.")

    def save_draft(self):
        """Lưu draft vào thư mục của CapCut."""
        # API /save_draft sẽ tạo một thư mục draft trong thư mục làm việc hiện tại của server.
        # Chúng ta cần di chuyển nó vào thư mục project của CapCut.
        
        # 1. Xác định đường dẫn đích của CapCut
        capcut_projects_dir = Path.home() / "AppData/Local/CapCut/User Data/Projects/com.lveditor.draft"
        if not capcut_projects_dir.exists():
            print(f"⚠️  Cảnh báo: Không tìm thấy thư mục project của CapCut tại: {capcut_projects_dir}")
            print("   Vui lòng kiểm tra lại đường dẫn nếu bạn cài CapCut ở vị trí khác.")
            # Vẫn tiếp tục để lưu vào thư mục hiện tại
            capcut_projects_dir.mkdir(parents=True, exist_ok=True)

        save_payload = {
            "draft_id": self.draft_id,
            # Tham số này chỉ định nơi server lưu trữ các file media, không phải nơi lưu draft cuối cùng.
            "draft_folder": str(capcut_projects_dir.resolve()),
        }

        print(f"💡 Đang gửi payload tới /save_draft với draft_folder: {capcut_projects_dir}")

        save_response = call_api("/save_draft", save_payload)

        # Phản hồi từ API có cấu trúc lồng nhau: {"output": {"draft_url": "..."}}
        draft_path_str = save_response.get("output", {}).get("draft_url")
        if draft_path_str:
            # draft_url là đường dẫn file mà CapCut trả về.
            print(f"✅ Draft đã được lưu bởi CapCut tại: {draft_path_str}")
        else:
            print(f"⚠️ Không nhận được đường dẫn draft từ API. Phản hồi: {save_response}")


def main():
    parser = argparse.ArgumentParser(description="Generate a CapCut video draft from an episode directory.")
    parser.add_argument("script_file", type=Path, help="Path to the script JSON file (e.g., 'data/1.json').")
    parser.add_argument("--ratio", type=str, default="9:16", choices=["9:16", "16:9"], help="Video aspect ratio (default: 9:16).")

    args = parser.parse_args()

    if not args.script_file.exists():
        print(f"❌ Lỗi: File kịch bản không tồn tại: {args.script_file}", file=sys.stderr)
        sys.exit(1)

    with open(args.script_file, 'r', encoding='utf-8') as f:
        script_data = json.load(f)

    project_path = get_project_path(script_data)

    generator = CapCutGenerator(project_path, args.ratio)
    generator.run()


if __name__ == "__main__":
    main()

"""
-------------------------------------------------------------------------------
HƯỚNG DẪN SỬ DỤNG
-------------------------------------------------------------------------------

Script này được dùng để tạo video nháp trong CapCut từ dữ liệu của một episode.

CÁCH CHẠY:
Mở terminal (PowerShell, Command Prompt, v.v.) trong thư mục gốc của dự án và
thực thi lệnh sau:

1. Chạy cho một episode cụ thể (tỉ lệ 9:16 mặc định):
   python 5_process_video_capcut.py data/1.json

2. Chạy với tỉ lệ khác (16:9):
   python 5_process_video_capcut.py data/1.json --ratio 16:9
"""