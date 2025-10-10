#!/bin/bash
set -euo pipefail

echo "WhisperX aligner container started. Args: $@"

# If user passed no args, drop to an interactive shell
if [ "$#" -eq 0 ]; then
  echo "No args passed. To run alignment: docker run --gpus all -v \"/host/path/to/repo:/workspace\" image --audio /workspace/episodes/..../audio/voiceover.mp3 --output /workspace/out.json"
  exec bash
fi

# If the user explicitly wants a shell or arbitrary command, run it
case "$1" in
  bash|sh|/bin/bash|/bin/sh)
    exec "$@"
    ;;
  *)
    ;;
esac

# Choose Python executable (prefer python3)
: ${PYTHON:=}
if command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON="python"
else
  PYTHON="python"
fi

# Resolve aligner script location. Priority:
# 1) ALIGNER_PATH env var (if set and file exists)
# 2) /workspace/docker/whisperx/whisperx_align.py
# 3) /workspace/docker/whisperx/scripts/whisperx_align.py
# 4) /workspace/whisperx_align.py
# 5) fail with helpful message

## Simple aligner resolution
# If user provided ALIGNER_PATH, treat absolute as-is, otherwise prefix with /workspace
if [ -n "${ALIGNER_PATH:-}" ]; then
  if [[ "${ALIGNER_PATH}" = /* ]]; then
    try_path="${ALIGNER_PATH}"
  else
    try_path="/workspace/${ALIGNER_PATH#./}"
  fi
  if [ -f "${try_path}" ]; then
    ALIGNER="${try_path}"
    echo "Using ALIGNER_PATH -> ${ALIGNER}"
  else
    echo "Warning: ALIGNER_PATH set but file not found: '${ALIGNER_PATH}' (tried '${try_path}')" >&2
  fi
fi

# If no ALIGNER yet, look in /workspace first (non-recursive), then /workspace/docker/whisperx
if [ -z "${ALIGNER:-}" ]; then
  # Prefer explicit whisperx_align.py if present
  if [ -f /workspace/whisperx_align.py ]; then
    ALIGNER=/workspace/whisperx_align.py
  elif [ -f /workspace/docker/whisperx/whisperx_align.py ]; then
    ALIGNER=/workspace/docker/whisperx/whisperx_align.py
  else
    # Find any whisperx-related python file in /workspace (non-recursive)
    for f in /workspace/*whisperx*.py; do
      if [ -f "$f" ]; then
        ALIGNER="$f"
        break
      fi
    done
    # Fallback: first .py in /workspace
    if [ -z "${ALIGNER:-}" ]; then
      for f in /workspace/*.py; do
        if [ -f "$f" ]; then
          ALIGNER="$f"
          break
        fi
      done
    fi
  fi
fi

# Final sanity checks
if [ -n "${ALIGNER:-}" ]; then
  if [ ! -r "${ALIGNER}" ]; then
    echo "Error: aligner exists but is not readable: ${ALIGNER}" >&2
    exit 2
  fi
else
  echo "Error: no aligner script found. Set ALIGNER_PATH or mount repository into /workspace containing a .py aligner script" >&2
  exit 2
fi

echo "Running aligner: ${PYTHON} ${ALIGNER} $@"
exec "${PYTHON}" "${ALIGNER}" "$@"
