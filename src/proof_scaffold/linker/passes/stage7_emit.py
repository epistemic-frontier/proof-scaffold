from __future__ import annotations

from ...ir import (
    Axiom,
    ConstDecl,
    DisjointDecl,
    EssentialHyp,
    FloatingHyp,
    Theorem,
    VarDecl,
)
from ..context import LinkContext, UnitInfo
from ..policy import stable_sorted


def _tok_name(info: UnitInfo, tok: object) -> str:
    """Resolve a token (int id or SymbolRef-like) to its string name."""
    if isinstance(tok, int):
        if info.symtab and 0 <= tok < len(info.symtab):
            return str(info.symtab[tok])
        return str(tok)
    name = getattr(tok, "name", None)
    if isinstance(name, str):
        return name
    # Explicitly cast unknowns to str for type-checkers
    return str(tok)


def run(ctx: LinkContext) -> str:
    out: list[str] = []

    # Header: $c / $v
    if ctx.global_consts:
        out.append(f"$c {' '.join(stable_sorted(ctx.global_consts))} $.")
    if ctx.global_vars:
        out.append(f"$v {' '.join(stable_sorted(ctx.global_vars))} $.")

    ordered_units = ctx.ordered_infos or ctx.infos

    for info in ordered_units:
        out.append("${")
        for st in info.stmts:
            if isinstance(st, DisjointDecl):
                toks = " ".join(_tok_name(info, s) for s in st.symbols)
                out.append(f"$d {toks} $.")
            elif isinstance(st, FloatingHyp):
                tc = _tok_name(info, st.typecode)
                var = _tok_name(info, st.var)
                lab = ctx.relabel[(info.unit_id, st.label)]
                out.append(f"{lab} $f {tc} {var} $.")
            elif isinstance(st, EssentialHyp):
                tc = _tok_name(info, st.typecode)
                expr = " ".join(_tok_name(info, t) for t in st.expr)
                lab = ctx.relabel[(info.unit_id, st.label)]
                out.append(f"{lab} $e {tc} {expr} $.")
            elif isinstance(st, Axiom):
                tc = _tok_name(info, st.typecode)
                expr = " ".join(_tok_name(info, t) for t in st.expr)
                lab = ctx.relabel[(info.unit_id, st.label)]
                out.append(f"{lab} $a {tc} {expr} $.")
            elif isinstance(st, Theorem):
                tc = _tok_name(info, st.typecode)
                expr = " ".join(_tok_name(info, t) for t in st.expr)
                lab = ctx.relabel[(info.unit_id, st.label)]
                steps: list[str] = []
                for tk in st.proof_tokens:
                    nm = _tok_name(info, tk)
                    key_local = (info.unit_id, nm)
                    if key_local in ctx.relabel:
                        steps.append(ctx.relabel[key_local])
                        continue
                    owners = ctx.label_owners.get(nm, set())
                    if owners:
                        owner = stable_sorted(owners)[0]
                        mapped = ctx.relabel.get((owner, nm), nm)
                        steps.append(mapped)
                    else:
                        steps.append(nm)
                out.append(f"{lab} $p {tc} {expr} $=")
                out.append("  " + " ".join(steps))
                out.append("$.")
            elif isinstance(st, (ConstDecl, VarDecl)):
                continue
            else:  # ScopeEnter/Exit removed by framing
                continue
        out.append("$}")

    return "\n".join(out) + ("\n" if out else "")
