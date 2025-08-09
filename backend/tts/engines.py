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
    name = "dia-1.6b"
    def __init__(self):
        try:
            from transformers import AutoProcessor
            from dia.hf import DiaForConditionalGeneration  # provided by the dia package
        except Exception as e:
            raise RuntimeError("Dia not installed. Install transformers main + dia: \n\n"                               "pip install git+https://github.com/huggingface/transformers.git\n"                               "pip install git+https://github.com/nari-labs/dia.git\n\n"                               f"Original error: {e}")
        import torch
        self.torch = torch
        self.AutoProcessor = AutoProcessor
        self.DiaForConditionalGeneration = DiaForConditionalGeneration
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = AutoProcessor.from_pretrained("nari-labs/Dia-1.6B")
        self.model = DiaForConditionalGeneration.from_pretrained("nari-labs/Dia-1.6B").to(self.device)

    def synthesize_one(self, req: SynthesisRequest) -> str:
        _set_seeds(req.seed)
        # Dia expects [S1]/[S2] tags. For single-speaker narration, start with [S1].
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
        # Save as MP3 then convert to WAV to match XTTS output for stitching
        mp3_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        self.processor.save_audio(outputs, mp3_path)
        from pydub import AudioSegment
        wav_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        AudioSegment.from_file(mp3_path).export(wav_path, format="wav")
        os.remove(mp3_path)
        return wav_path
