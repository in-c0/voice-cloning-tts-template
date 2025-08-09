from __future__ import annotations
import os, tempfile, random
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

import numpy as np
from pydub import AudioSegment

def _set_seeds(seed: Optional[int]):
    if seed is None:
        return
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    try:
        torch.use_deterministic_algorithms(False)  # best-effort; strict determinism may slow things down
    except Exception:
        pass

@dataclass
class SynthesisRequest:
    text: str
    language: str = "en"
    speaker_wav: Optional[str] = None
    seed: Optional[int] = None
    speed: float = 1.0

class BaseEngine:
    name: str
    def synthesize_many(self, reqs: List[SynthesisRequest], pause_ms: int = 120) -> str:
        """Synthesize multiple chunks and concatenate into a single wav file.
        Returns path to the output wav file.
        """
        paths: List[str] = []
        for r in reqs:
            p = self.synthesize_one(r)
            paths.append(p)

        # Concatenate with small pauses
        silence = AudioSegment.silent(duration=pause_ms)
        final = None
        for p in paths:
            seg = AudioSegment.from_file(p)
            final = seg if final is None else final + silence + seg

        out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        final.export(out_path, format="wav")
        # cleanup
        for p in paths:
            try: os.remove(p)
            except Exception: pass
        return out_path

    def synthesize_one(self, req: SynthesisRequest) -> str:
        raise NotImplementedError

class XTTSEngine(BaseEngine):
    name = "xtts-v2"
    def __init__(self):
        # Lazy import to avoid heavy import at module import time
        from TTS.api import TTS
        import torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # You can pin a specific version like 'xtts_v2.0.2'
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

    def synthesize_one(self, req: SynthesisRequest) -> str:
        _set_seeds(req.seed)  # best-effort
        out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        kwargs: Dict[str, Any] = dict(
            text=req.text,
            file_path=out_path,
            language=req.language,
            split_sentences=False,  # we chunk at the API layer
        )
        if req.speaker_wav:
            kwargs["speaker_wav"] = [req.speaker_wav]
        # speed is supported by low-level API; TTS.api exposes it in newer versions
        # if not available, this arg will be ignored.
        kwargs["speed"] = req.speed
        self.tts.tts_to_file(**kwargs)  # type: ignore
        return out_path

class DiaEngine(BaseEngine):
    name = "Dia-1.6B-0626"

    def __init__(self):
        from transformers import AutoProcessor, DiaForConditionalGeneration
        import torch

        # Choose device safely (no CUDA hardcoding)
        device = "cuda" if getattr(torch, "cuda", None) and torch.cuda.is_available() else "cpu"

        model_checkpoint = "nari-labs/Dia-1.6B-0626"

        try:
            # Load once, with appropriate dtype
            dtype = torch.float16 if device == "cuda" else torch.float32
            self.processor = AutoProcessor.from_pretrained(model_checkpoint)
            self.model = (
                DiaForConditionalGeneration
                .from_pretrained(model_checkpoint, torch_dtype=dtype)
                .to(device)
            )
        except AssertionError as e:
            # If a CUDA-less torch slipped through but device was "cuda", fall back to CPU
            device = "cpu"
            self.processor = AutoProcessor.from_pretrained(model_checkpoint)
            self.model = (
                DiaForConditionalGeneration
                .from_pretrained(model_checkpoint, torch_dtype=torch.float32)
                .to(device)
            )
        except Exception as e:
            # Surface a concise error to the API layer
            raise RuntimeError(f"Dia init failed: {e}")

        # Stash for later
        self.device = device
        self.AutoProcessor = AutoProcessor
        self.DiaForConditionalGeneration = DiaForConditionalGeneration
        self.torch = torch

    def synthesize_one(self, req: SynthesisRequest) -> str:
        _set_seeds(req.seed)
        text = req.text if req.text.strip().startswith("[S1]") else f"[S1] {req.text}"
        inputs = self.processor(text=[text], padding=True, return_tensors="pt").to(self.device)

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=2048,
            guidance_scale=3.0,
            temperature=1.4,
            top_p=0.9,
            top_k=45,
            do_sample=True,
        )

        # Save directly to WAV (libsndfile-friendly)
        wav_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        self.processor.save_audio(outputs, wav_path)
        return wav_path

