from __future__ import annotations

from whisper_index import engine

from .conftest import segment


class TestTokenize:
    def test_lowercases_and_splits(self) -> None:
        assert engine.tokenize("Hello, World!") == ["hello", "world"]

    def test_keeps_apostrophes(self) -> None:
        assert engine.tokenize("it's fine") == ["it's", "fine"]

    def test_empty_text(self) -> None:
        assert engine.tokenize("") == []


class TestBuild:
    def test_indexes_every_segment(self) -> None:
        index = engine.build([segment(0, "alpha beta"), segment(1, "beta gamma")])
        assert len(index) == 2
        assert set(index.postings) == {"alpha", "beta", "gamma"}

    def test_postings_count_term_frequency_per_segment(self) -> None:
        index = engine.build([segment(0, "beta beta beta")])
        assert index.postings["beta"][0] == 3

    def test_empty_segment_list_builds_an_empty_index(self) -> None:
        index = engine.build([])
        assert len(index) == 0
        assert index.postings == {}


class TestSearch:
    def test_single_term_matches_containing_segments(self) -> None:
        index = engine.build([segment(0, "alpha beta"), segment(1, "gamma delta")])
        hits = engine.search(index, "alpha")
        assert [h.segment.index for h in hits] == [0]

    def test_multi_term_is_and_not_or(self) -> None:
        index = engine.build(
            [segment(0, "alpha beta"), segment(1, "alpha only"), segment(2, "beta only")]
        )
        hits = engine.search(index, "alpha beta")
        assert [h.segment.index for h in hits] == [0]

    def test_missing_any_term_yields_no_results(self) -> None:
        index = engine.build([segment(0, "alpha beta")])
        assert engine.search(index, "alpha zzzznotpresent") == []

    def test_empty_query_yields_no_results(self) -> None:
        index = engine.build([segment(0, "alpha beta")])
        assert engine.search(index, "   ") == []

    def test_search_is_case_insensitive(self) -> None:
        index = engine.build([segment(0, "Alpha Beta")])
        assert engine.search(index, "ALPHA beta")

    def test_search_matches_whole_words_only(self) -> None:
        index = engine.build([segment(0, "alphabet soup")])
        assert engine.search(index, "alpha") == []

    def test_higher_term_frequency_ranks_first(self) -> None:
        index = engine.build(
            [segment(0, "alpha once here"), segment(1, "alpha alpha alpha repeated")]
        )
        hits = engine.search(index, "alpha")
        assert [h.segment.index for h in hits] == [1, 0]

    def test_score_sums_across_query_terms(self) -> None:
        index = engine.build([segment(0, "alpha beta alpha")])
        hits = engine.search(index, "alpha beta")
        assert hits[0].score == 3.0

    def test_match_spans_locate_every_occurrence(self) -> None:
        index = engine.build([segment(0, "alpha and alpha again")])
        hits = engine.search(index, "alpha")
        assert len(hits[0].match_spans) == 2
        for start, end in hits[0].match_spans:
            assert index.segments[0].text[start:end].lower() == "alpha"

    def test_limit_truncates_results(self) -> None:
        segments = [segment(i, "alpha") for i in range(20)]
        index = engine.build(segments)
        assert len(engine.search(index, "alpha", limit=3)) == 3

    def test_ties_break_deterministically_by_source_then_index(self) -> None:
        index = engine.build(
            [
                segment(1, "alpha", source="b.json"),
                segment(0, "alpha", source="a.json"),
                segment(0, "alpha", source="b.json"),
            ]
        )
        hits = engine.search(index, "alpha")
        assert [(h.segment.source, h.segment.index) for h in hits] == [
            ("a.json", 0),
            ("b.json", 0),
            ("b.json", 1),
        ]

    def test_duplicate_query_terms_do_not_double_count_spans(self) -> None:
        index = engine.build([segment(0, "alpha beta")])
        hits = engine.search(index, "alpha alpha")
        assert len(hits[0].match_spans) == 1
