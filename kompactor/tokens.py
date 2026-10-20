"""Token estimation.

Uses tiktoken when installed (cl100k is close enough to Claude's tokenizer for
relative savings); otherwise a chars/token heuristic. Savings are reported as
ratios, so the absolute calibration matters less than consistency.
"""

import re

try:  # optional dependency
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover - depends on environment
    _ENC = None

_WORDISH = re.compile(r"\w+|[^\w\s]")


def count(text: str) -> int:
    if not text:
        return 0
    if _ENC is not None:
        return len(_ENC.encode(text, disallowed_special=()))
    # Heuristic: Claude averages ~3.5-4 chars/token on code and logs. Blend a
    # char-based and a piece-based estimate so long identifiers and dense
    # punctuation are both handled reasonably.
    pieces = len(_WORDISH.findall(text))
    return max(1, int(0.5 * len(text) / 3.8 + 0.5 * pieces * 0.9))
