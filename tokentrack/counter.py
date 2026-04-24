"""Token counting — tiktoken for OpenAI, estimator fallback for others."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    lower = model.lower()

    if any(k in lower for k in ("gpt", "o3", "o4", "davinci", "turbo")):
        count = _count_tiktoken(text, model)
        if count is not None:
            return count

    return _estimate_tokens(text)


def count_file(path: Path, model: str = "gpt-4o") -> tuple[int, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    tokens = count_tokens(text, model)
    lines = len(text.splitlines())
    return tokens, lines


def _count_tiktoken(text: str, model: str) -> Optional[int]:
    try:
        import tiktoken
    except ImportError:
        return None

    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        try:
            enc = tiktoken.get_encoding("o200k_base")
        except Exception:
            return None

    return len(enc.encode(text))


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)
