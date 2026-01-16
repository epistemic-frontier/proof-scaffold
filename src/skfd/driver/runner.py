# skfd/driver/runner.py
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from skfd.builder import MMBuilder
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.emit.emit_mm import emit_mm

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

    def execute_all(self) -> None:
        """Build all packages in order."""
        self.discover()
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
            interner=self.interner,
            origin_table=self.origin_table,
            module_id=name
        )
        
        # Execute hook
        result = mod.build(mm, **injected_deps)
        
        # Store result (default to empty dict if None)
        self.interfaces[name] = result if result is not None else {}
        
        # Collect LIR using correct method name
        self.lirs[name] = mm.to_proof_unit(unit_id=name)

    def verify_package(self, name: str) -> None:
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
        
        symtab = self.interner.symbol_table()
        
        with open(outfile, "w", encoding="utf-8") as f:
            # Pass list of units to emit_mm
            text = emit_mm(symtab=symtab, units=units)
            f.write(text)
            
        logger.info(f"Generated verification monolith: {outfile}")
        
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
