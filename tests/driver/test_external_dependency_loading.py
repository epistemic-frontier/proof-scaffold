from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from skfd.driver.runner import DriverRunner


@pytest.fixture
def workspace(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    return src, target


def _write_pyproject(pkg_dir: Path, *, name: str, deps: list[str]) -> None:
    deps_list = ", ".join(f'"{d}"' for d in deps)
    content = f"""
[project]
name = "{name}"
dependencies = [{deps_list}]
"""
    (pkg_dir / "pyproject.toml").write_text(content, encoding="utf-8")


def create_package(src_root: Path, name: str, deps: list[str], build_code: str):
    pkg_dir = src_root / name
    pkg_dir.mkdir()
    _write_pyproject(pkg_dir, name=name, deps=deps)
    (pkg_dir / "build.py").write_text(build_code, encoding="utf-8")


def test_external_dist_with_hyphen_loads_via_top_level_txt(
    workspace: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
):
    src, target = workspace

    external_root = src.parent / "external"
    external_pkg = external_root / "demo_pkg"
    external_pkg.mkdir(parents=True)
    (external_pkg / "__init__.py").write_text("", encoding="utf-8")
    (external_pkg / "build.py").write_text(
        """
from skfd.api_v2 import BuildContextV2

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    wff = mm.sym.const('wff')
    ph = mm.sym.var('ph')
    mm.auto.floating(ph, tc=wff)
    ax = mm.sym.label('ext-ax')
    mm.a(ax, tc=wff, expr=[ph])
    mm.export(wff, ph, ax)
""",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(external_root))

    import importlib.metadata as md

    def fake_distribution(name: str):  # type: ignore[no-untyped-def]
        if name in {"demo-dist", "demo_dist"}:
            return SimpleNamespace(
                requires=[],
                read_text=lambda p: "demo_pkg\n" if p == "top_level.txt" else None,
            )
        raise md.PackageNotFoundError(name)

    monkeypatch.setattr(md, "distribution", fake_distribution)

    create_package(
        src,
        "pkg_main",
        ["demo-dist"],
        """
from skfd.api_v2 import BuildContextV2

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    ext = ctx.deps.demo_pkg
    wff = ext['wff']
    ph = ext['ph']
    ax = mm.sym.label('use-ext')
    mm.a(ax, tc=wff, expr=[ph])
    mm.export(ax)
""",
    )

    runner = DriverRunner(src, target)
    runner.execute_all()
    assert "pkg_main" in runner.lirs
    runner.verify_package("pkg_main")
    out = (target / "pkg_main_full.mm").read_text(encoding="utf-8")
    assert "ext-ax" in out
    assert "use-ext" in out
