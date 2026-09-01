"""Core model: transcript segments, the built index, and search hits."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    """One timestamped span of a transcript — Whisper's own unit of output.

    Times are seconds, float, matching Whisper JSON / SRT / VTT directly, so
    a hit's ``start`` can be handed straight to a player's seek call.
    """

    source: str
    index: int
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Hit:
    """One search result: the segment it came from, plus why it matched."""

    segment: Segment
    #: Term-frequency score within this segment, for ranking.
    score: float
    #: Character offsets of each match within `segment.text`, for highlighting.
    match_spans: tuple[tuple[int, int], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.segment.source,
            "index": self.segment.index,
            "start": self.segment.start,
            "end": self.segment.end,
            "text": self.segment.text,
            "score": self.score,
            "match_spans": [list(span) for span in self.match_spans],
        }
