# Hướng dẫn sử dụng Pipeline

Dự án này sử dụng một chuỗi các script Python để tự động hóa quy trình tạo video từ kịch bản thô.
https://docs.google.com/spreadsheets/d/1fX-4yWSzuetkaQQY6Nvh7FdP2vkcWI6G/edit?gid=1417908852#gid=1417908852

## Cài đặt ban đầu

Trước khi chạy pipeline, bạn cần đảm bảo môi trường đã được thiết lập đúng cách.

### 1. Yêu cầu hệ thống
- Python 3.7+
- Docker (đã cài đặt và đang chạy)

### 2. Tạo Môi trường ảo và Cài đặt Thư viện (Khuyến khích)
Sử dụng môi trường ảo (`venv`) là một cách tốt nhất để quản lý các gói phụ thuộc cho dự án.

1.  **Tạo môi trường ảo:** (Chỉ cần làm một lần trong thư mục gốc dự án)
    ```bash
    python -m venv venv
    ```
2.  **Kích hoạt môi trường ảo:** (Cần làm mỗi khi mở một terminal mới để làm việc với dự án)
    ```bash
    .\venv\Scripts\activate
    ```
3.  **Cài đặt các gói cần thiết từ `requirements.txt`:**
```bash
pip install -r requirements.txt
```

### 3. Build Docker Image (Quan trọng)
Bước nhận dạng giọng nói (Alignment) yêu cầu một Docker image tùy chỉnh. Hãy build image này một lần bằng lệnh sau từ thư mục gốc của dự án:
```bash
docker build -t cc_bcal-whisperx -f whisperx/Dockerfile .
```

## Quy trình làm việc

Quy trình tạo video từ kịch bản thô bao gồm 5 bước chính. Bạn cần thực hiện các bước này theo đúng thứ tự cho mỗi project.

### Bước 1: Tạo cấu trúc Project (`1_generate_episodes.py`)

Sau khi tạo các file kịch bản `.json` trong thư mục `data/`, hãy chạy script sau để tự động tạo cấu trúc thư mục và các file cần thiết trong `projects/`.
```bash
python 1_generate_episodes.py
```

Bước 2: Tạo ra kịch bản chi tiết cho từng scenes từ cái file audio khi dự án đã chuẩn bị xong.

```bash
python process_align_episodes.py 13.sinh-lao-benh-tu-la-ban-chat-tu-nhien
```

Bước 3: Tạo ra template video capcut sử dụng CapCut API services tại localhost:9001
```bash
python process_video_draft.py 13.sinh-lao-benh-tu-la-ban-chat-tu-nhien
```