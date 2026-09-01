from __future__ import annotations

import json

from whisper_index import engine, report

from .conftest import segment


class TestFormatTimestamp:
    def test_zero(self) -> None:
        assert report.format_timestamp(0.0) == "0:00:00"

    def test_minutes_and_seconds(self) -> None:
        assert report.format_timestamp(75.0) == "0:01:15"

    def test_hours(self) -> None:
        assert report.format_timestamp(3661.0) == "1:01:01"

    def test_rounds_to_nearest_second(self) -> None:
        assert report.format_timestamp(59.6) == "0:01:00"


class TestRenderHitsText:
    def test_no_matches_says_so(self) -> None:
        assert report.render_hits_text([]) == "no matches"

    def test_hit_shows_source_timestamp_and_score(self) -> None:
        index = engine.build([segment(0, "alpha beta", start=65.0, source="ep.json")])
        hits = engine.search(index, "alpha")
        text = report.render_hits_text(hits)
        assert "ep.json" in text
        assert "0:01:05" in text
        assert "score 1" in text

    def test_matches_are_highlighted_in_place(self) -> None:
        index = engine.build([segment(0, "find the target word")])
        hits = engine.search(index, "target")
        text = report.render_hits_text(hits)
        assert "**target**" in text
        assert "find the **target** word" in text

    def test_multiple_spans_all_highlighted_without_shifting(self) -> None:
        index = engine.build([segment(0, "alpha middle alpha")])
        hits = engine.search(index, "alpha")
        text = report.render_hits_text(hits)
        assert text.count("**alpha**") == 2


class TestRenderHitsJson:
    def test_round_trips_through_to_dict(self) -> None:
        index = engine.build([segment(0, "alpha beta")])
        hits = engine.search(index, "alpha")
        payload = json.loads(report.render_hits_json(hits))
        assert payload == [hits[0].to_dict()]

    def test_empty_hits_render_an_empty_array(self) -> None:
        assert json.loads(report.render_hits_json([])) == []


class TestRenderIndexSummary:
    def test_counts_segments_files_and_terms(self) -> None:
        index = engine.build(
            [
                segment(0, "alpha beta", source="a.json", start=0.0, end=1.0),
                segment(1, "beta gamma", source="b.json", start=1.0, end=2.0),
            ]
        )
        summary = report.render_index_summary(index)
        assert "2 segment(s)" in summary
        assert "2 file(s)" in summary
        assert "3 distinct term(s)" in summary
