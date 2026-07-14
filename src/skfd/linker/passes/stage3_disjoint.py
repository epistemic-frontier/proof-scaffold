# skfd/linker/passes/stage3_disjoint.py
from __future__ import annotations

from skfd.core.contracts import AssertionContract
from skfd.core.disjoint import normalize_dv_pairs
from skfd.core.lir import (
    Axiom,
    DisjointVar,
    FloatingHyp,
    ScopeEnter,
    ScopeExit,
    Theorem,
)
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

    Scans units for active DisjointVar ($d) statements and enriches the
    AssertionContract for each $a/$p with its mandatory DV pairs.

    Active groups are expanded pairwise. A pair is part of an assertion's
    public contract only when both variables are mandatory for that assertion;
    proof-only active pairs remain in the LIR but do not enter the contract.
    """

    floating_var_by_label = {
        st.label: st.var
        for unit in units
        for st in unit.lir_stmts
        if isinstance(st, FloatingHyp)
    }

    ambient_dv_pairs: set[tuple[SymbolId, SymbolId]] = set()

    for u in units:
        scope_stack_dv: list[set[tuple[SymbolId, SymbolId]]] = []
        active_dv_pairs = set(ambient_dv_pairs)

        for st in u.lir_stmts:
            if isinstance(st, ScopeEnter):
                scope_stack_dv.append(set(active_dv_pairs))

            elif isinstance(st, ScopeExit):
                if scope_stack_dv:
                    active_dv_pairs = scope_stack_dv.pop()
                else:
                    active_dv_pairs = set()

            elif isinstance(st, DisjointVar):
                active_dv_pairs.update(
                    normalize_dv_pairs(
                        (
                            (left, right)
                            for index, left in enumerate(st.vars)
                            for right in st.vars[index + 1 :]
                        ),
                        symtab=symtab,
                    )
                )

            elif isinstance(st, Axiom | Theorem):
                old_c = contracts.contracts.get(st.label)
                if old_c:
                    mandatory_vars = set(old_c.mandatory_var_ids)
                    if not mandatory_vars and old_c.mandatory_vars:
                        missing_floating = [
                            label
                            for label in old_c.mandatory_vars
                            if label not in floating_var_by_label
                        ]
                        if missing_floating:
                            raise ValueError(
                                "mandatory $f labels missing from LIR: "
                                f"{sorted(missing_floating)}"
                            )
                        mandatory_vars = {
                            floating_var_by_label[label]
                            for label in old_c.mandatory_vars
                        }
                    mandatory_dv_pairs = list(
                        normalize_dv_pairs(
                            (
                                pair
                                for pair in active_dv_pairs
                                if pair[0] in mandatory_vars
                                and pair[1] in mandatory_vars
                            ),
                            symtab=symtab,
                        )
                    )
                    new_c = AssertionContract(
                        label=old_c.label,
                        mandatory_hyps=old_c.mandatory_hyps,
                        mandatory_vars=old_c.mandatory_vars,
                        mandatory_var_ids=old_c.mandatory_var_ids,
                        distinct_vars=mandatory_dv_pairs,
                    )
                    contracts.contracts[st.label] = new_c

        if u.kind == "foundation":
            ambient_dv_pairs = active_dv_pairs

    return contracts
