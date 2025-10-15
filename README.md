# Dự án Buoc Chan An Lac — Hướng dẫn sử dụng Pipeline

Dự án này sử dụng một chuỗi các script Python để tự động hóa quy trình tạo video từ kịch bản thô.

## Cài đặt ban đầu

Trước khi chạy pipeline, bạn cần đảm bảo môi trường đã được thiết lập đúng cách.

### 1. Yêu cầu hệ thống
- Python 3.7+
- Docker (đã cài đặt và đang chạy)

### 2. Tạo Môi trường ảo và Cài đặt Thư viện (Khuyến khích)
Sử dụng môi trường ảo (`.venv`) là một cách tốt nhất để quản lý các gói phụ thuộc cho dự án.

1.  **Tạo môi trường ảo:** (Chỉ cần làm một lần trong thư mục gốc dự án)
    ```powershell
    python -m venv .venv
    ```
2.  **Kích hoạt môi trường ảo:** (Cần làm mỗi khi mở một terminal mới để làm việc với dự án)
    ```powershell
    .\.venv\Scripts\activate
    ```
3.  **Cài đặt các gói cần thiết từ `requirements.txt`:**
```powershell
pip install -r requirements.txt
```

### 3. Build Docker Image (Quan trọng)
Bước nhận dạng giọng nói (Alignment) yêu cầu một Docker image tùy chỉnh. Hãy build image này một lần bằng lệnh sau từ thư mục gốc của dự án:
```powershell
docker build -t cc_bcal-whisperx -f whisperx/Dockerfile .
```

## Quy trình làm việc

Quy trình tạo video từ kịch bản thô bao gồm 3 bước chính. Bạn cần thực hiện các bước này theo đúng thứ tự cho mỗi episode.

### Bước 1: Tạo cấu trúc Episode

Sau khi tạo các file kịch bản `.json` trong thư mục `data/`, hãy chạy script sau để tự động tạo cấu trúc thư mục và các file cần thiết trong `episodes/`.
```powershell
python generate_episodes.py
```

- Ví dụ chạy container trực tiếp (mount repo vào `/workspace`):
```powershell
docker run --gpus all --rm -v "${PWD}:/workspace" cc_bcal-whisperx --audio /workspace/episodes/1.tam-nhu-mat-ho/audio.mp3 --output /workspace/episodes/1.tam-nhu-mat-ho/audio.whisperx.json
```

## Ghi chú vận hành

- Lần chạy đầu sẽ tải model (nặng) — mount cache host (`%USERPROFILE%\.cache`) để tái sử dụng.
- Nếu dùng GPU, đảm bảo Docker Desktop/WSL2 đã bật GPU support hoặc cài NVIDIA container toolkit.
- Batch mặc định skip audio đã có `.srt` — dùng `--force` để ghi đè.

## Tài liệu thêm
- Xem `whisperx-pipeline.md` trong repo để có hướng dẫn nhanh và các mẹo vận hành chi tiết.

---
Tệp này chỉ là tóm tắt nhanh các lệnh thường dùng. Muốn mình mở rộng thành phần hướng dẫn chi tiết (ví dụ PowerShell helper scripts, CI snippets), nói mình biết thông tin bạn muốn bổ sung.
