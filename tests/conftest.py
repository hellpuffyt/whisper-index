"""Builders for segments and indexes, used across the suite."""

from __future__ import annotations

from whisper_index.types import Segment


def segment(
    index: int, text: str, start: float = 0.0, end: float = 1.0, source: str = "t.json"
) -> Segment:
    return Segment(source=source, index=index, start=start, end=end, text=text)
