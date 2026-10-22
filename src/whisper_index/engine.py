"""The inverted index and search over it.

Search is AND-of-terms: a result must contain every query term somewhere in
its segment. This is a deliberate precision choice — the whole point of a
"jump back to the source" tool is that each result is worth listening to;
an OR search over a transcript index would flood a two-word query with
segments that only match one word.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from .types import Hit, Segment

# Unicode letters and digits (apostrophes inside a word kept). Whisper
# transcribes ~100 languages; an ASCII-only pattern split "año" into "a" and
# "o" and indexed "café" as "caf", so searches matched the wrong segments.
_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)*")


def tokenize(text: str) -> list[str]:
    return _WORD.findall(text.lower())


@dataclass
class Index:
    """Segments plus the token -> {segment_id: count} postings over them.

    ``segment_id`` is the position of the segment in ``segments`` — stable
    for the life of one built index, and what postings key on so search
    never re-derives identity from (source, index) tuples.
    """

    segments: list[Segment] = field(default_factory=list)
    postings: dict[str, dict[int, int]] = field(default_factory=lambda: defaultdict(dict))

    def __len__(self) -> int:
        return len(self.segments)


def build(segments: list[Segment]) -> Index:
    index = Index(segments=list(segments))
    for segment_id, segment in enumerate(index.segments):
        counts: dict[str, int] = defaultdict(int)
        for token in tokenize(segment.text):
            counts[token] += 1
        for token, count in counts.items():
            index.postings.setdefault(token, {})[segment_id] = count
    return index


def _term_spans(text: str, term: str) -> list[tuple[int, int]]:
    """Every whole-word, case-insensitive occurrence of ``term`` in ``text``."""
    pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
    return [match.span() for match in pattern.finditer(text)]


def search(index: Index, query: str, limit: int = 10) -> list[Hit]:
    # A repeated query word must not count twice towards the score.
    terms = list(dict.fromkeys(tokenize(query)))
    if not terms:
        return []

    candidates: set[int] | None = None
    for term in terms:
        postings_for_term = set(index.postings.get(term, {}))
        candidates = (
            postings_for_term if candidates is None else candidates & postings_for_term
        )
        if not candidates:
            return []
    assert candidates is not None

    hits = []
    for segment_id in candidates:
        segment = index.segments[segment_id]
        term_counts = (index.postings[term][segment_id] for term in terms)
        score = float(sum(term_counts))
        spans = tuple(
            sorted(
                span
                for term in dict.fromkeys(terms)  # de-duplicate, preserve order
                for span in _term_spans(segment.text, term)
            )
        )
        hits.append(Hit(segment=segment, score=score, match_spans=spans))

    hits.sort(key=lambda hit: (-hit.score, hit.segment.source, hit.segment.index))
    return hits[:limit]
