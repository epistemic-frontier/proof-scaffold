from pathlib import Path

import pytest
from skfd.driver.runner import DriverRunner
from skfd.proof import ProofCoverageError


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


def _create_pkg(src_root: Path, *, module: str, dist: str, deps: list[str], build_code: str) -> None:
    pkg_dir = src_root / module
    pkg_dir.mkdir()
    _write_pyproject(pkg_dir, name=dist, deps=deps)
    (pkg_dir / "build.py").write_text(build_code, encoding="utf-8")


def test_runner_build_ctx_and_deps_view_aliasing(workspace) -> None:
    src, target = workspace

    _create_pkg(
        src,
        module="prelude",
        dist="metamath-prelude",
        deps=[],
        build_code="""
from skfd.api_v2 import BuildContextV2

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    wff = mm.sym.const("wff")
    ph = mm.sym.var("φ")
    mm.auto.floating(ph, tc=wff)
    ax1 = mm.sym.label("ax-1")
    mm.a(ax1, tc=wff, expr=[ph])
    mm.export(wff, ph, ax1)
""",
    )

    _create_pkg(
        src,
        module="logic",
        dist="metamath-logic",
        deps=["metamath-prelude"],
        build_code="""
from skfd.api_v2 import BuildContextV2

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    prelude1 = ctx.deps.prelude
    prelude2 = ctx.deps["metamath-prelude"]
    prelude3 = ctx.deps.metamath_prelude
    assert prelude1["wff"] == prelude2["wff"] == prelude3["wff"]

    wff = prelude1["wff"]
    ph = prelude1["ph"]
    th1 = mm.sym.label("th-1")
    mm.p(th1, tc=wff, expr=[ph], proof=[prelude1["ax-1"]])
    mm.export(th1)
""",
    )

    runner = DriverRunner(src, target)
    runner.execute_all()

    assert runner.metas["metamath-prelude"].kind == "foundation"
    assert runner.build_order[0] == "metamath-prelude"

    runner.verify_package("metamath-logic")
    out = target / "metamath-logic_full.mm"
    assert out.exists()
    mm_text = out.read_text(encoding="utf-8")
    assert "ax-1" in mm_text
    assert "th-1" in mm_text


def test_runner_records_declared_proof_coverage(workspace) -> None:
    src, target = workspace

    _create_pkg(
        src,
        module="pkg",
        dist="pkg",
        deps=[],
        build_code="""
from skfd.api_v2 import BuildContextV2

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    wff = mm.sym.const("wff")
    ph = mm.sym.var("ph")
    mm.auto.floating(ph, tc=wff)
    th1 = mm.sym.label("th-1")
    mm.a(th1, tc=wff, expr=[ph])
    mm.export(th1)
    ctx.coverage.declare_labels("public", ["missing", "th-1"])
""",
    )

    runner = DriverRunner(src, target)
    runner.execute_all()

    report = runner.coverage_report("pkg")
    assert report is not None
    assert report.has_declarations
    assert report.declared_labels == ("missing", "th-1")
    assert report.declared_but_unemitted == ("missing",)
    assert report.ok


def test_runner_fails_when_required_declared_labels_are_unemitted(workspace) -> None:
    src, target = workspace

    _create_pkg(
        src,
        module="pkg",
        dist="pkg",
        deps=[],
        build_code="""
from skfd.api_v2 import BuildContextV2

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    wff = mm.sym.const("wff")
    ph = mm.sym.var("ph")
    mm.auto.floating(ph, tc=wff)
    th1 = mm.sym.label("th-1")
    mm.a(th1, tc=wff, expr=[ph])
    mm.export(th1)
    ctx.coverage.declare_labels("public", ["missing", "th-1"])
    ctx.coverage.require_all_declared_verified()
""",
    )

    runner = DriverRunner(src, target)
    with pytest.raises(ProofCoverageError) as exc_info:
        runner.execute_all()

    assert "missing required labels: missing" in str(exc_info.value)
