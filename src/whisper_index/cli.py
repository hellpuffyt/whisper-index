"""Console entry point: build and search.

Exit codes:

* ``build``  — 0 built and saved, 1 usage/input error
* ``search`` — 0 always (no matches is a valid answer), 1 usage/input error
"""

from __future__ import annotations

import argparse
import sys

from . import __version__, engine, io, persist, report
from .errors import WhisperIndexError

EXIT_OK = 0
EXIT_USAGE = 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whisper-index",
        description=(
            "Build a searchable transcript index from an audio library's "
            "Whisper output, with timestamped results that jump back to "
            "the source."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="index transcript files")
    p_build.add_argument("paths", nargs="+", help="transcript files or directories")
    p_build.add_argument("--out", required=True, help="path to write the index JSON to")

    p_search = sub.add_parser("search", help="search a built index")
    p_search.add_argument("--index", required=True, help="path to an index JSON")
    p_search.add_argument("query", help="search terms (all must match, whole-word)")
    p_search.add_argument("--limit", type=int, default=10, help="max results (default: 10)")
    p_search.add_argument("--format", choices=("text", "json"), default="text")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "build":
            return _build(args)
        if args.command == "search":
            return _search(args)
        raise AssertionError(f"unknown command {args.command!r}")
    except WhisperIndexError as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_USAGE


def _build(args: argparse.Namespace) -> int:
    transcript_paths = io.discover(list(args.paths))
    if not transcript_paths:
        raise WhisperIndexError("no transcript files found under the given paths")
    segments = [segment for path in transcript_paths for segment in io.load(path)]
    index = engine.build(segments)
    persist.save(index, args.out)
    print(report.render_index_summary(index))
    print(f"index written to {args.out}")
    return EXIT_OK


def _search(args: argparse.Namespace) -> int:
    if args.limit < 1:
        raise WhisperIndexError(f"--limit must be at least 1 (got {args.limit})")
    index = persist.load(args.index)
    hits = engine.search(index, args.query, args.limit)
    print(
        report.render_hits_json(hits)
        if args.format == "json"
        else report.render_hits_text(hits)
    )
    return EXIT_OK
