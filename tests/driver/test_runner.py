# tests/driver/test_runner.py
from pathlib import Path

import pytest
from skfd.driver.runner import DriverRunner


@pytest.fixture
def workspace(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    target = tmp_path / "target"
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


def test_runner_integration(workspace):
    src, target = workspace

    # 1. Create pkg_a (Base)
    create_package(
        src,
        "pkg_a",
        [],
        """
from skfd.api_v2 import BuildContextV2

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    wff = mm.sym.const("wff")
    ph = mm.sym.var("ph")
    const_a = mm.sym.const("const_a")
    mm.auto.floating(ph, tc=wff)
    ax_a = mm.sym.label("ax-a")
    mm.a(ax_a, tc=wff, expr=[const_a, ph])
    mm.export(wff, ph, const_a, ax_a)
""",
    )

    # 2. Create pkg_b (Depends on A)
    create_package(
        src,
        "pkg_b",
        ["pkg_a"],
        """
from skfd.api_v2 import BuildContextV2

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    pkg_a = ctx.deps.pkg_a
    wff = pkg_a["wff"]
    ph = pkg_a["ph"]
    const_a = pkg_a["const_a"]
    const_b = mm.sym.const("const_b")
    ax_b = mm.sym.label("ax-b")
    mm.a(ax_b, tc=wff, expr=[const_a, const_b, ph])
    mm.export(const_b, ax_b)
""",
    )

    # 3. Create pkg_c (Depends on B, transitively on A)
    create_package(
        src,
        "pkg_c",
        ["pkg_b", "pkg_a"],
        """
from skfd.api_v2 import BuildContextV2

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    pkg_b = ctx.deps.pkg_b
    pkg_a = ctx.deps.pkg_a
    wff = pkg_a["wff"]
    ph = pkg_a["ph"]
    const_b = pkg_b["const_b"]
    const_c = mm.sym.const("const_c")
    ax_c = mm.sym.label("ax-c")
    mm.a(ax_c, tc=wff, expr=[const_b, const_c, ph])
    mm.export(const_c, ax_c)
""",
    )

    # Run Driver
    runner = DriverRunner(src, target)
    runner.execute_all()

    # Assert build success
    assert "pkg_a" in runner.lirs
    assert "pkg_b" in runner.lirs
    assert "pkg_c" in runner.lirs

    # Verify pkg_b (Should include A and B)
    runner.verify_package("pkg_b")
    out_b = target / "pkg_b_full.mm"
    names_b = target / "pkg_b_full.names.json"
    assert out_b.exists()
    assert names_b.exists()
    content_b = out_b.read_text()
    assert "const_a" in content_b
    assert "const_b" in content_b
    assert "const_c" not in content_b  # Downstream

    # Verify pkg_c (Should include A, B, and C)
    runner.verify_package("pkg_c")
    out_c = target / "pkg_c_full.mm"
    names_c = target / "pkg_c_full.names.json"
    assert out_c.exists()
    assert names_c.exists()
    content_c = out_c.read_text()
    assert "const_a" in content_c
    assert "const_b" in content_c
    assert "const_c" in content_c
