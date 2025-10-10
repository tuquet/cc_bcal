# Dự án Buoc Chan An Lac — Scripts quick reference

Tệp này tóm tắt các script hữu ích trong `package.json` để chạy các phần chính của pipeline (tạo episode, render video, chạy Whisper/WhisperX aligner).

Mọi ví dụ dưới đây dùng PowerShell (Windows). Khi gọi npm script và muốn truyền flag tới script Node, đặt `--` sau tên script.

## Scripts chính

- `npm run generate`
  - Chạy `scripts/generate-episodes.mjs` để tạo/cập nhật metadata cho episodes.
  - Ví dụ:
```powershell
npm run generate
```

- `npm run video`
  - Chạy `scripts/video-generator.mjs` để build video cho một episode theo cấu hình mặc định.
  - Ví dụ:
```powershell
npm run video
```

- `npm run video:test` / `npm run video:final` / `npm run video:all` / `npm run video:batch`
  - Các chế độ của `video-generator.mjs` cho test, final hoặc batch rendering.
  - Ví dụ (render tất cả):
```powershell
npm run video:all
```

- `npm run align:all`
  - Chạy `scripts/whisperx-batch.mjs` để scan `episodes/*/audio`, chạy Whisper+WhisperX (thông qua Docker image `cc_bcal-whisperx`) và sinh `.srt` từ output JSON.
  - Các flag thông dụng (đặt sau `--`):
    - `--dry-run` — chỉ liệt kê files, không chạy Docker.
    - `--force` — ghi đè `.srt` hiện có.
    - `--require-gpu` — yêu cầu chạy với GPU (Docker sẽ thêm `--gpus all`).
    - `--parallel N` — chạy N job song song (cẩn thận với GPU/VRAM).
  - Ví dụ:
```powershell
# dry-run (liệt kê)
npm run align:all -- --dry-run

# chạy thực tế, ghi đè nếu cần
npm run align:all -- --force

# chạy yêu cầu GPU
npm run align:all -- --require-gpu
```

## WhisperX JSON

- Aligner sẽ ghi một file JSON cạnh file audio: `<base>.whisperx.json` (ví dụ `voiceover.whisperx.json`).
- Batch script dùng JSON này để sinh `.srt` bằng `scripts/write-srt-from-outjson.mjs`. JSON được giữ lại để debug.

## Docker

- Build image aligner (từ gốc repo):
```powershell
docker build -t cc_bcal-whisperx -f docker/whisperx/Dockerfile .
```

- Ví dụ chạy container trực tiếp (mount repo vào `/workspace`):
```powershell
docker run --gpus all --rm -v "${PWD}:/workspace" cc_bcal-whisperx --audio /workspace/episodes/1.tam-nhu-mat-ho/audio/voiceover.mp3 --output /workspace/episodes/1.tam-nhu-mat-ho/audio/voiceover.whisperx.json
```

## Ghi chú vận hành

- Lần chạy đầu sẽ tải model (nặng) — mount cache host (`%USERPROFILE%\.cache`) để tái sử dụng.
- Nếu dùng GPU, đảm bảo Docker Desktop/WSL2 đã bật GPU support hoặc cài NVIDIA container toolkit.
- Batch mặc định skip audio đã có `.srt` — dùng `--force` để ghi đè.

## Tài liệu thêm
- Xem `whisperx-pipeline.md` trong repo để có hướng dẫn nhanh và các mẹo vận hành chi tiết.

---
Tệp này chỉ là tóm tắt nhanh các lệnh thường dùng. Muốn mình mở rộng thành phần hướng dẫn chi tiết (ví dụ PowerShell helper scripts, CI snippets), nói mình biết thông tin bạn muốn bổ sung.
