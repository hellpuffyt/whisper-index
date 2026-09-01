# Contributing

Thanks for looking into whisper-index.

## Setup

```console
python -m venv .venv && . .venv/bin/activate   # Scripts\activate on Windows
pip install -e ".[dev]"
```

## Before opening a pull request

```console
pytest            # the whole suite; new behaviour needs new tests
ruff check .      # lint
mypy              # strict — the src/ tree carries full annotations
```

## Ground rules

- **No runtime dependencies.** `dependencies = []` is a feature, not an
  oversight.
- **Never run speech recognition.** This tool indexes transcripts that
  already exist; a change that reaches for a model or a network call does
  not belong here.
- **Index files are plain JSON, never pickle.** An index is the kind of
  artefact that gets committed and shared; loading one must never execute
  code.
- **Search stays AND-of-terms, whole-word.** A change toward OR search or
  substring matching needs to defend why flooding results is the right
  tradeoff for a "jump back to the source" tool.
