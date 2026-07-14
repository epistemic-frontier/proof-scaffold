# skfd/linker/passes/stage2_contracts.py
from __future__ import annotations

from dataclasses import dataclass, field

from skfd.core.contracts import AssertionContract, TheoremDetails
from skfd.core.lir import (
    Axiom,
    EssentialHyp,
    FloatingHyp,
    ScopeEnter,
    ScopeExit,
    Theorem,
)
from skfd.core.symbols import SymbolDef, SymbolId
from skfd.core.unit import ProofUnitIR


@dataclass(frozen=True)
class ContractIndex:
    """Results of contract extraction."""

    # usage: contracts[label_id] -> Contract
    contracts: dict[SymbolId, AssertionContract] = field(default_factory=dict)
    # usage: details[label_id] -> Details
    details: dict[SymbolId, TheoremDetails] = field(default_factory=dict)


def run(units: list[ProofUnitIR], symtab: dict[SymbolId, SymbolDef]) -> ContractIndex:
    """
    Stage 2: Contract Extraction.

    Analyses units to determine:
    1. Interface definition of every $a/$p (Contract)
    2. Dependency usage of every $p (Details)
    """
    contracts: dict[SymbolId, AssertionContract] = {}
    details: dict[SymbolId, TheoremDetails] = {}

    # Stage 5 emits foundation statements at top level, so their top-level
    # hypotheses are ambient for every later unit. Ordinary units receive an
    # implicit outer block and must not leak their hypotheses to the next unit.
    ambient_f: list[FloatingHyp] = []
    ambient_e: list[EssentialHyp] = []

    for u in units:
        scope_stack_f: list[list[FloatingHyp]] = []
        scope_stack_e: list[list[EssentialHyp]] = []
        current_frame_f = list(ambient_f)
        current_frame_e = list(ambient_e)

        for st in u.lir_stmts:
            if isinstance(st, ScopeEnter):
                scope_stack_f.append(list(current_frame_f))
                scope_stack_e.append(list(current_frame_e))

            elif isinstance(st, ScopeExit):
                if scope_stack_f:
                    current_frame_f = scope_stack_f.pop()
                    current_frame_e = scope_stack_e.pop()
                else:
                    current_frame_f = []
                    current_frame_e = []

            elif isinstance(st, FloatingHyp):
                current_frame_f.append(st)

            elif isinstance(st, EssentialHyp):
                current_frame_e.append(st)

            elif isinstance(st, Axiom | Theorem):
                m_hyps = [h.label for h in current_frame_e]
                required_vars: set[SymbolId] = set()

                def scan_vars(expr: tuple[SymbolId, ...]) -> None:
                    for t in expr:
                        if symtab[t].kind == "Var":
                            required_vars.add(t)

                scan_vars(tuple(st.expr))
                for h_stmt in current_frame_e:
                    scan_vars(tuple(h_stmt.expr))

                m_vars = [
                    floating.label
                    for floating in current_frame_f
                    if floating.var in required_vars
                ]
                mandatory_var_ids = sorted(
                    required_vars,
                    key=lambda sid: (
                        symtab[sid].origin_module_id,
                        symtab[sid].local_name,
                        sid,
                    ),
                )

                contracts[st.label] = AssertionContract(
                    label=st.label,
                    mandatory_hyps=m_hyps,
                    mandatory_vars=m_vars,
                    mandatory_var_ids=mandatory_var_ids,
                )

                if isinstance(st, Theorem):
                    details[st.label] = TheoremDetails(
                        label=st.label,
                        direct_dependencies=set(st.proof),
                    )

        if u.kind == "foundation":
            ambient_f = current_frame_f
            ambient_e = current_frame_e

    return ContractIndex(contracts, details)
