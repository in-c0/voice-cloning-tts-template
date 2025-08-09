import re
from typing import List

def _sentences(text: str) -> List[str]:
    # Simple sentence split on ., !, ? while preserving punctuation
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]

def chunk_text(text: str, max_chars: int = 280, strategy: str = "punct") -> List[str]:
    """Chunk text for TTS.
    strategy: 'punct' (default) or 'none'
    """
    if strategy == "none" or max_chars <= 0:
        return [text]

    sents = _sentences(text)
    chunks = []
    cur = []
    cur_len = 0
    for s in sents:
        if cur_len + len(s) + (1 if cur else 0) <= max_chars:
            cur.append(s)
            cur_len += len(s) + (1 if cur else 0)
        else:
            if cur:
                chunks.append(' '.join(cur))
            cur = [s]
            cur_len = len(s)
    if cur:
        chunks.append(' '.join(cur))
    return chunks
