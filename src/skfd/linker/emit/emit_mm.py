# skfd/linker/emit/emit_mm.py
from __future__ import annotations

from skfd.core.lir import (
    Axiom,
    Comment,
    ConstDecl,
    DisjointVar,
    EssentialHyp,
    FloatingHyp,
    ScopeEnter,
    ScopeExit,
    SymbolId,
    Theorem,
    VarDecl,
)
from skfd.core.symbols import SymbolDef
from skfd.core.unit import ProofUnitIR


def emit_mm(*, symtab: dict[SymbolId, SymbolDef], units: list[ProofUnitIR]) -> str:
    """
    Emit a single .mm text stream from resolved units.
    Only emits constants/variables that are referenced in the units.
    """
    out: list[str] = []

    # 1. Collect used symbols from units
    used_ids: set[SymbolId] = set()
    for u in units:
        for st in u.lir_stmts:
            if isinstance(st, ConstDecl):
                used_ids.update(st.tokens)
            elif isinstance(st, VarDecl):
                used_ids.update(st.tokens)
            elif isinstance(st, FloatingHyp):
                used_ids.add(st.label)
                used_ids.add(st.typecode)
                used_ids.add(st.var)
            elif isinstance(st, EssentialHyp):
                used_ids.add(st.label)
                used_ids.add(st.typecode)
                used_ids.update(st.expr)
            elif isinstance(st, Axiom):
                used_ids.add(st.label)
                used_ids.add(st.typecode)
                used_ids.update(st.expr)
            elif isinstance(st, Theorem):
                used_ids.add(st.label)
                used_ids.add(st.typecode)
                used_ids.update(st.expr)
                used_ids.update(st.proof)
            elif isinstance(st, DisjointVar):
                used_ids.update(st.vars)
                
    # 2. Global declarations (filtered)
    # Sort symbols by ID to be deterministic
    sorted_syms = sorted(
        [(k, v) for k, v in symtab.items() if k in used_ids],
        key=lambda x: x[0]
    )
    
    # Emit Constants
    consts = [defn.local_name for _, defn in sorted_syms if defn.kind == "Const"]
    if consts:
        out.append(f"$c {' '.join(consts)} $.")

    # Emit Variables
    vars_ = [defn.local_name for _, defn in sorted_syms if defn.kind == "Var"]
    if vars_:
        out.append(f"$v {' '.join(vars_)} $.")

    # 3. Emit units
    for u in units:
        for st in u.lir_stmts:
            if isinstance(st, ConstDecl | VarDecl):
                # Already handled globally
                continue
            
            if isinstance(st, Comment):
                out.append(f"$( {st.text} $)")
            elif isinstance(st, FloatingHyp):
                lab = symtab[st.label].local_name
                tc = symtab[st.typecode].local_name
                v = symtab[st.var].local_name
                out.append(f"{lab} $f {tc} {v} $.")
            elif isinstance(st, EssentialHyp):
                lab = symtab[st.label].local_name
                tc = symtab[st.typecode].local_name
                expr = [symtab[t].local_name for t in st.expr]
                out.append(f"{lab} $e {tc} {' '.join(expr)} $.")
            elif isinstance(st, Axiom):
                lab = symtab[st.label].local_name
                tc = symtab[st.typecode].local_name
                expr = [symtab[t].local_name for t in st.expr]
                out.append(f"{lab} $a {tc} {' '.join(expr)} $.")
            elif isinstance(st, Theorem):
                lab = symtab[st.label].local_name
                tc = symtab[st.typecode].local_name
                expr = [symtab[t].local_name for t in st.expr]
                # Reconstruct proof from tokens
                proof = [symtab[t].local_name for t in st.proof]
                out.append(f"{lab} $p {tc} {' '.join(expr)} $=")
                out.append(f"  {' '.join(proof)}")
                out.append("$.")
            elif isinstance(st, DisjointVar):
                vars_ = [symtab[v].local_name for v in st.vars]
                out.append(f"$d {' '.join(vars_)} $.")
            elif isinstance(st, ScopeEnter):
                out.append("${")
            elif isinstance(st, ScopeExit):
                out.append("$}")
                
    return "\n".join(out) + "\n"
