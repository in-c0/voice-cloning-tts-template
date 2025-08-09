# GPU Dockerfile for Voice SaaS Template (XTTS + optional Dia)
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive     PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y \
    python3.11 python3.11-venv python3-pip \
    ffmpeg curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Backend
COPY backend /app/backend
RUN python3.11 -m pip install --upgrade pip  && pip install -r /app/backend/requirements.txt

# Install PyTorch (CUDA 12.1) + torchaudio (adjust if needed)
RUN pip install --index-url https://download.pytorch.org/whl/cu121 torch torchaudio

# Optional (Dia + transformers main). Comment out to save build time.
RUN pip install git+https://github.com/huggingface/transformers.git \    && pip install git+https://github.com/nari-labs/dia.git || true

# --- Frontend
COPY frontend /app/frontend
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \ && apt-get install -y nodejs \ && cd /app/frontend \ && npm ci \ && npm run build

EXPOSE 8000 5173

# Run API and serve built UI via Vite preview for simplicity
WORKDIR /app/backend
CMD uvicorn app:app --host 0.0.0.0 --port 8000 & \    cd /app/frontend && npx vite preview --host 0.0.0.0 --port 5173
