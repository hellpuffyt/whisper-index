from __future__ import annotations

import json
from pathlib import Path

import pytest

from whisper_index import engine, persist
from whisper_index.errors import IndexFormatError

from .conftest import segment


class TestRoundTrip:
    def test_save_then_load_preserves_segments(self, tmp_path: Path) -> None:
        index = engine.build([segment(0, "alpha beta", start=1.5, end=3.0)])
        path = tmp_path / "index.json"
        persist.save(index, path)
        loaded = persist.load(path)
        assert loaded.segments == index.segments

    def test_save_then_load_preserves_postings(self, tmp_path: Path) -> None:
        index = engine.build([segment(0, "alpha alpha beta"), segment(1, "beta gamma")])
        path = tmp_path / "index.json"
        persist.save(index, path)
        loaded = persist.load(path)
        assert loaded.postings == index.postings

    def test_search_results_are_identical_after_a_round_trip(self, tmp_path: Path) -> None:
        index = engine.build(
            [segment(0, "alpha beta"), segment(1, "alpha gamma"), segment(2, "beta gamma")]
        )
        path = tmp_path / "index.json"
        persist.save(index, path)
        loaded = persist.load(path)
        before = [h.to_dict() for h in engine.search(index, "alpha")]
        after = [h.to_dict() for h in engine.search(loaded, "alpha")]
        assert before == after

    def test_saved_file_is_plain_json(self, tmp_path: Path) -> None:
        index = engine.build([segment(0, "alpha")])
        path = tmp_path / "index.json"
        persist.save(index, path)
        json.loads(path.read_text(encoding="utf-8"))  # must not raise


class TestErrors:
    def test_missing_file_reports_the_path(self, tmp_path: Path) -> None:
        with pytest.raises(IndexFormatError, match="cannot read"):
            persist.load(tmp_path / "absent.json")

    def test_not_json_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "i.json"
        path.write_text("{oops", encoding="utf-8")
        with pytest.raises(IndexFormatError, match="not valid JSON"):
            persist.load(path)

    def test_non_object_json_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "i.json"
        path.write_text("[1, 2]", encoding="utf-8")
        with pytest.raises(IndexFormatError, match="not an index file"):
            persist.load(path)

    def test_wrong_format_version_is_refused(self, tmp_path: Path) -> None:
        index = engine.build([segment(0, "alpha")])
        path = tmp_path / "i.json"
        persist.save(index, path)
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace(
                f'"format_version": {persist.FORMAT_VERSION}', '"format_version": 7'
            ), encoding="utf-8"
        )
        with pytest.raises(IndexFormatError, match="format version 7"):
            persist.load(path)

    def test_missing_field_is_a_named_error(self, tmp_path: Path) -> None:
        path = tmp_path / "i.json"
        path.write_text(
            json.dumps({"format_version": persist.FORMAT_VERSION}), encoding="utf-8"
        )
        with pytest.raises(IndexFormatError, match="malformed"):
            persist.load(path)



def test_a_version_1_index_is_refused_so_it_gets_rebuilt(tmp_path: Path) -> None:
    # Version 1 postings came from the ASCII-only tokenizer.
    index = engine.build([segment(0, "alpha")])
    path = tmp_path / "i.json"
    persist.save(index, path)
    text = path.read_text(encoding="utf-8").replace(
        f'"format_version": {persist.FORMAT_VERSION}', '"format_version": 1'
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(IndexFormatError, match="format version 1"):
        persist.load(path)
