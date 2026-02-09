from __future__ import annotations

import argparse

import pytest

from skfd import cli


def test_cmd_example_minimal_ok(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    class DummyCfg:
        def get_active_commands(self):
            return [("v", ["cmd"]) ]

    monkeypatch.setattr(cli, "load_config", lambda _root: DummyCfg())
    monkeypatch.setattr(cli, "_run_example_minimal_ok", lambda *_a, **_k: None)

    args = argparse.Namespace(name="minimal_ok", no_write=True, root=None)
    rc = cli._cmd_example(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "accepted" in out


def test_cmd_example_minimal_diag(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(cli, "_run_example_minimal_diag", lambda *_a, **_k: None)
    args = argparse.Namespace(name="minimal_diag", no_write=True, root=None)
    rc = cli._cmd_example(args)
    assert rc == 2
    out = capsys.readouterr().out
    assert "unexpected" in out


def test_cmd_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyCfg:
        def get_active_commands(self):
            return [("v", ["cmd"]) ]

    monkeypatch.setattr(cli, "load_config", lambda _root: DummyCfg())
    monkeypatch.setattr(cli, "run_sanity", lambda *_a, **_k: None)
    monkeypatch.setattr(cli, "_run_example_minimal_ok", lambda *_a, **_k: None)

    args = argparse.Namespace(no_write=True, root=None)
    rc = cli._cmd_smoke(args)
    assert rc == 0
