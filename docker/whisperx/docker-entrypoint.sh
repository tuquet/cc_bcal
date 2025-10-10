#!/bin/bash
set -euo pipefail

echo "WhisperX aligner container started. Running whisperx aligner with args: $@"

if [ "$#" -eq 0 ]; then
  echo "Usage: docker run --gpus all -v \"/host/path/to/repo:/workspace\" image --audio /workspace/episodes/1.../audio/voiceover.mp3 --output /workspace/out.json"
  exec bash
fi

# Prefer the whisperx script located under docker/whisperx/scripts when repo is mounted at /workspace
if [ -f /workspace/docker/whisperx/whisperx_align.py ]; then
  exec python /workspace/docker/whisperx/whisperx_align.py "$@"
elif [ -f /workspace/docker/whisperx/scripts/whisperx_align.py ]; then
  exec python /workspace/docker/whisperx/scripts/whisperx_align.py "$@"
else
  exec python /workspace/whisperx_align.py "$@"
fi
