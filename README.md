# whisper-index

Build a searchable, timestamped index over a library of Whisper
transcripts, so a query returns not just a matching line but the exact
moment to seek to. Zero runtime dependencies — Python 3.10+ and nothing
else.

```console
$ whisper-index build transcripts/ --out index.json
842 segment(s) across 14 file(s), 3910 distinct term(s), 6:12:04 of transcript indexed
index written to index.json

$ whisper-index search --index index.json "supply chain"
transcripts/ep03.json @ 0:14:22  (score 2)
  ...disruption in the global **supply** **chain** meant every vendor...
transcripts/ep07.vtt @ 0:41:05  (score 2)
  ...rebuilding the **supply** **chain** from the ground up after...
```

## What it indexes, and what it does not do

**This tool never runs speech recognition.** It indexes transcripts that
already exist — Whisper's own native JSON output (a `segments` array of
`{start, end, text}`), or the SRT/VTT files any Whisper wrapper can export.
That is what makes it a from-scratch, deterministic, dependency-free tool
rather than one that needs a model and a GPU: it does the part after
transcription, which most Whisper workflows leave you to solve yourself.

## Search semantics

Search is **AND-of-terms, whole-word, case-insensitive**: a result must
contain every query word somewhere in its segment. This is deliberate —
the point of "jump back to the source" is that each result is worth
listening to, and an OR search over a transcript index floods a two-word
query with segments matching only one word. Results are ranked by term
frequency within the segment and rendered with `**matches**` marked
in-place so you can see *why* a segment matched before you seek to it.

## Usage

```console
whisper-index build transcript.json other/ --out index.json   # files and dirs mix freely
whisper-index search --index index.json "some query"
whisper-index search --index index.json "some query" --format json --limit 5
```

Exit codes: `0` on success (including "no matches" — that is a valid
answer, not a failure), `1` on a usage or input error.

## Input formats

- **Whisper JSON**: `{"segments": [{"start": 0.0, "end": 2.5, "text": "..."}]}`
  — exactly what `whisper.transcribe()` / the `whisper` CLI's `--output_format
  json` produces.
- **SRT**: numbered cues, `HH:MM:SS,mmm --> HH:MM:SS,mmm`.
- **WebVTT**: `WEBVTT` header, `HH:MM:SS.mmm --> HH:MM:SS.mmm`; inline
  `<b>`/`<i>`/`<c.color>` styling tags are stripped before indexing.

## Development

```console
pip install -e ".[dev]"
pytest
ruff check .
mypy
```

MIT licensed.
