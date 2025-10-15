import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import requests
from dotenv import load_dotenv


class AI33Service:
    """
    Một client Python để tương tác với API của ai33.pro, hỗ trợ các dịch vụ
    của ElevenLabs, Minimax và các tác vụ chung.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.ai33.pro"):
        """
        Khởi tạo AI33Service client.

        Args:
            api_key: API key (xi-api-key) của bạn. Nếu không được cung cấp,
                     nó sẽ được đọc từ biến môi trường 'AI33_API_KEY'.
            base_url: URL gốc của API (không bao gồm /v1 hay /v1m).
        """
        # Load environment variables from .env file
        load_dotenv()

        self.api_key = api_key or os.getenv("AI33_API_KEY")
        if not self.api_key:
            raise ValueError("API key is not provided. Please pass it to the constructor or set the 'AI33_API_KEY' environment variable.")
        self.base_url = base_url
        self.default_headers = {
            "xi-api-key": self.api_key,
        }

    def _make_request(self, method: str, endpoint: str, headers: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """
        Hàm riêng tư để gửi các yêu cầu HTTP đến API.

        Args:
            method: Phương thức HTTP ('GET', 'POST', 'DELETE').
            endpoint: Đường dẫn endpoint đầy đủ (ví dụ: '/v1/tasks').
            headers: Headers tùy chỉnh cho request. Nếu không có, sẽ dùng header mặc định.
            **kwargs: Các tham số khác cho `requests.request` (json, data, files).

        Returns:
            Phản hồi JSON từ API dưới dạng dictionary.
        """
        url = f"{self.base_url}{endpoint}"
        request_headers = headers if headers is not None else self.default_headers.copy()
        if 'json' in kwargs and 'Content-Type' not in request_headers:
            request_headers['Content-Type'] = 'application/json'

        try:
            response = requests.request(method, url, headers=request_headers, **kwargs)
            response.raise_for_status()
            # Handle empty response for DELETE requests
            if response.status_code == 204 or not response.content:
                return {"success": True}
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            raise

    def _log_task_id(self, task_id: str, task_type: str):
        """Ghi lại task_id vào file log."""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "ai33.log")
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} - TYPE: {task_type}, TASK_ID: {task_id}\n"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

    # --- Common Task and User Methods ---

    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Truy xuất trạng thái và kết quả của một tác vụ dựa trên ID."""
        return self._make_request("GET", f"/v1/task/{task_id}")

    def list_tasks(self, page: int = 1, limit: int = 20, task_type: Optional[str] = None) -> Dict[str, Any]:
        """Liệt kê các tác vụ của người dùng với phân trang và bộ lọc."""
        params = {"page": page, "limit": limit}
        if task_type:
            params["type"] = task_type
        return self._make_request("GET", "/v1/tasks", params=params)

    def delete_tasks(self, task_ids: List[str]) -> Dict[str, Any]:
        """Xóa các tác vụ và nhận lại tín dụng (nếu có)."""
        return self._make_request("POST", "/v1/task/delete", json={"task_ids": task_ids})

    def get_credits(self) -> Dict[str, Any]:
        """Lấy tổng số tín dụng hiện có của người dùng."""
        return self._make_request("GET", "/v1/credits")

    def health_check(self) -> Dict[str, Any]:
        """Kiểm tra trạng thái sức khỏe của các dịch vụ nền."""
        return self._make_request("GET", "/v1/health-check")

    def poll_for_result(self, task_id: str, timeout: int = 300, interval: int = 5) -> Dict[str, Any]:
        """
        Thăm dò (poll) kết quả của một tác vụ cho đến khi nó hoàn thành hoặc xảy ra lỗi.

        Args:
            task_id: ID của tác vụ cần thăm dò.
            timeout: Thời gian chờ tối đa (tính bằng giây).
            interval: Khoảng thời gian giữa mỗi lần thăm dò (tính bằng giây).

        Returns:
            Dictionary chứa kết quả cuối cùng của tác vụ khi hoàn thành.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            task = self.get_task(task_id)
            try:
                task = self.get_task(task_id)
                status = task.get("status")
                progress = task.get('progress') or 0
                print(f"Polling task {task_id}... Status: {status}, Progress: {progress}%")

                if status == "done":
                    return task
                if status == "error":
                    raise Exception(f"Task failed with error: {task.get('error_message', 'Unknown error')}")

                time.sleep(interval)
            except requests.exceptions.HTTPError as e:
                # Retry on 5xx server errors, fail on 4xx client errors
                if 500 <= e.response.status_code < 600:
                    print(f"⚠️ Gặp lỗi máy chủ ({e.response.status_code}), sẽ thử lại sau {interval} giây...")
                    time.sleep(interval)
                    continue
                else:
                    raise  # Re-raise client errors (e.g., 401, 404)

        raise TimeoutError(f"Task {task_id} timed out after {timeout} seconds.")

    # --- ElevenLabs Methods ---

    def elevenlabs_tts(self, text: str, voice_id: str, model_id: str = "eleven_multilingual_v2", output_format: str = "mp3_44100_128") -> str:
        """Gửi tác vụ TTS đến dịch vụ của ElevenLabs."""
        endpoint = f"/v1/text-to-speech/{voice_id}"
        params = {"output_format": output_format}
        payload = {
            "text": text,
            "model_id": model_id,
            "with_transcript": False,
        }
        response = self._make_request("POST", endpoint, params=params, json=payload)
        if not response.get("success"):
            raise Exception("Failed to submit TTS task.")
        task_id = response["task_id"]
        self._log_task_id(task_id, "elevenlabs_tts")
        return task_id

    def dub_audio(self, file_path: Union[str, os.PathLike], target_lang: str, num_speakers: int = 0, source_lang: str = "auto") -> str:
        """Gửi tác vụ lồng tiếng (dubbing) cho một file audio."""
        headers = self.default_headers.copy()
        # `requests` sẽ tự đặt Content-Type là multipart/form-data khi có `files`
        
        data = {
            "num_speakers": str(num_speakers),
            "disable_voice_cloning": "false",
            "source_lang": source_lang,
            "target_lang": target_lang,
        }
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            response = self._make_request("POST", "/v1/task/dubbing", headers=headers, data=data, files=files)
        
        if not response.get("success"):
            raise Exception("Failed to submit dubbing task.")
        task_id = response["task_id"]
        self._log_task_id(task_id, "dubbing")
        return task_id

    def list_elevenlabs_models(self) -> Dict[str, Any]:
        """Lấy danh sách các mô hình tổng hợp giọng nói của ElevenLabs."""
        return self._make_request("GET", "/v1/models")

    def list_elevenlabs_voices(self) -> Dict[str, Any]:
        """Lấy danh sách các giọng nói được đề xuất của ElevenLabs."""
        # Lưu ý endpoint này là v2
        return self._make_request("GET", "/v2/voices")

    def list_shared_voices(self) -> Dict[str, Any]:
        """Lấy danh sách các giọng nói được chia sẻ của ElevenLabs."""
        return self._make_request("GET", "/v1/shared-voices")

    # --- Minimax Methods ---

    def get_minimax_config(self) -> Dict[str, Any]:
        """Lấy các cài đặt cấu hình chung từ dịch vụ Minimax."""
        return self._make_request("GET", "/v1m/common/config")

    def minimax_tts(self, text: str, voice_id: str, model: str = "speech-2.5-hd-preview", vol: float = 1.0, pitch: int = 0, speed: float = 1.0) -> str:
        """Gửi tác vụ TTS đến dịch vụ của Minimax."""
        payload = {
            "text": text,
            "model": model,
            "voice_setting": {
                "voice_id": voice_id,
                "vol": vol,
                "pitch": pitch,
                "speed": speed,
            },
            "language_boost": "Auto",
            "with_transcript": False,
        }
        response = self._make_request("POST", "/v1m/task/text-to-speech", json=payload)
        if not response.get("success"):
            raise Exception("Failed to submit Minimax TTS task.")
        task_id = response["task_id"]
        self._log_task_id(task_id, "minimax_tts")
        return task_id

    def clone_voice(self, file_path: Union[str, os.PathLike], voice_name: str, preview_text: str, language_tag: str, gender_tag: str, need_noise_reduction: bool = False) -> Dict[str, Any]:
        """Tạo một bản sao giọng nói (voice clone) từ một file audio."""
        headers = self.default_headers.copy()
        data = {
            "voice_name": voice_name,
            "preview_text": preview_text,
            "language_tag": language_tag,
            "need_noise_reduction": str(need_noise_reduction).lower(),
            "gender_tag": gender_tag,
        }
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            response = self._make_request("POST", "/v1m/voice/clone", headers=headers, data=data, files=files)
        
        if not response.get("success"):
            raise Exception("Failed to submit voice clone task.")
        return response

    def delete_voice_clone(self, voice_clone_id: str) -> Dict[str, Any]:
        """Xóa một giọng nói đã được nhân bản."""
        return self._make_request("DELETE", f"/v1m/voice/clone/{voice_clone_id}")

    def list_voice_clones(self) -> Dict[str, Any]:
        """Lấy danh sách tất cả các giọng nói đã nhân bản của người dùng."""
        return self._make_request("GET", "/v1m/voice/clone")

    def list_minimax_voices(self, page: int = 1, page_size: int = 30, tag_list: Optional[List[str]] = None) -> Dict[str, Any]:
        """Lấy danh sách các giọng nói có sẵn từ Minimax."""
        payload = {
            "page": page,
            "page_size": page_size,
            "tag_list": tag_list or [],
        }
        return self._make_request("POST", "/v1m/voice/list", json=payload)