from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from skfd import cli
from skfd.core.diag import Diagnostic, LinkerDiagError
from skfd.proof import ProofCoverageDeclaration, ProofCoverageReport


class _DummyCfg:
    def __init__(self, cmds):
        self._cmds = cmds
        self.active_verifiers = []
        self.verifiers = {}

    def get_active_commands(self):
        return self._cmds


def test_cmd_doctor_runs_all(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    calls: list[str] = []

    def _run_sanity(_cmd=None):
        calls.append(str(_cmd))

    monkeypatch.setattr(cli, "run_sanity", _run_sanity)
    monkeypatch.setattr(cli, "load_config", lambda _root: _DummyCfg([("v1", ["cmd1"])]))

    rc = cli._cmd_doctor(argparse.Namespace(root=None))
    assert rc == 0
    out = capsys.readouterr().out
    assert "Doctor check passed" in out
    assert calls


def test_cmd_verify_script_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = tmp_path / "p.py"
    script.write_text("def prove_x():\n    return None\n", encoding="utf-8")

    import skfd.driver.script_runner as sr

    monkeypatch.setattr(sr, "verify_script", lambda *_a, **_k: 0)
    rc = cli._cmd_verify(argparse.Namespace(package=str(script), root=None, level=0))
    assert rc == 0


def test_cmd_verify_package(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path
    src = root / "src"
    target = root / "target"
    src.mkdir()

    class DummyRunner:
        def __init__(self, _root, _target):
            self.lirs = {"pkg": object()}

        def execute_all(self):
            return None

        def verify_package(self, *_args, **_kwargs):
            return None

        def coverage_report(self, _pkg):
            return ProofCoverageReport(
                unit_id="pkg",
                declarations=(),
                emitted_labels=("th-1",),
                declared_labels=(),
                declared_but_unemitted=(),
                missing_required_labels=(),
            )

    monkeypatch.setattr(cli, "DriverRunner", DummyRunner)
    monkeypatch.setattr(cli, "load_config", lambda _root: _DummyCfg([("v", ["cmd"]) ]))
    monkeypatch.setattr(cli, "verify", lambda *_a, **_k: None)

    # create artifact to satisfy verify
    target.mkdir()
    (target / "pkg_full.mm").write_text("$c wff $.", encoding="utf-8")

    rc = cli._cmd_verify(
        argparse.Namespace(package="pkg", root=root, level=0, coverage="emitted")
    )
    assert rc == 0


def test_cmd_verify_declared_coverage_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path
    src = root / "src"
    src.mkdir()

    class DummyRunner:
        def __init__(self, _root, _target):
            self.lirs = {"pkg": object()}

        def execute_all(self):
            return None

        def verify_package(self, *_args, **_kwargs):
            return None

        def coverage_report(self, _pkg):
            return ProofCoverageReport(
                unit_id="pkg",
                declarations=(
                    ProofCoverageDeclaration(
                        name="public",
                        labels=("missing", "th-1"),
                        require_verified=False,
                        source="labels",
                    ),
                ),
                emitted_labels=("th-1",),
                declared_labels=("missing", "th-1"),
                declared_but_unemitted=("missing",),
                missing_required_labels=(),
            )

    monkeypatch.setattr(cli, "DriverRunner", DummyRunner)

    rc = cli._cmd_verify(
        argparse.Namespace(package="pkg", root=root, level=0, coverage="declared")
    )
    assert rc == 1


def test_main_handles_linker_diag(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_args):
        raise LinkerDiagError(
            Diagnostic(
                error_code="E_TEST",
                message="boom",
                primary_origin_ref=None,
                related_origin_refs=(),
                origin_chain=(),
                details={},
            )
        )

    monkeypatch.setattr(cli, "_cmd_verify", _raise)
    rc = cli.main(["verify", "pkg"])
    assert rc == 1
