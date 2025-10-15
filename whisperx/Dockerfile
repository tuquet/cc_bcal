FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Basic tools and Python 3.11
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates wget git ffmpeg build-essential curl \
    python3.11 python3.11-venv python3.11-distutils python3-pip \
 && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3.11 /usr/bin/python || true
# Ensure `python3` also points to python3.11 so `python3 -m pip` and runtime imports use the
# same interpreter. This avoids packages being installed for a different python binary.
RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 || true
# Ensure pip for python3.11 is available
RUN python -m pip install --upgrade pip setuptools wheel || python3 -m pip install --upgrade pip setuptools wheel

# Install a CUDA-capable PyTorch wheel (CUDA 12.9 index). This matches modern NVIDIA drivers.
# If you prefer a different CUDA tag (12.1), change the index-url accordingly.
RUN python -m pip install --no-cache-dir "torch==2.8.0+cu129" torchvision torchaudio --index-url https://download.pytorch.org/whl/cu129

# Copy requirements and project into the image. requirements.txt lives under docker/whisperx in the repo.
COPY whisperx/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /workspace
# Copy only the alignment tooling and runtime entrypoint to keep the image small.
# Audio files and episode assets should be mounted at runtime from the host.
COPY whisperx /workspace/whisperx

# Make entrypoint executable (entrypoint lives at whisperx/docker-entrypoint.sh in the repo)
RUN chmod +x /workspace/whisperx/docker-entrypoint.sh

ENTRYPOINT ["/workspace/whisperx/docker-entrypoint.sh"]
