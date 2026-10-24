# Changelog

## Unreleased

- Fixed: the tokenizer only knew ASCII letters, so `año` was indexed as `a` +
  `o` (matching unrelated segments) and `café` as `caf`. Words are now Unicode
  letter/digit runs. The index format version is now 2; version-1 indexes are
  refused and must be rebuilt.
- Fixed: a repeated query word counted twice towards a hit's score.
- Docs: README example replaced with real output for `examples/`; install from
  source; tokenizer and verification limits documented. Added tests for the
  exact openai-whisper JSON/SRT/VTT layouts, `SECURITY.md`, `.editorconfig`,
  `docs/PRODUCTION_READINESS.md`.

## 0.1.0 — 2026-09-01

Initial release.

- Loaders for the three formats a Whisper workflow actually produces:
  native JSON (`segments` array), SRT, and WebVTT — with VTT's inline
  `<b>`/`<i>`/`<c.color>` styling tags stripped before indexing and
  hours-optional, comma-or-dot millisecond timestamps parsed uniformly.
- An inverted index (token → per-segment term frequency) built from
  scratch, with AND-of-terms, whole-word, case-insensitive search and
  deterministic tie-breaking.
- `whisper-index build|search` CLI: `build` indexes files and directories
  recursively; `search` ranks by term frequency and renders `**matches**`
  highlighted in place, in text or JSON.
- Index files persist as plain JSON — never pickle — with a format-version
  check on load.
- Zero runtime dependencies; Python 3.10–3.13. This tool never runs speech
  recognition itself — it indexes transcripts that already exist.
