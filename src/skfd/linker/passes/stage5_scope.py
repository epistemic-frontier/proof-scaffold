# skfd/linker/passes/stage5_scope.py
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from skfd.core.lir import (
    Axiom,
    Comment,
    ConstDecl,
    DisjointVar,
    EssentialHyp,
    FloatingHyp,
    ScopeEnter,
    ScopeExit,
    Theorem,
    VarDecl,
)
from skfd.core.symbols import SymbolDef, SymbolId
from skfd.core.unit import ProofUnitIR


@dataclass(frozen=True)
class ScopeFrame:
    """A scoped region ${ ... $} in the linear output."""

    stmts: list[object] = field(default_factory=list)


@dataclass(frozen=True)
class LinearPlan:
    """The complete instruction set for Stage 7 emission."""

    preamble: list[str]
    header_consts: list[SymbolId]  # Sorted IDs
    header_vars: list[SymbolId]  # Sorted IDs
    frames: list[ScopeFrame]  # Top-level frames (usually one per unit, or flattened)


def run(units: list[ProofUnitIR], symtab: Mapping[SymbolId, SymbolDef]) -> LinearPlan:
    """
    Transform resolved units into a linear emission plan.
    Separates global header declarations from scoped body content.
    """
    preamble: list[str] = []
    used_ids: set[SymbolId] = set()
    frames: list[ScopeFrame] = []

    # 1. Collect Usage & Build Body Frames
    for u in units:
        current_stmts: list[object] = []

        for st in u.lir_stmts:
            if isinstance(st, ConstDecl):
                used_ids.update(st.tokens)
                # Do NOT add to body
            elif isinstance(st, VarDecl):
                used_ids.update(st.tokens)
                # Do NOT add to body
            elif isinstance(st, FloatingHyp):
                used_ids.add(st.label)
                used_ids.add(st.typecode)
                used_ids.add(st.var)
                current_stmts.append(st)
            elif isinstance(st, EssentialHyp):
                used_ids.add(st.label)
                used_ids.add(st.typecode)
                used_ids.update(st.expr)
                current_stmts.append(st)
            elif isinstance(st, Axiom):
                used_ids.add(st.label)
                used_ids.add(st.typecode)
                used_ids.update(st.expr)
                current_stmts.append(st)
            elif isinstance(st, Theorem):
                used_ids.add(st.label)
                used_ids.add(st.typecode)
                used_ids.update(st.expr)
                used_ids.update(st.proof)
                current_stmts.append(st)
            elif isinstance(st, DisjointVar):
                used_ids.update(st.vars)
                current_stmts.append(st)
            elif isinstance(st, ScopeEnter):
                current_stmts.append(st)
            elif isinstance(st, ScopeExit):
                current_stmts.append(st)
            elif isinstance(st, Comment):
                current_stmts.append(st)

        # Foundation statements remain top-level so foundation-owned `$f` labels
        # stay ambient. Ordinary units receive an outer frame so local `$f/$e`
        # labels cannot leak into downstream units.
        if u.kind == "foundation" or not current_stmts:
            frames.append(ScopeFrame(stmts=current_stmts))
        else:
            frames.append(
                ScopeFrame(
                    stmts=[
                        ScopeEnter(stmt_id=-1, origin_ref=u.origin_ref),
                        *current_stmts,
                        ScopeExit(stmt_id=-1, origin_ref=u.origin_ref),
                    ]
                )
            )

    # 2. Header Calculation
    # Sort symbols by ID to be deterministic
    sorted_syms = sorted(
        [(k, v) for k, v in symtab.items() if k in used_ids], key=lambda x: x[0]
    )

    header_consts = [defn.id for _, defn in sorted_syms if defn.kind == "Const"]
    header_vars = [defn.id for _, defn in sorted_syms if defn.kind == "Var"]

    return LinearPlan(
        preamble=preamble,
        header_consts=header_consts,
        header_vars=header_vars,
        frames=frames,
    )
