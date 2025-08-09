from __future__ import annotations
import io, os, tempfile, traceback
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from tts.chunking import chunk_text
from tts.engines import XTTSEngine, DiaEngine, SynthesisRequest

app = FastAPI(title="Voice SaaS Template", version="1.0.0")

# CORS for local dev; tighten in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-init engines
_xtts = None
_dia = None

def get_xtts():
    global _xtts
    if _xtts is None:
        _xtts = XTTSEngine()
    return _xtts

def get_dia():
    global _dia
    if _dia is None:
        _dia = DiaEngine()
    return _dia

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/engines")
def engines():
    caps = []
    try:
        get_xtts()
        caps.append({"engine":"xtts","status":"ok"})
    except Exception as e:
        caps.append({"engine":"xtts","status":"error","error":str(e)})
    try:
        get_dia()
        caps.append({"engine":"dia","status":"ok"})
    except Exception as e:
        caps.append({"engine":"dia","status":"error","error":str(e)})
    return {"engines": caps}

@app.post("/api/tts")
async def tts_api(
    engine: str = Form("xtts"),
    text: str = Form(...),
    language: str = Form("en"),
    seed: int | None = Form(None),
    speed: float = Form(1.0),
    max_chars: int = Form(280),
    pause_ms: int = Form(120),
    split_strategy: str = Form("punct"),
    transcript: str | None = Form(None),
    reference: UploadFile | None = File(None),
    consent: bool = Form(False),
):
    if not consent:
        raise HTTPException(status_code=400, detail="Please confirm you have consent to use this voice.")
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")

    # Save reference wav if sent
    ref_path = None
    if reference is not None:
        ref_bytes = await reference.read()
        if len(ref_bytes) > 0:
            ref_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
            with open(ref_path, "wb") as f:
                f.write(ref_bytes)

    # Chunk the text
    chunks: List[str] = chunk_text(text, max_chars=max_chars, strategy=split_strategy)

    # Build synthesis requests
    reqs = [SynthesisRequest(text=c, language=language, speaker_wav=ref_path, seed=seed, speed=speed) for c in chunks]

    # Choose engine
    try:
        if engine == "xtts":
            out = get_xtts().synthesize_many(reqs, pause_ms=pause_ms)
        elif engine == "dia":
            # Dia ignores language, uses [S1] tagging. transcript can be prepended client-side if desired.
            out = get_dia().synthesize_many(reqs, pause_ms=pause_ms)
        else:
            raise HTTPException(status_code=400, detail="Unknown engine. Use 'xtts' or 'dia'.")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    # Return WAV
    return FileResponse(out, media_type="audio/wav", filename="speech.wav")
