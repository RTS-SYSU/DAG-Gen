from __future__ import annotations

from typing import Optional

from .errors import StageError

DEFAULT_TIMING_REPEATS = 10


def normalize_timing_repeats(repeats: Optional[int]) -> int:
    value = DEFAULT_TIMING_REPEATS if repeats is None else int(repeats)
    if value < 1:
        raise StageError(f"timing repeats must be >= 1, got: {value}")
    return value
