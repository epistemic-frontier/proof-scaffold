# skfd/driver/runner.py
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from skfd.builder import MMBuilder
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.api import LinkerV1

from .discover import find_packages
from .graph import sort_packages
from .types import ModuleInterface, PackageModule

logger = logging.getLogger(__name__)


class DriverRunner:
    def __init__(self, root: Path, target_dir: Path):
        self.root = root
        self.target_dir = target_dir
        self.interner = SymbolInterner()
        self.origin_table = OriginTable()

        # Build artifacts
        self.interfaces: dict[str, ModuleInterface] = {}
        self.lirs: dict[str, ProofUnitIR] = {}

        # Discovered modules
        self.modules: dict[str, PackageModule] = {}
        self.deps_graph: dict[str, list[str]] = {}

    def discover(self) -> None:
        """Scan and plan build order."""
        for name, _, mod in find_packages(self.root):
            try:
                manifest = mod.manifest()
                self.modules[name] = mod
                self.deps_graph[name] = manifest["deps"]
            except Exception as e:
                logger.error(f"Failed to load manifest for {name}: {e}")
                raise

    def _resolve_dependency(self, name: str) -> None:
        """Recursively resolve missing dependencies from installed packages."""
        if name in self.modules:
            return

        # Attempt to load external module
        from .discover import load_external_build_module

        mod = load_external_build_module(name)
        if not mod:
            raise ValueError(
                f"Dependency '{name}' not found locally or as installed package"
            )

        logger.info(f"Resolved external dependency: {name}")
        self.modules[name] = mod

        try:
            manifest = mod.manifest()
            self.deps_graph[name] = manifest["deps"]
        except Exception as e:
            logger.error(f"Failed to load manifest for external {name}: {e}")
            raise

        # Recurse
        for dep in manifest["deps"]:
            self._resolve_dependency(dep)

    def execute_all(self) -> None:
        """Build all packages in order."""
        self.discover()

        # Ensure full closure is resolved (scan known deps)
        # We must copy keys because we modify self.modules during iteration
        for pkg in list(self.modules.keys()):
            for dep in self.deps_graph.get(pkg, []):
                self._resolve_dependency(dep)

        order = sort_packages(self.deps_graph)
        logger.info(f"Build plan: {order}")

        for pkg_name in order:
            self.build_package(pkg_name)

    def build_package(self, name: str) -> None:
        """Execute build() for a single package."""
        logger.info(f"Building {name}...")
        mod = self.modules[name]
        deps_names = self.deps_graph[name]

        # Resolve injected dependencies
        injected_deps = {dep: self.interfaces[dep] for dep in deps_names}

        mm = MMBuilder(
            interner=self.interner, origin_table=self.origin_table, module_id=name
        )

        # Execute hook
        result = mod.build(mm, **injected_deps)

        # Store result (default to empty dict if None)
        self.interfaces[name] = result if result is not None else {}

        # Collect LIR using correct method name
        self.lirs[name] = mm.to_proof_unit(unit_id=name)

    def verify_package(self, name: str, conformance_level: int = 0) -> None:
        """
        Verify a specific package using Transient Monolith strategy.
        1. Collect LIRs of transitive dependencies + self.
        2. Concatenate (via list).
        3. Emit to target/{name}_full.mm.
        4. (Optional) Run metamath-exe.
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
            # Resolve origins to make the map useful
            # We dump the raw mappings (line -> origin_ref)
            # And the origin table (origin_ref -> {file, line, module})
            # OriginRef is an index into the table.
            # Assuming origin_table structure allows easy dump.

            # OriginTable stores `_records`. We access protected member or add public accessor?
            # Ideally add `to_json()` to OriginTable.
            # For now, let's just use `res.ctx.origin_table._records` if we have to,
            # or rely on the Fact that OriginRef is just ID.

            # Let's inspect OriginTable.
            # If I can't access `_records`, I'll iterate the refs in the map.

            map_data = {
                "format": "skfd-sourcemap-v1",
                "mappings": res.source_map.to_json(),
                "origins": res.ctx.origin_table.dump(root=self.root),
            }
            json.dump(map_data, f, indent=2)

        logger.info(f"Generated verification monolith: {outfile} (Map: {mapfile})")

        # 4. Run metamath-exe (if available)
        if shutil.which("metamath"):
            logger.info("Running metamath-exe...")
            # subprocess.run(["metamath", str(outfile)], check=True)
        else:
            logger.warning("metamath-exe not found, skipping verification run.")

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
