from __future__ import annotations

import json
from pathlib import Path

import pytest

from whisper_index import __version__, cli


def write_whisper_json(path: Path) -> str:
    doc = {
        "segments": [
            {"start": 0.0, "end": 2.0, "text": "alpha beta"},
            {"start": 2.0, "end": 4.0, "text": "beta gamma"},
        ]
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return str(path)


class TestBuild:
    def test_builds_and_writes_an_index(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        transcript = write_whisper_json(tmp_path / "t.json")
        index_path = tmp_path / "index.json"
        code = cli.main(["build", transcript, "--out", str(index_path)])
        assert code == cli.EXIT_OK
        assert index_path.exists()
        assert "segment(s)" in capsys.readouterr().out

    def test_no_transcripts_found_is_a_usage_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        code = cli.main(["build", str(empty_dir), "--out", str(tmp_path / "i.json")])
        assert code == cli.EXIT_USAGE
        assert capsys.readouterr().err.startswith("error:")

    def test_bad_transcript_path_is_a_usage_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = cli.main(
            ["build", str(tmp_path / "absent.json"), "--out", str(tmp_path / "i.json")]
        )
        assert code == cli.EXIT_USAGE


class TestSearch:
    def _index(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> str:
        transcript = write_whisper_json(tmp_path / "t.json")
        index_path = tmp_path / "index.json"
        cli.main(["build", transcript, "--out", str(index_path)])
        capsys.readouterr()  # discard build's own stdout
        return str(index_path)

    def test_finds_a_match(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        index_path = self._index(tmp_path, capsys)
        code = cli.main(["search", "--index", index_path, "alpha"])
        assert code == cli.EXIT_OK
        assert "**alpha**" in capsys.readouterr().out

    def test_no_matches_still_exits_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        index_path = self._index(tmp_path, capsys)
        code = cli.main(["search", "--index", index_path, "zzznotpresent"])
        assert code == cli.EXIT_OK
        assert "no matches" in capsys.readouterr().out

    def test_json_format(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        index_path = self._index(tmp_path, capsys)
        cli.main(["search", "--index", index_path, "beta", "--format", "json"])
        payload = json.loads(capsys.readouterr().out)
        assert isinstance(payload, list)
        assert len(payload) == 2

    def test_limit_is_honoured(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        index_path = self._index(tmp_path, capsys)
        cli.main(["search", "--index", index_path, "beta", "--format", "json", "--limit", "1"])
        payload = json.loads(capsys.readouterr().out)
        assert len(payload) == 1

    def test_zero_limit_is_refused(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        index_path = self._index(tmp_path, capsys)
        code = cli.main(["search", "--index", index_path, "beta", "--limit", "0"])
        assert code == cli.EXIT_USAGE

    def test_missing_index_file_is_a_usage_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = cli.main(["search", "--index", str(tmp_path / "absent.json"), "x"])
        assert code == cli.EXIT_USAGE


class TestMisc:
    def test_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as excinfo:
            cli.main(["--version"])
        assert excinfo.value.code == 0
        assert __version__ in capsys.readouterr().out

    def test_no_command_is_a_usage_error(self) -> None:
        with pytest.raises(SystemExit):
            cli.main([])


class TestModuleEntryPoint:
    def test_python_dash_m_invocation(self, tmp_path: Path) -> None:
        import subprocess
        import sys

        transcript = write_whisper_json(tmp_path / "t.json")
        index_path = tmp_path / "index.json"
        done = subprocess.run(
            [
                sys.executable, "-m", "whisper_index",
                "build", transcript, "--out", str(index_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert done.returncode == 0
        assert index_path.exists()
