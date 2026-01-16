# skfd/linker/passes/stage3_disjoint.py
from __future__ import annotations

from skfd.core.contracts import AssertionContract
from skfd.core.lir import Axiom, DisjointVar, ScopeEnter, ScopeExit, Theorem
from skfd.core.symbols import SymbolDef, SymbolId
from skfd.core.unit import ProofUnitIR
from skfd.linker.passes.stage2_contracts import ContractIndex


def run(
    units: list[ProofUnitIR],
    symtab: dict[SymbolId, SymbolDef],
    contracts: ContractIndex,
) -> ContractIndex:
    """
    Stage 3: $d Processing.

    Scans units for active DisjointVar ($d) statements and enriches
    the AssertionContract for each $a/$p.

    Mode A (Pass-Through):
    We collect all active $d constraints available at the assertion point.
    """

    for u in units:
        # Scope tracking state
        # A disjoint constraint is valid if it is active in the current scope.

        scope_stack_dj: list[list[DisjointVar]] = []
        current_frame_dj: list[DisjointVar] = []

        for st in u.lir_stmts:
            if isinstance(st, ScopeEnter):
                scope_stack_dj.append(list(current_frame_dj))
                # Scopes inherit
                # Current frame continues with outer definitions?
                # Usually standard Metamath implies nested scopes see outer.
                # So we keep current_frame_dj as is?
                # Actually, ScopeEnter means "Push current state".
                # New declarations will be added to current_frame.
                # ScopeExit means "Pop state".
                pass

            elif isinstance(st, ScopeExit):
                if scope_stack_dj:
                    current_frame_dj = scope_stack_dj.pop()
                else:
                    current_frame_dj = []

            elif isinstance(st, DisjointVar):
                current_frame_dj.append(st)

            elif isinstance(st, Axiom | Theorem):
                # Found assertion. Update its contract.
                # In Mode A, we assume "All active $d" are relevant.
                # A stricter Mode B would check if the vars are actually used in the assertion.
                # For now, we capture the environment.

                # Convert active DisjointVar statements to list[set[SymbolId]]
                # Note: Metamath $d x y z means x,y disjoint; y,z disjoint; x,z disjoint.
                # We store the set {x, y, z}.

                dv_specs = []
                for dj in current_frame_dj:
                    dv_specs.append(set(dj.vars))

                # Update contract in place?
                # ContractIndex contains immutable AssertionContract objects (frozen).
                # We need to replace them.

                old_c = contracts.contracts.get(st.label)
                if old_c:
                    new_c = AssertionContract(
                        label=old_c.label,
                        mandatory_hyps=old_c.mandatory_hyps,
                        mandatory_vars=old_c.mandatory_vars,
                        distinct_vars=dv_specs,
                    )
                    contracts.contracts[st.label] = new_c

    return contracts
