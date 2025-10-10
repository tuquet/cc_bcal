# Hướng dẫn pipeline WhisperX / aligner (nhanh)

Tập hợp nhanh các lệnh và cách dùng để chạy pipeline dựa trên Docker + Node mà repo đã cung cấp.

Mục tiêu
- Dùng Docker image `cc_bcal-whisperx` để chạy Whisper + WhisperX alignment trên audio (.mp3).
- Dùng Node script `scripts/whisperx-batch.mjs` để chạy batch, scan `episodes/*/audio`, chuyển `.mp3` -> `.srt`.

Chuẩn bị
- Cài Docker và GPU runtime nếu muốn dùng GPU (nvidia-container-toolkit).
- Tạo cache Hugging Face trên host để tránh tải model mỗi lần: `%USERPROFILE%\.cache` (helper PowerShell script sẽ tạo tự động nếu cần).

Lệnh quan trọng

- Chạy một folder audio (dry-run):
```powershell
node scripts/whisperx-batch.mjs episodes/1.tam-nhu-mat-ho/audio --dry-run
```

- Scan toàn bộ `episodes/*/audio` (dry-run):
```powershell
node scripts/whisperx-batch.mjs dummy --scan-episodes --dry-run
```

- Chạy thực tế, yêu cầu GPU (serial):
```powershell
node scripts/whisperx-batch.mjs dummy --scan-episodes --require-gpu
```

- Chạy song song (cẩn thận với GPU trên máy chỉ có 1 GPU):
```powershell
node scripts/whisperx-batch.mjs dummy --scan-episodes --parallel 2
```

- Nếu muốn ghi đè .srt hiện có:
```powershell
node scripts/whisperx-batch.mjs dummy --scan-episodes --force
```

PowerShell helper
- `run-whisperx.ps1` và `run-whisperx-batch.ps1` hỗ trợ tạo host cache (`%USERPROFILE%\.cache`) và chạy container với mount cache để tránh tải model lại.

Vấn đề thường gặp
- Nếu thấy tiến trình tải model (ví dụ 461 MB) — đó là lần đầu model được lưu. Đảm bảo mount cache host (`%USERPROFILE%\.cache`) để tái sử dụng.
- Nếu dùng `--require-gpu` với `--parallel>1` trên 1 GPU: có thể quá tải VRAM — khuyến nghị serial GPU jobs (`--parallel 1 --require-gpu`).

Gợi ý nâng cao
- Muốn tự động hóa CI/local scheduling: dùng `--scan-episodes` kết hợp `--dry-run` trong cron/task scheduler.
- Muốn tối ưu: tôi có thể bổ sung báo cáo tóm tắt (success/fail) hoặc queue thông minh phân loại GPU/CPU.

----
File liên quan
- `scripts/whisperx-batch.mjs` — Node batch runner (scan, parallel, dry-run, force, require-gpu)
- `scripts/write-srt-from-outjson.mjs` — chuyển out-whisperx.json -> .srt
- `run-whisperx.ps1`, `run-whisperx-batch.ps1` — helper PowerShell để mount host cache và chạy container
- `docker/whisperx/whisperx_align.py` — Python aligner used inside container

Nếu muốn, tôi sẽ commit các thay đổi và tạo 1 commit message rõ ràng (đã sẵn sàng để commit).
