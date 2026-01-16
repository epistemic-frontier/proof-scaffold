# skfd/linker/passes/stage4_topo_sort.py
from __future__ import annotations

import graphlib

from skfd.core.context import Context
from skfd.core.diag import Diagnostic, LinkerDiagError
from skfd.core.lir import Theorem
from skfd.core.unit import ProofUnitIR
from skfd.linker.passes.stage2_contracts import ContractIndex


def run(units: list[ProofUnitIR], contracts: ContractIndex) -> list[ProofUnitIR]:
    """
    Sort units topologically based on dependencies found in contracts.
    
    1. Build a dependency graph of Units.
    2. Units define assertions (exports).
    3. Units use assertions (in theorem proofs).
    """

    # Map SymbolId (Label) -> UnitId (Owner)
    # We only care about exported symbols for inter-unit dependency.
    label_owner: dict[int, str] = {}
    unit_lut: dict[str, ProofUnitIR] = {}

    for u in units:
        unit_lut[u.unit_id] = u
        for label_id in u.exports:
            label_owner[label_id] = u.unit_id

    # Build Graph: UnitId -> set[UnitId] (dependencies)
    graph: dict[str, set[str]] = {u.unit_id: set() for u in units}

    for u in units:
        uid = u.unit_id
        # Scan internal theorems for usage
        # We use the ContractIndex now!
        # Which assertions does this unit define?
        # We iterate LIR to find definitions (or we could index unit content earlier).
        # Stage 2 results are keyed by SymbolId.
        
        # We need to know which theorems belong to this unit to look up their details.
        # This is where 'indexing' vs 'scanning' tradeoff comes in.
        # Scanning key LIR structures is cheap enough.
        
        for st in u.lir_stmts:
            if isinstance(st, Theorem):
                # Look up details
                # If stage 2 ran correctly, details should exist.
                det = contracts.details.get(st.label)
                if det:
                    for dep_label in det.direct_dependencies:
                        if dep_label in label_owner:
                            owner = label_owner[dep_label]
                            # Self-dependency is fine (and ignored by topo sort usually)
                            # But graphlib handles DAGs.
                            if owner != uid:
                                graph[uid].add(owner)

    # Topo Sort
    sorter = graphlib.TopologicalSorter(graph)
    
    try:
        # Convert to list (consumption)
        sorted_unit_ids = list(sorter.static_order())
    except graphlib.CycleError as e:
        # e.args[1] is the chain of nodes in cycle
        cycle = e.args[1] if len(e.args) > 1 else []
        cycle_str = " -> ".join(str(c) for c in cycle)
        
        # We attribute the error to the first unit in the cycle we have a handle on, 
        # or just a generic error attached to the primary unit passed in context?
        # Since 'run' doesn't take 'ctx' with 'primary unit', we pick the first available.
        
        err_unit_id = cycle[-1] if cycle else units[0].unit_id
        # Find origin ref from LUT
        err_unit = unit_lut.get(err_unit_id, units[0])

        raise LinkerDiagError(
            Diagnostic(
                error_code="E_DEPENDENCY_CYCLE",
                message=f"Circular dependency detected between units: {cycle_str}",
                primary_origin_ref=err_unit.origin_ref,
                details={"cycle": cycle},
                origin_chain=({"stage": 4},)
            )
        )

    # Reconstruct list[ProofUnitIR]
    return [unit_lut[uid] for uid in sorted_unit_ids]
