from __future__ import annotations

import importlib
import importlib.metadata as md
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from skfd.driver.discover import (
    find_packages,
    get_package_deps,
    get_package_name,
    load_build_module,
    load_external_build_module,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


def test_load_build_module_uses_package_import_for_relative_imports(tmp_path: Path) -> None:
    pkg = tmp_path / "src" / "pkg_rel"
    _write(pkg / "__init__.py", "")
    _write(pkg / "helper.py", "VALUE = 41")
    _write(
        pkg / "build.py",
        """
        from .helper import VALUE

        def build(ctx):
            return VALUE + 1
        """,
    )

    sys.modules.pop("pkg_rel", None)
    sys.modules.pop("pkg_rel.build", None)
    mod = load_build_module(pkg / "build.py")
    assert mod.build(None) == 42


def test_load_build_module_supports_internal_name(tmp_path: Path) -> None:
    pkg = tmp_path / "src" / "pkg_internal"
    _write(pkg / "__init__.py", "")
    _write(pkg / "helper.py", "VALUE = 42")
    _write(
        pkg / "_build.py",
        "from .helper import VALUE\n\ndef build(ctx):\n    return VALUE\n",
    )
    sys.modules.pop("pkg_internal._build", None)

    mod = load_build_module(pkg / "_build.py")

    assert mod.build(None) == 42


def test_load_build_module_falls_back_to_file_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build = tmp_path / "loose_pkg" / "build.py"
    _write(build, "MARKER = 'standalone'")

    real_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None) -> Any:
        if name == "loose_pkg.build":
            err = ImportError("no loose package")
            err.name = "loose_pkg"
            raise err
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    mod = load_build_module(build)
    assert mod.MARKER == "standalone"
    assert mod.__name__.startswith("skfd_build_loose_pkg")


def test_load_build_module_reraises_import_errors_inside_module(tmp_path: Path) -> None:
    pkg = tmp_path / "src" / "pkg_bad_import"
    _write(pkg / "__init__.py", "")
    _write(pkg / "build.py", "import definitely_missing_inner_dependency")

    sys.modules.pop("pkg_bad_import", None)
    sys.modules.pop("pkg_bad_import.build", None)
    with pytest.raises(ImportError) as excinfo:
        load_build_module(pkg / "build.py")
    assert excinfo.value.name == "definitely_missing_inner_dependency"


def test_load_external_build_module_uses_distribution_top_level(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "site"
    pkg = root / "top_pkg"
    _write(pkg / "__init__.py", "")
    _write(pkg / "build.py", "VALUE = 'external'")
    monkeypatch.syspath_prepend(str(root))
    importlib.invalidate_caches()

    def fake_distribution(name: str) -> Any:
        if name == "demo-dist":
            return SimpleNamespace(
                read_text=lambda path: "top_pkg\n" if path == "top_level.txt" else None
            )
        raise md.PackageNotFoundError(name)

    monkeypatch.setattr(md, "distribution", fake_distribution)
    sys.modules.pop("top_pkg", None)
    sys.modules.pop("top_pkg.build", None)

    mod = load_external_build_module("demo-dist")
    assert mod is not None
    assert mod.VALUE == "external"


def test_load_external_build_module_derives_metamath_suffix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "site"
    pkg = root / "demo_logic"
    _write(pkg / "__init__.py", "")
    _write(pkg / "build.py", "VALUE = 'suffix'")
    monkeypatch.syspath_prepend(str(root))
    importlib.invalidate_caches()

    monkeypatch.setattr(
        md,
        "distribution",
        lambda name: (_ for _ in ()).throw(md.PackageNotFoundError(name)),
    )
    sys.modules.pop("demo_logic", None)
    sys.modules.pop("demo_logic.build", None)

    mod = load_external_build_module("metamath-demo-logic")
    assert mod is not None
    assert mod.VALUE == "suffix"


def test_get_package_deps_parses_project_deps_and_filters_self(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    _write(pkg / "build.py", "")
    _write(
        pkg / "pyproject.toml",
        """
        [project]
        name = "pkg"
        dependencies = [
          "proof-scaffold>=0.0.5",
          "metamath-prelude>=0.1; python_version >= '3.11'",
          "demo_pkg==1.2",
          "other<3",
        ]
        """,
    )

    assert get_package_deps(pkg / "build.py") == [
        "metamath-prelude",
        "demo_pkg",
        "other",
    ]
    assert get_package_name(pkg / "build.py") == "pkg"


def test_get_package_metadata_handles_bad_pyproject(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pkg = tmp_path / "pkg"
    _write(pkg / "build.py", "")
    _write(pkg / "pyproject.toml", "[project\n")

    assert get_package_deps(pkg / "build.py") == []
    assert "Failed to parse pyproject.toml" in capsys.readouterr().out
    assert get_package_name(pkg / "build.py") is None


def test_find_packages_skips_root_build_and_uses_project_name(tmp_path: Path) -> None:
    root = tmp_path / "src"
    root.mkdir()
    _write(root / "build.py", "")
    _write(root / "pkg" / "build.py", "")
    _write(root / "pkg" / "pyproject.toml", '[project]\nname = "dist-name"\n')

    assert list(find_packages(tmp_path / "missing")) == []
    found = list(find_packages(root))
    assert found == [("dist-name", root / "pkg", root / "pkg" / "build.py")]


def test_find_packages_prefers_internal_build_module(tmp_path: Path) -> None:
    root = tmp_path / "src"
    pkg = root / "pkg"
    _write(pkg / "build.py", "")
    _write(pkg / "_build.py", "")

    found = list(find_packages(root))

    assert found == [("pkg", pkg, pkg / "_build.py")]
