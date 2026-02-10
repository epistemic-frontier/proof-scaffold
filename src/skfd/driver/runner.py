# skfd/driver/runner.py
from __future__ import annotations

import logging
import inspect
from pathlib import Path
from typing import Any

import tomllib

from skfd.api_v2 import BuildConfig, BuildContextV2, DepsView, ExportsView, UnitMeta
from skfd.builder_v2 import MMBuilderV2
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver

from .discover import find_packages, get_package_deps, load_build_module
from .graph import sort_packages

logger = logging.getLogger(__name__)


class DriverRunner:
    def __init__(self, root: Path, target_dir: Path):
        self.root = root
        self.target_dir = target_dir
        self.interner = SymbolInterner()
        self.origin_table = OriginTable()
        self.names = NameResolver()
        self.cfg = BuildConfig()

        # Build artifacts
        self.exports_by_pkg: dict[str, dict[str, int]] = {}
        self.lirs: dict[str, ProofUnitIR] = {}

        # Discovered info
        self.build_paths: dict[str, Path] = {}
        self.metas: dict[str, UnitMeta] = {}
        self.deps_graph: dict[str, list[str]] = {}

    def discover(self) -> None:
        """Scan and plan build order."""
        for name, _, path in find_packages(self.root):
            try:
                deps = get_package_deps(path)
                self.build_paths[name] = path
                self.metas[name] = UnitMeta(
                    dist_name=name, module_name=path.parent.name, build_path=path
                )
                self.deps_graph[name] = deps
            except Exception as e:
                logger.error(f"Failed to discover dependencies for {name}: {e}")
                raise

    def _resolve_dependency(self, name: str) -> None:
        """Recursively resolve missing dependencies from installed packages."""
        if name in self.build_paths:
            return

        project_root = self.root.parent
        pyproject = project_root / "pyproject.toml"
        if pyproject.exists():
            try:
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                sources = (
                    data.get("tool", {})
                    .get("uv", {})
                    .get("sources", {})
                )
                src_spec = sources.get(name)
                if isinstance(src_spec, dict):
                    rel = src_spec.get("path")
                    if isinstance(rel, str):
                        dep_root = (project_root / rel).resolve()
                        dep_src = dep_root / "src"
                        if dep_src.exists():
                            for dep_name, _, build_path in find_packages(dep_src):
                                if dep_name != name:
                                    continue
                                deps = get_package_deps(build_path)
                                self.build_paths[dep_name] = build_path
                                self.metas[dep_name] = UnitMeta(
                                    dist_name=dep_name,
                                    module_name=build_path.parent.name,
                                    build_path=build_path,
                                )
                                self.deps_graph[dep_name] = deps
                                for dep in deps:
                                    self._resolve_dependency(dep)
                                return
            except Exception:
                pass

        # Attempt to load external module
        # Note: External modules are installed, so we don't have a source path usually.
        # We rely on importlib to find them.
        # This part is tricky with the new path-based approach.
        # But `load_external_build_module` returns a module.
        # We can handle external modules differently (store in a separate dict?)
        # Or just treat them as "built".
        
        # For now, let's assume we can load them and check deps.
        from .discover import load_external_build_module

        mod = load_external_build_module(name)
        if not mod:
            raise ValueError(
                f"Dependency '{name}' not found locally or as installed package"
            )

        logger.info(f"Resolved external dependency: {name}")
        # We store 'None' as path for external modules to indicate "already loaded/installed"
        # But wait, we need to build them?
        # If they are installed packages, they should provide pre-built artifacts?
        # Or we run their build.py?
        # ProofScaffold assumes we run build.py to generate IR.
        # So we treat them as "modules with no path but a loaded module object".
        # This requires `build_paths` to store `Path | PackageModule`.
        
        # Hack: Store the module in a separate cache
        if not hasattr(self, "_external_modules"):
            self._external_modules = {}
        self._external_modules[name] = mod
        self.metas[name] = UnitMeta(dist_name=name, module_name=name, build_path=None)
        self.deps_graph[name] = []

    def execute_all(self) -> None:
        """Build all packages in order."""
        self.discover()

        # Ensure full closure is resolved (scan known deps)
        for pkg in list(self.build_paths.keys()):
            for dep in self.deps_graph.get(pkg, []):
                self._resolve_dependency(dep)

        order = sort_packages(self.deps_graph)
        logger.info(f"Build plan: {order}")

        for pkg_name in order:
            self.build_package(pkg_name)

    def build_package(self, name: str) -> None:
        """Execute build() for a single package."""
        logger.info(f"Building {name}...")
        deps_names = self.deps_graph[name]

        for dep in deps_names:
            if dep not in self.exports_by_pkg:
                raise ValueError(f"Dependency '{dep}' must be built before '{name}'")

        mod: Any
        if name in self.build_paths:
            build_path = self.build_paths[name]
            mod = load_build_module(build_path)
        else:
            mod = self._external_modules[name]

        if not hasattr(mod, "build"):
            raise ValueError(f"build.py for '{name}' is missing a build(ctx) entrypoint")

        sig = inspect.signature(mod.build)
        params = list(sig.parameters.values())
        wants_ctx = (
            len(params) == 1
            and params[0].kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        )
        if not wants_ctx:
            raise TypeError(
                f"build() for '{name}' must have signature build(ctx: BuildContextV2) -> None"
            )

        meta = self.metas[name]
        dep_exports: dict[str, ExportsView] = {}
        dep_metas: dict[str, UnitMeta] = {}
        for dep in deps_names:
            dep_exports[dep] = ExportsView(self.exports_by_pkg[dep])
            dep_metas[dep] = self.metas[dep]

        deps_view = DepsView(deps=dep_exports, metas=dep_metas)
        mm = MMBuilderV2(
            interner=self.interner,
            origin_table=self.origin_table,
            names=self.names,
            unit_id=name,
            origin_module_id=meta.module_name,
            cfg=self.cfg,
        )
        ctx = BuildContextV2(
            mm=mm,
            deps=deps_view,
            unit=meta,
            names=self.names,
            cfg=self.cfg,
            log=logger,
        )
        mod.build(ctx)
        unit = mm.finish()

        symtab = self.interner.symbol_table()
        exports_dict: dict[str, int] = {}
        for sid in unit.exports:
            sym = symtab.get(sid)
            if sym is not None:
                exports_dict[sym.local_name] = sid
        self.exports_by_pkg[name] = exports_dict

        # Pre-check: LIR must not be empty to avoid emitting degenerate monoliths
        if not getattr(unit, "lir_stmts", None):
            raise ValueError(f"Build produced empty LIR for package '{name}'")
        self.lirs[name] = unit

    def verify_package(self, name: str, conformance_level: int = 0) -> None:
        """
        Verify a specific package using Transient Monolith strategy.
        """
        if name not in self.lirs:
            raise ValueError(f"Package {name} has not been built yet.")

        # 1. Identify dependencies
        chain = self._get_transitive_deps(name)
        chain.append(name)

        logger.info(f"Verifying {name} (monolith chain: {chain})...")

        # 2. Collect dependency units
        units = [self.lirs[n] for n in chain]

        # 3. Emit
        self.target_dir.mkdir(parents=True, exist_ok=True)
        outfile = self.target_dir / f"{name}_full.mm"
        mapfile = self.target_dir / f"{name}_full.mm.map"
        namesfile = self.target_dir / f"{name}_full.names.json"

        import json

        with open(outfile, "w", encoding="utf-8") as f:
            # Pass list of units to LinkerV1
            res = LinkerV1.link(
                units=units,
                origin_table=self.origin_table,
                interner=self.interner,
                conformance_level=conformance_level,
            )
            f.write(res.mm_text)

        with open(mapfile, "w", encoding="utf-8") as f:
            map_data = {
                "format": "skfd-sourcemap-v1",
                "mappings": res.source_map.to_json(),
                "origins": res.ctx.origin_table.dump(root=self.root),
            }
            json.dump(map_data, f, indent=2)

        with open(namesfile, "w", encoding="utf-8") as f:
            json.dump(self.names.used_mappings(), f, indent=2, sort_keys=True)

        logger.info(f"Generated verification monolith: {outfile} (Map: {mapfile})")

    def _get_transitive_deps(self, root: str) -> list[str]:
        """Return list of dependencies in topological order (deps only)."""
        visited = set()
        result = []

        def visit(n: str):
            if n in visited:
                return
            visited.add(n)
            for dep in self.deps_graph.get(n, []):
                visit(dep)
            if n != root:
                result.append(n)

        # Iterate deps_graph[root] and visit
        for dep in self.deps_graph.get(root, []):
            visit(dep)

        return result
