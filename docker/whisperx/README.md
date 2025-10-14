# WhisperX Docker (GPU)

Thư mục này chứa `Dockerfile` và các tập trợ giúp để xây dựng một container có hỗ trợ GPU, dùng để chạy script `scripts/whisperx_align.py` của dự án.

Cách build (chạy từ thư mục gốc của repo):

```bash
docker build -t cc_bcal-whisperx -f docker/whisperx/Dockerfile .
```

Ví dụ lệnh chạy container:

```bash
docker run --gpus all --rm -v "$(pwd):/workspace" cc_bcal-whisperx --audio /workspace/episodes/1.tam-nhu-mat-ho/audio.mp3 --output /workspace/out-whisperx.json
```

Ghi chú:
- Tùy theo shell trên Windows, bạn có thể thay `$(pwd)` bằng `${PWD}` trong PowerShell khi mount volume.
- Lệnh trên sẽ chạy script alignment bên trong container; kết quả JSON sẽ được ghi ra `out-whisperx.json` trong thư mục gốc (vì chúng ta mount repo vào `/workspace`).

Hoặc sử dụng docker-compose từ thư mục này:

```bash
cd docker/whisperx
docker compose up --build
```