# Production readiness — whisper-index

Audit date: 2026-10-22. Tested commit: `b55125c` (branch `audit/production-readiness`, based on `main` @ `ee1681e`).

## Scope

Stdlib-only CLI that indexes existing Whisper transcripts (native JSON, SRT, WebVTT) into a JSON
inverted index and searches it (AND of whole words, case-insensitive) returning file + timestamp +
highlighted text. It never runs speech recognition — there is no model path to download or verify.

## Platforms

CPython 3.10+, no runtime dependencies. Verified on macOS 27 (Apple M5), CPython 3.12.14.

## Clean-clone verification (commit `b55125c`)

```bash
git clone -b audit/production-readiness <local clone> whisper-index && cd whisper-index
uv venv --python 3.12 .venv && . .venv/bin/activate && uv pip install .
whisper-index build examples --out index.json            # 7 segments, 2 files — matches README
whisper-index search --index index.json "supply chain"   # 3 hits — matches README
whisper-index search --index index.json "nothing matches this"   # "no matches", exit 0 (documented)
uv pip install -e ".[dev]" && pytest && ruff check . && mypy     # 78 passed / clean / clean
```

## Commands and results

| Command | Baseline (`ee1681e`) | After (`b55125c`) |
| --- | --- | --- |
| `pytest` | exit 0 — 71 passed, 0 failed, 0 skipped | exit 0 — 78 passed, 0 failed, 0 skipped |
| `ruff check .` / `mypy` | exit 0 / exit 0 | exit 0 / exit 0 |
| `uvx pip-audit` | — | no known vulnerabilities |

CI status — default branch: success (`ee1681e`, 2026-09-01); audit branch: pending until pushed.

## Bugs found and fixed

| Severity | Bug | Regression test |
| --- | --- | --- |
| High (core, multilingual) | ASCII-only tokenizer: `año` → `a`,`o` (query matched unrelated segments), `café` → `caf` | `tests/test_engine.py::test_non_ascii_words_are_whole_tokens`, `test_a_non_ascii_query_does_not_match_unrelated_segments` |
| Medium (silent stale data) | old indexes hold ASCII postings → format version bumped to 2; v1 refused | `tests/test_persist.py::test_a_version_1_index_is_refused_so_it_gets_rebuilt` |
| Low | repeated query word double-counted in score | `test_a_repeated_query_word_does_not_double_the_score` |
| Docs | README example (842 segments, 14 files) was not from a real run | README shows real output for `examples/` |

Two existing persist tests hard-coded `"format_version": 1`; they now use `persist.FORMAT_VERSION`
(required by the version bump; assertions unchanged).

## Verification of format compatibility

New tests reproduce the layouts produced by openai-whisper's writers from their format definitions:
JSON with `id/seek/tokens/temperature/avg_logprob/...`, SRT `HH:MM:SS,mmm`, VTT `MM:SS.mmm` below one
hour and `H:MM:SS.mmm` above, `<u>` highlight tags. **Unverified:** no speech model was run (by design
and per audit rules: no model downloads), and no real Whisper output files were available.

## Security review

No network, no model, JSON via `json`. History secret scan: no hits. `pip-audit`: clean.

## Known limitations

No word segmentation for CJK/Thai; whole-file in-memory index; AND-only search.

## Acceptance checklist

| # | Item | Expected | Evidence | Result |
| --- | --- | --- | --- | --- |
| 1 | README example reproduces | identical | clean clone | PASS |
| 2 | Timestamps parsed from JSON/SRT/VTT | exact seconds | io tests | PASS |
| 3 | Whole-word AND search with highlights | spans correct | engine tests | PASS |
| 4 | Non-ASCII words searchable correctly | `año` only hits `año` | new tests | PASS |
| 5 | Stale index refused | version error | new test | PASS |
| 6 | Real Whisper output end to end | indexes | not available | NOT VERIFIED |

## Classification proposal

**Production-Ready for Its Documented Scope** (proposal), with real Whisper files unverified.
