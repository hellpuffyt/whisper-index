"""Serialise a built index to and from plain JSON.

JSON, not pickle — an index file is meant to be committed, shared, and
rebuilt-and-diffed; it should never be able to execute code on load.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .engine import Index
from .errors import IndexFormatError
from .types import Segment

FORMAT_VERSION = 1


def to_dict(index: Index) -> dict[str, object]:
    return {
        "format_version": FORMAT_VERSION,
        "segments": [
            {
                "source": s.source,
                "index": s.index,
                "start": s.start,
                "end": s.end,
                "text": s.text,
            }
            for s in index.segments
        ],
        # JSON object keys are strings; segment ids are re-parsed to int on load.
        "postings": {
            term: {str(segment_id): count for segment_id, count in counts.items()}
            for term, counts in index.postings.items()
        },
    }


def from_dict(payload: dict[str, Any]) -> Index:
    try:
        version = payload["format_version"]
        if version != FORMAT_VERSION:
            raise IndexFormatError(
                f"index format version {version} is not supported "
                f"(expected {FORMAT_VERSION})"
            )
        segments = [
            Segment(
                source=item["source"],
                index=item["index"],
                start=item["start"],
                end=item["end"],
                text=item["text"],
            )
            for item in payload["segments"]
        ]
        postings: dict[str, dict[int, int]] = defaultdict(dict)
        for term, counts in payload["postings"].items():
            for segment_id, count in counts.items():
                postings[term][int(segment_id)] = count
        return Index(segments=segments, postings=postings)
    except (KeyError, TypeError, ValueError) as err:
        raise IndexFormatError(f"index file is malformed: {err}") from err


def save(index: Index, path: str | Path) -> None:
    Path(path).write_text(json.dumps(to_dict(index), indent=2), encoding="utf-8")


def load(path: str | Path) -> Index:
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as err:
        raise IndexFormatError(f"cannot read {path}: {err.strerror or err}") from err
    except json.JSONDecodeError as err:
        raise IndexFormatError(f"{path}: not valid JSON: {err.msg}") from err
    if not isinstance(raw, dict):
        raise IndexFormatError(f"{path}: not an index file")
    return from_dict(raw)
