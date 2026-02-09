from __future__ import annotations

from pathlib import Path

import pytest

from skfd.verifier import aggregate


def test_run_all_handles_exception(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mm_file = tmp_path / "t.mm"
    mm_file.write_text("$c wff $.\n", encoding="utf-8")

    def _boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(aggregate, "_run", _boom)
    res = aggregate.run_all(mm_file, [("v", ["cmd"])])
    assert res[0].passed is False
    assert "boom" in res[0].output


def test_run_all_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mm_file = tmp_path / "t.mm"
    mm_file.write_text("$c wff $.\n", encoding="utf-8")

    monkeypatch.setattr(aggregate, "_run", lambda *_a, **_k: (0, "ok"))
    res = aggregate.run_all(mm_file, [("v", ["cmd"])])
    assert res[0].passed is True
    assert res[0].output == "ok"


def test_run_and_summarize(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    mm_file = tmp_path / "t.mm"
    mm_file.write_text("$c wff $.\n", encoding="utf-8")

    class Proc:
        returncode = 0
        stdout = "ok"

    monkeypatch.setattr(aggregate.subprocess, "run", lambda *_a, **_k: Proc())
    rc, out = aggregate._run(["cmd"], mm_file, 1)
    assert rc == 0
    assert out == "ok"

    assert aggregate.summarize([]) == ""
    results = [aggregate.VerifierResult(name="v", passed=False, returncode=1, output="err")]
    summary = aggregate.summarize(results)
    assert "FAIL" in summary

    class ProcNone:
        returncode = 0
        stdout = None

    monkeypatch.setattr(aggregate.subprocess, "run", lambda *_a, **_k: ProcNone())
    rc2, out2 = aggregate._run(["cmd"], mm_file, 1)
    assert rc2 == 0
    assert out2 == ""
