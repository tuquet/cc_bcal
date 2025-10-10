## GPU Docker aligner (WhisperX)

This document shows how to build and run the Whisper+WhisperX aligner inside Docker with GPU access.

Prerequisites:
- NVIDIA GPU and drivers installed (nvidia-smi should show the card).
- Docker Engine with NVIDIA Container Toolkit (nvidia-docker) configured so `--gpus` works.

Build the image (from repository root):

```bash
docker build -t cc_bcal-aligner:latest .
```

Run the aligner (mount the repo so the container can access audio and scripts):

```bash
docker run --gpus all --rm -v "$(pwd):/workspace" cc_bcal-aligner:latest --audio /workspace/episodes/1.tam-nhu-mat-ho/audio/voiceover.mp3 --output /workspace/out-whisperx.json
```

If you prefer docker-compose:

```bash
docker compose run --rm --gpus all aligner --audio /workspace/episodes/1.tam-nhu-mat-ho/audio/voiceover.mp3 --output /workspace/out-whisperx.json
```

Notes:
- The image installs a CUDA-capable PyTorch wheel (CUDA 12.9). If your system uses a different CUDA runtime, change the Dockerfile's pip index accordingly.
- The container will execute `/workspace/scripts/whisperx_align.py` with the same CLI you use locally.
