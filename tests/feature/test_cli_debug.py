from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from skfd import cli


def test_cmd_debug_happy_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path
    src = root / "src"
    target = root / "target"
    src.mkdir()
    target.mkdir()

    mm_file = target / "pkg_full.mm"
    map_file = target / "pkg_full.mm.map"
    mm_file.write_text("L1 $a wff ph $.\n", encoding="utf-8")
    map_file.write_text("{\"mappings\": [], \"origins\": []}", encoding="utf-8")

    class DummyRunner:
        def __init__(self, _root, _target):
            self.lirs = {"pkg": object()}

        def execute_all(self):
            return None

        def verify_package(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(cli, "DriverRunner", DummyRunner)

    args = argparse.Namespace(package="pkg", label="L1", root=root, level=0, context=2)
    rc = cli._cmd_debug(args)
    assert rc == 0


def test_cmd_debug_missing_map(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path
    src = root / "src"
    target = root / "target"
    src.mkdir()
    target.mkdir()

    mm_file = target / "pkg_full.mm"
    mm_file.write_text("$c wff $.\n", encoding="utf-8")

    class DummyRunner:
        def __init__(self, _root, _target):
            self.lirs = {"pkg": object()}

        def execute_all(self):
            return None

        def verify_package(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(cli, "DriverRunner", DummyRunner)

    args = argparse.Namespace(package="pkg", label="L1", root=root, level=0, context=2)
    rc = cli._cmd_debug(args)
    assert rc == 1
