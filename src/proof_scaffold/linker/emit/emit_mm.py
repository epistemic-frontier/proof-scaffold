from __future__ import annotations

from ..lir import Comment, ConstDecl, FloatingHyp, Theorem, VarDecl
from ..symbols import SymbolDef, SymbolId
from ..unit import ProofUnitIR


def emit_mm(*, symtab: dict[SymbolId, SymbolDef], units: list[ProofUnitIR]) -> str:
    # Two-phase: header ($c/$v) then body.
    consts: list[str] = []
    vars_: list[str] = []
    # Deterministic order by SymbolId.
    for sid in sorted(symtab.keys()):
        sd = symtab[sid]
        if sd.kind == "Const":
            consts.append(sd.local_name)
        elif sd.kind == "Var":
            vars_.append(sd.local_name)

    out: list[str] = []
    if consts:
        out.append(f"$c {' '.join(consts)} $.")
    if vars_:
        out.append(f"$v {' '.join(vars_)} $.")

    for u in units:
        for st in u.lir_stmts:
            if isinstance(st, ConstDecl | VarDecl):
                continue
            if isinstance(st, Comment):
                out.append(f"$( {st.text} $)")
            elif isinstance(st, FloatingHyp):
                lab = symtab[st.label].local_name
                tc = symtab[st.typecode].local_name
                var = symtab[st.var].local_name
                out.append(f"{lab} $f {tc} {var} $.")
            elif isinstance(st, Theorem):
                lab = symtab[st.label].local_name
                expr = " ".join(symtab[t].local_name for t in st.expr)
                proof = " ".join(symtab[t].local_name for t in st.proof)
                out.append(f"{lab} $p {expr} $= {proof} $.")

    return "\n".join(out) + "\n"
