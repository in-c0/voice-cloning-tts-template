# Voice Cloning TTS SaaS — XTTS‑v2 + Dia (optional)

A **voice cloning** TTS web app template for **podcasts & YouTube**:

- ✅ **XTTS‑v2** (zero‑shot cloning) — great English quality out of the box
- ✅ **Chunking** for long scripts + smart joins (with configurable pauses)
- ✅ **Seed control** (best‑effort for XTTS; deterministic for Dia)
- ✅ **Nice UI** (React + Vite + Tailwind) with engine, seed, chunking controls
- ✅ **FastAPI API** (binary WAV response), CORS, health/engines endpoints
- ✅ **Dockerfile (GPU)** and local dev instructions

> **Dia support is optional**. XTTS works out of the box. Dia requires an extra install (see below).

---

## 1) Local dev (recommended)

### Backend
```bash
# Python 3.10+; NVIDIA GPU recommended (CUDA 12.x)
cd backend
python -m venv .venv
source .venv/bin/activate # OR .\.venv\Scripts\Activate # for windows


# 1. Install PyTorch for your CUDA / CPU (choose one):
#   CUDA 12.1 (Linux):
pip install --index-url https://download.pytorch.org/whl/cu121 torch torchaudio --upgrade
#   or CPU only (works but slow):
# pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --upgrade

# 2. Install rest
pip install -r requirements.txt

# 3. (Optional) Dia 1.6B support via Transformers main
pip install git+https://github.com/huggingface/transformers.git
pip install git+https://github.com/nari-labs/dia.git  #(or alternatively, clone directly from git)
git clone https://github.com/nari-labs/dia.git
cd dia
pip install -e .

You'll need to make sure you have a matching CUDA build of PyTorch. If CUDA version is recent, PyTorch might not have published the exact version yet. 
e.g. as of August 2025, if you have CUDA 12.6 installed, it should be backward-compatible with cu121 and cu124. You may need to run:
```bash
pip uninstall torch torchaudio -y
pip cache purge
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
python -c "import torch; print(torch.version.cuda, torch.cuda.is_available())" # for verification
```

# 4. Run the API
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm i
# Point the UI to your API (default http://localhost:8000)
# (Optional) echo "VITE_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open http://localhost:5173

---

## 2) Docker (GPU)

```bash
# Build
docker build -t voice-saas:gpu -f docker/Dockerfile .
# Run with NVIDIA runtime
docker run --gpus all -p 8000:8000 -p 5173:5173 --env VITE_API_URL=http://localhost:8000 voice-saas:gpu
```

This image serves API on :8000 and the built UI on :5173.

---

## 3) Usage notes

- **Consent checkbox** is built‑in. Only upload your own voice or voices with explicit permission.
- **Chunking**: The backend splits long text on punctuation into ~`max_chars` blocks, adds a short configurable **pause** between chunks, and stitches WAVs. For XTTS, this is more stable than one huge pass.
- **Seed control**:
  - **Dia**: deterministic across runs when you set a seed.
  - **XTTS**: we set `random`, `numpy`, and `torch` seeds for best‑effort repeatability. Exact determinism isn't guaranteed by the high‑level API.
- **Dia cloning**: For the most faithful cloning, provide a short (5–10 s) **audio prompt** *and its transcript*. Put the transcript first, then your script. The UI exposes an optional transcript field.

---

## 4) Endpoints

- `POST /api/tts` (multipart): fields `engine`, `text`, `language`, `seed?`, `speed?`, `max_chars?`, `pause_ms?`, `split_strategy?`, `transcript?`, and file `reference?`. Returns `audio/wav`.
- `GET  /api/engines` → which engines are loaded and basic caps.
- `GET  /api/health`  → `{ ok: true }`

---

## 5) Licenses & attribution

- **XTTS‑v2** weights: **Coqui Public Model License (CPML)**. Review and comply.
- **Dia 1.6B** code/weights: **Apache‑2.0** (check upstream README for any restrictions).
- This template is MIT‑licensed. See `LICENSE`.

Enjoy! 🚀
