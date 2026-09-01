"""Errors the CLI reports as exit code 1."""

from __future__ import annotations


class WhisperIndexError(Exception):
    """Base class for user-facing input/usage failures."""


class TranscriptFormatError(WhisperIndexError):
    """A transcript file could not be read in any supported format."""


class IndexFormatError(WhisperIndexError):
    """An index file could not be read, or is the wrong format version."""
