from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from skfd import cli
from skfd.verifier import _explain_output, verify


@dataclass
class _Proc:
    returncode: int
    stdout: str


def test_explain_output_stack_underflow() -> None:
    msg = _explain_output("stack underflow")
    assert "stack underflow" in msg.lower()
    assert "Explanation" in msg


def test_verify_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mm = tmp_path / "t.mm"
    mm.write_text("$c wff $.\n", encoding="utf-8")

    def _run(*_args: Any, **_kwargs: Any) -> _Proc:
        return _Proc(returncode=0, stdout="ok")

    monkeypatch.setattr("subprocess.run", _run)
    verify(["echo"], mm)


def test_verify_failure_includes_map(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mm = tmp_path / "t.mm"
    mm.write_text("line1\nline2\nline3\n", encoding="utf-8")

    map_file = mm.with_suffix(".mm.map")
    map_file.write_text(
        """
{
  "format": "skfd-sourcemap-v1",
  "mappings": [{"line": 2, "origin_ref": 0}],
  "origins": [{"file": "src/foo.py", "line": 123}]
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    def _run(*_args: Any, **_kwargs: Any) -> _Proc:
        return _Proc(
            returncode=1,
            stdout="?Error at line 2: stack underflow\n",
        )

    monkeypatch.setattr("subprocess.run", _run)
    with pytest.raises(RuntimeError) as exc:
        verify(["verifier"], mm)

    text = str(exc.value)
    assert "stack underflow" in text
    assert "Source Origin" in text
    assert "src/foo.py:123" in text


def test_cli_hints_and_configure_path(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    cli._print_friendly_hint(ImportError("No module named 'prelude'"))
    cli._print_friendly_hint(RuntimeError("No active dependencies context"))
    out = capsys.readouterr().err
    assert "prelude" in out
    assert "Run via 'python -m skfd.cli verify" in out

    (tmp_path / "src").mkdir()
    (tmp_path / "repo" / "src").mkdir(parents=True)
    cli._configure_path(tmp_path)
    assert str(tmp_path) in cli.sys.path
    assert str(tmp_path / "src") in cli.sys.path
    assert str(tmp_path / "repo" / "src") in cli.sys.path


def test_configure_logging_does_not_crash() -> None:
    cli._configure_logging()
    # basicConfig should be safe to call multiple times
    cli._configure_logging()
