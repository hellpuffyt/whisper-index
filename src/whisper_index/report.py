"""Render search results and index summaries."""

from __future__ import annotations

import json

from .engine import Index
from .types import Hit


def format_timestamp(seconds: float) -> str:
    """H:MM:SS, matching what a player's seek control expects."""
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"


def render_hits_json(hits: list[Hit]) -> str:
    return json.dumps([hit.to_dict() for hit in hits], indent=2)


def render_hits_text(hits: list[Hit]) -> str:
    if not hits:
        return "no matches"
    lines = []
    for hit in hits:
        segment = hit.segment
        lines.append(
            f"{segment.source} @ {format_timestamp(segment.start)}  "
            f"(score {hit.score:g})"
        )
        lines.append(f"  {_highlight(segment.text, hit.match_spans)}")
    return "\n".join(lines)


def _highlight(text: str, spans: tuple[tuple[int, int], ...]) -> str:
    """Wrap each match span in **markers**, working back-to-front so
    earlier insertions never shift the offsets of later ones."""
    out = text
    for start, end in sorted(spans, reverse=True):
        out = f"{out[:start]}**{out[start:end]}**{out[end:]}"
    return out


def render_index_summary(index: Index) -> str:
    sources = sorted({s.source for s in index.segments})
    duration = sum(s.end - s.start for s in index.segments)
    return (
        f"{len(index.segments)} segment(s) across {len(sources)} file(s), "
        f"{len(index.postings)} distinct term(s), "
        f"{format_timestamp(duration)} of transcript indexed"
    )
