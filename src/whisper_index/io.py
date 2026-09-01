"""Load transcript segments from Whisper's own output formats.

Three formats, because Whisper (and whisper.cpp, and most wrappers around
it) can emit any of them: the native JSON with a ``segments`` array, SRT,
and WebVTT. This tool never runs speech recognition itself — it indexes
output that already exists, which is what makes it a from-scratch, zero
runtime dependency, deterministic tool rather than one that needs a model.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import cast

from .errors import TranscriptFormatError
from .types import Segment

_SRT_TIME = re.compile(
    r"(?:(\d+):)?(\d{1,2}):(\d{2})[,.](\d{1,3})\s*-->\s*"
    r"(?:(\d+):)?(\d{1,2}):(\d{2})[,.](\d{1,3})"
)


def discover(paths: list[str | Path]) -> list[Path]:
    """Expand files and directories into a sorted list of transcript paths."""
    found: set[Path] = set()
    suffixes = {".json", ".srt", ".vtt"}
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            for candidate in path.rglob("*"):
                if candidate.suffix.lower() in suffixes and candidate.is_file():
                    found.add(candidate)
        elif path.suffix.lower() in suffixes:
            found.add(path)
        else:
            raise TranscriptFormatError(
                f"{path}: not a transcript (.json/.srt/.vtt) or directory"
            )
    return sorted(found)


def load(path: str | Path) -> list[Segment]:
    path = Path(path)
    suffix = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as err:
        raise TranscriptFormatError(f"cannot read {path}: {err.strerror or err}") from err

    if suffix == ".json":
        segments = _load_json(text, str(path))
    elif suffix == ".srt":
        segments = _load_subtitle(text, str(path), comma_millis=True)
    elif suffix == ".vtt":
        segments = _load_subtitle(text, str(path), comma_millis=False)
    else:
        raise TranscriptFormatError(
            f"unsupported input {path.name!r}: expected .json, .srt or .vtt"
        )
    if not segments:
        raise TranscriptFormatError(f"{path}: no segments found")
    return segments


def _load_json(text: str, source: str) -> list[Segment]:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as err:
        raise TranscriptFormatError(f"{source}: not valid JSON: {err.msg}") from err
    if not isinstance(raw, dict) or "segments" not in raw:
        raise TranscriptFormatError(f"{source}: no 'segments' array; not Whisper JSON")
    segments_raw = raw["segments"]
    if not isinstance(segments_raw, list):
        raise TranscriptFormatError(f"{source}: 'segments' is not a list")

    segments = []
    for index, item in enumerate(segments_raw):
        if not isinstance(item, dict):
            raise TranscriptFormatError(f"{source}: segment {index} is not an object")
        try:
            start = float(item["start"])
            end = float(item["end"])
            body = str(item["text"]).strip()
        except (KeyError, TypeError, ValueError) as err:
            raise TranscriptFormatError(
                f"{source}: segment {index} missing start/end/text: {err}"
            ) from err
        if body:
            segments.append(
                Segment(source=source, index=index, start=start, end=end, text=body)
            )
    return segments


def _load_subtitle(text: str, source: str, *, comma_millis: bool) -> list[Segment]:
    blocks = re.split(r"\r?\n\r?\n+", text.strip())
    segments = []
    index = 0
    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        # SRT numbers each cue; VTT's optional cue identifier looks the
        # same. Either way, the first line that is not a timestamp line
        # is skipped rather than parsed as one.
        timing_line = next((line for line in lines if "-->" in line), None)
        if timing_line is None:
            continue
        match = _SRT_TIME.search(timing_line)
        if not match:
            raise TranscriptFormatError(f"{source}: unparseable timing line {timing_line!r}")
        raw_groups = match.groups()
        groups = cast(
            "tuple[str | None, str, str, str, str | None, str, str, str]", raw_groups
        )
        start = _timestamp_seconds(groups[:4])
        end = _timestamp_seconds(groups[4:])
        body_lines = lines[lines.index(timing_line) + 1 :]
        stripped_lines = (_strip_tags(line) for line in body_lines)
        body = " ".join(stripped_lines).strip()
        if body:
            segments.append(
                Segment(source=source, index=index, start=start, end=end, text=body)
            )
            index += 1
    return segments


def _timestamp_seconds(parts: tuple[str | None, str, str, str]) -> float:
    hours_raw, minutes, seconds, millis = parts
    hours = int(hours_raw) if hours_raw else 0
    # SRT/VTT allow 1-3 millisecond digits in the wild; pad to 3 for a
    # consistent fractional value regardless of how many were written.
    millis_value = int(millis.ljust(3, "0")[:3])
    return hours * 3600 + int(minutes) * 60 + int(seconds) + millis_value / 1000


_TAG = re.compile(r"<[^>]+>")


def _strip_tags(line: str) -> str:
    """Drop VTT's inline styling tags (<b>, <i>, <c.color>...) — cosmetic
    markup that has no place in a search index or a highlighted result."""
    return _TAG.sub("", line)
