from __future__ import annotations

import importlib.metadata as md
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import skfd.driver.discover as discover_mod
import skfd.driver.runner as runner_mod
from skfd.api_v2 import UnitMeta
from skfd.driver.runner import DriverRunner


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


def _seed_runner(tmp_path: Path, *, name: str = "pkg") -> DriverRunner:
    r = DriverRunner(tmp_path / "src", tmp_path / "target")
    r.build_paths[name] = tmp_path / "src" / name / "build.py"
    r.metas[name] = UnitMeta(dist_name=name, module_name=name, build_path=r.build_paths[name])
    r.deps_graph[name] = []
    return r


def test_requirement_helpers_filter_proof_scaffold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert runner_mod._norm_dist_name("Demo_Pkg.Name") == "demo-pkg-name"
    assert runner_mod._parse_requirement_name("demo>=1; python_version>'3.11'") == "demo"

    monkeypatch.setattr(
        md,
        "distribution",
        lambda name: SimpleNamespace(
            requires=["proof-scaffold>=0.0.5", "dep-one<2", "dep_two==1"]
        ),
    )
    assert runner_mod._external_requires("demo") == ["dep-one", "dep_two"]

    def missing(_name: str) -> Any:
        raise md.PackageNotFoundError(_name)

    monkeypatch.setattr(md, "distribution", missing)
    assert runner_mod._external_requires("missing") == []


def test_resolve_dependency_from_uv_sources(tmp_path: Path) -> None:
    project = tmp_path / "project"
    src = project / "src"
    target = project / "target"
    dep_root = tmp_path / "dep"
    _write(
        project / "pyproject.toml",
        """
        [tool.uv.sources]
        dep-dist = { path = "../dep" }
        """,
    )
    _write(dep_root / "src" / "dep_mod" / "build.py", "")
    _write(dep_root / "src" / "dep_mod" / "pyproject.toml", '[project]\nname = "dep-dist"\n')

    r = DriverRunner(src, target)
    r._resolve_dependency("dep-dist")

    assert r.build_paths["dep-dist"] == dep_root.resolve() / "src" / "dep_mod" / "build.py"
    assert r.metas["dep-dist"].module_name == "dep_mod"
    assert r.deps_graph["dep-dist"] == []


def test_resolve_dependency_raises_when_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = DriverRunner(tmp_path / "src", tmp_path / "target")
    monkeypatch.setattr(discover_mod, "load_external_build_module", lambda _name: None)

    with pytest.raises(ValueError, match="not found"):
        r._resolve_dependency("missing-dep")


def test_build_package_rejects_missing_or_bad_build_entrypoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = _seed_runner(tmp_path)

    monkeypatch.setattr(runner_mod, "load_build_module", lambda _path: SimpleNamespace())
    with pytest.raises(ValueError, match="missing a build"):
        r.build_package("pkg")

    monkeypatch.setattr(
        runner_mod,
        "load_build_module",
        lambda _path: SimpleNamespace(build=lambda: None),
    )
    with pytest.raises(TypeError, match="must have signature"):
        r.build_package("pkg")


def test_build_package_checks_dependency_order_and_empty_lir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = _seed_runner(tmp_path)
    r.deps_graph["pkg"] = ["dep"]

    with pytest.raises(ValueError, match="must be built before"):
        r.build_package("pkg")

    r.deps_graph["pkg"] = []

    def empty_build(_ctx: Any) -> None:
        return None

    monkeypatch.setattr(
        runner_mod,
        "load_build_module",
        lambda _path: SimpleNamespace(build=empty_build),
    )
    with pytest.raises(ValueError, match="empty LIR"):
        r.build_package("pkg")


def test_build_package_uses_external_module_cache(tmp_path: Path) -> None:
    r = DriverRunner(tmp_path / "src", tmp_path / "target")
    r.deps_graph["ext"] = []
    r.metas["ext"] = UnitMeta(dist_name="ext", module_name="ext_mod", build_path=None)

    def build(ctx: Any) -> None:
        wff = ctx.mm.sym.const("wff")
        ph = ctx.mm.sym.var("ph")
        ctx.mm.auto.floating(ph, tc=wff)
        ax = ctx.mm.sym.label("ax")
        ctx.mm.a(ax, tc=wff, expr=[ph])
        ctx.mm.export(ax)

    r._external_modules = {"ext": SimpleNamespace(build=build)}
    r.build_package("ext")

    assert "ext" in r.lirs
    assert "ax" in r.exports_by_pkg["ext"]


def test_verify_package_requires_built_lir_and_sorts_transitive_deps(tmp_path: Path) -> None:
    r = DriverRunner(tmp_path / "src", tmp_path / "target")

    with pytest.raises(ValueError, match="has not been built"):
        r.verify_package("pkg")

    r.deps_graph = {"root": ["b", "a"], "a": ["base"], "b": ["base"], "base": []}
    assert r._get_transitive_deps("root") == ["base", "b", "a"]


def test_discover_reraises_dependency_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = DriverRunner(tmp_path / "src", tmp_path / "target")
    path = tmp_path / "src" / "pkg" / "build.py"

    monkeypatch.setattr(runner_mod, "find_packages", lambda _root: iter([("pkg", path.parent, path)]))
    monkeypatch.setattr(
        runner_mod,
        "get_package_deps",
        lambda _path: (_ for _ in ()).throw(RuntimeError("bad deps")),
    )

    with pytest.raises(RuntimeError, match="bad deps"):
        r.discover()
