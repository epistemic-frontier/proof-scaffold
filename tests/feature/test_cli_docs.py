from __future__ import annotations

import argparse
import types

import pytest

from skfd import cli


def test_cmd_list_lemmas(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    # fake package module with prove_* functions
    def prove_L1():
        """doc L1"""
        return None

    def prove_L2():
        """doc L2"""
        return None

    mod = types.SimpleNamespace(prove_L1=prove_L1, prove_L2=prove_L2)

    def _fake_import(name: str):
        assert name.endswith(".lemmas")
        return mod

    monkeypatch.setattr(cli.importlib, "import_module", _fake_import)
    args = argparse.Namespace(package="logic", module="propositional.hilbert.lemmas")
    rc = cli._cmd_list_lemmas(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "L1" in out and "L2" in out


def test_cmd_list_defs(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    # fake package module
    mod = types.SimpleNamespace(
        DEFINITIONS={
            "def1": "x",
            "def2": "y",
        }
    )

    def _fake_import(name: str):
        assert name.endswith(".definitions")
        return mod

    monkeypatch.setattr(cli.importlib, "import_module", _fake_import)
    args = argparse.Namespace(package="logic", module="propositional.hilbert.definitions")
    rc = cli._cmd_list_defs(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "def1" in out and "def2" in out


def test_cmd_list_lemmas_missing(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    def _fake_import(_name: str):
        raise ModuleNotFoundError("boom")

    monkeypatch.setattr(cli.importlib, "import_module", _fake_import)
    args = argparse.Namespace(package="logic", module="x")
    rc = cli._cmd_list_lemmas(args)
    assert rc == 1
    err = capsys.readouterr().err
    assert "boom" in err
