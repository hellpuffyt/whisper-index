"""whisper-index: a searchable, timestamped index over Whisper transcripts."""

from __future__ import annotations

__version__ = "0.1.0"

from .types import Hit, Segment

__all__ = ["Hit", "Segment", "__version__"]
