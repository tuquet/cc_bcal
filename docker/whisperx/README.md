# WhisperX Docker (gpu)

This folder contains the Dockerfile and helper files to build a GPU-capable container that runs the project's `scripts/whisperx_align.py` script.

Build (run from repo root):

```bash
docker build -t cc_bcal-whisperx -f docker/whisperx/Dockerfile .
```

Run (example):

```bash
docker run --gpus all --rm -v "$(pwd):/workspace" cc_bcal-whisperx --audio /workspace/episodes/1.tam-nhu-mat-ho/audio/voiceover.mp3 --output /workspace/out-whisperx.json
```

Or using docker-compose from this folder:

```bash
cd docker/whisperx
docker compose up --build
```
