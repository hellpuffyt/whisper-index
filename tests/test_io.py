from __future__ import annotations

import json
from pathlib import Path

import pytest

from whisper_index import io
from whisper_index.errors import TranscriptFormatError


def write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


class TestWhisperJson:
    def test_loads_segments(self, tmp_path: Path) -> None:
        doc = {"segments": [{"start": 0.0, "end": 1.5, "text": " hello world "}]}
        segments = io.load(write(tmp_path / "a.json", json.dumps(doc)))
        assert len(segments) == 1
        assert segments[0].text == "hello world"
        assert segments[0].start == 0.0
        assert segments[0].end == 1.5

    def test_segment_index_matches_position(self, tmp_path: Path) -> None:
        doc = {
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "a"},
                {"start": 1.0, "end": 2.0, "text": "b"},
            ]
        }
        segments = io.load(write(tmp_path / "a.json", json.dumps(doc)))
        assert [s.index for s in segments] == [0, 1]

    def test_empty_text_segments_are_dropped(self, tmp_path: Path) -> None:
        doc = {
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "   "},
                {"start": 1.0, "end": 2.0, "text": "real content"},
            ]
        }
        segments = io.load(write(tmp_path / "a.json", json.dumps(doc)))
        assert len(segments) == 1
        assert segments[0].text == "real content"

    def test_missing_segments_key_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(TranscriptFormatError, match="not Whisper JSON"):
            io.load(write(tmp_path / "a.json", json.dumps({"text": "whole doc"})))

    def test_not_json_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(TranscriptFormatError, match="not valid JSON"):
            io.load(write(tmp_path / "a.json", "{oops"))

    def test_segment_missing_a_required_field_is_named(self, tmp_path: Path) -> None:
        doc = {"segments": [{"start": 0.0, "text": "no end field"}]}
        with pytest.raises(TranscriptFormatError, match="segment 0"):
            io.load(write(tmp_path / "a.json", json.dumps(doc)))

    def test_no_segments_at_all_is_an_error(self, tmp_path: Path) -> None:
        with pytest.raises(TranscriptFormatError, match="no segments found"):
            io.load(write(tmp_path / "a.json", json.dumps({"segments": []})))


class TestSrt:
    def test_loads_numbered_cues(self, tmp_path: Path) -> None:
        content = (
            "1\n00:00:00,000 --> 00:00:02,500\nHello world\n\n"
            "2\n00:00:02,500 --> 00:00:05,000\nSecond cue\n"
        )
        segments = io.load(write(tmp_path / "a.srt", content))
        assert [s.text for s in segments] == ["Hello world", "Second cue"]
        assert segments[0].start == 0.0
        assert segments[0].end == 2.5

    def test_hours_are_parsed_when_present(self, tmp_path: Path) -> None:
        content = "1\n01:02:03,000 --> 01:02:04,000\nfar in\n"
        segments = io.load(write(tmp_path / "a.srt", content))
        assert segments[0].start == 3723.0

    def test_multi_line_cue_bodies_are_joined(self, tmp_path: Path) -> None:
        content = "1\n00:00:00,000 --> 00:00:02,000\nLine one\nLine two\n"
        segments = io.load(write(tmp_path / "a.srt", content))
        assert segments[0].text == "Line one Line two"

    def test_unparseable_timing_line_is_named(self, tmp_path: Path) -> None:
        content = "1\nnot a timestamp --> also not\ntext\n"
        with pytest.raises(TranscriptFormatError, match="unparseable timing line"):
            io.load(write(tmp_path / "a.srt", content))

    def test_index_is_assigned_by_kept_cue_order(self, tmp_path: Path) -> None:
        content = (
            "1\n00:00:00,000 --> 00:00:01,000\n \n\n"
            "2\n00:00:01,000 --> 00:00:02,000\nreal\n"
        )
        segments = io.load(write(tmp_path / "a.srt", content))
        assert len(segments) == 1
        assert segments[0].index == 0


class TestVtt:
    def test_loads_dot_separated_timestamps(self, tmp_path: Path) -> None:
        content = "WEBVTT\n\n00:00:00.000 --> 00:00:02.500\nHello world\n"
        segments = io.load(write(tmp_path / "a.vtt", content))
        assert segments[0].text == "Hello world"
        assert segments[0].end == 2.5

    def test_inline_styling_tags_are_stripped(self, tmp_path: Path) -> None:
        content = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n<b>Bold</b> and <i>italic</i>\n"
        segments = io.load(write(tmp_path / "a.vtt", content))
        assert segments[0].text == "Bold and italic"

    def test_cue_identifier_line_is_skipped(self, tmp_path: Path) -> None:
        content = "WEBVTT\n\nintro\n00:00:00.000 --> 00:00:01.000\ntext here\n"
        segments = io.load(write(tmp_path / "a.vtt", content))
        assert segments[0].text == "text here"


class TestDiscover:
    def test_single_file(self, tmp_path: Path) -> None:
        path = write(tmp_path / "a.json", json.dumps({"segments": []}))
        assert io.discover([path]) == [path]

    def test_directory_is_recursive_and_sorted(self, tmp_path: Path) -> None:
        write(tmp_path / "b.srt", "")
        (tmp_path / "sub").mkdir()
        write(tmp_path / "sub" / "a.vtt", "")
        found = io.discover([tmp_path])
        assert [p.name for p in found] == ["b.srt", "a.vtt"]

    def test_non_transcript_files_are_ignored_in_a_directory(self, tmp_path: Path) -> None:
        write(tmp_path / "notes.txt", "not a transcript")
        write(tmp_path / "a.srt", "")
        assert [p.name for p in io.discover([tmp_path])] == ["a.srt"]

    def test_explicit_non_transcript_path_is_refused(self, tmp_path: Path) -> None:
        path = write(tmp_path / "notes.txt", "x")
        with pytest.raises(TranscriptFormatError, match="not a transcript"):
            io.discover([path])

    def test_duplicates_collapse(self, tmp_path: Path) -> None:
        path = write(tmp_path / "a.srt", "")
        assert io.discover([path, tmp_path]) == [path]


class TestErrors:
    def test_missing_file_reports_the_path(self, tmp_path: Path) -> None:
        with pytest.raises(TranscriptFormatError, match="cannot read"):
            io.load(tmp_path / "absent.json")
