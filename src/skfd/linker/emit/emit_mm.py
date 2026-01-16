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
    Theorem,
    VarDecl,
)
from skfd.core.source_map import SourceMap, SourceMapEntry
from skfd.core.symbols import SymbolDef, SymbolId
from skfd.linker.passes.stage5_scope import LinearPlan


def emit_mm(
    *,
    symtab: dict[SymbolId, SymbolDef],
    plan: LinearPlan,
    reloc_table: dict[SymbolId, str] | None = None,
) -> tuple[str, SourceMap]:
    """
    Emit a single .mm text stream from a LinearPlan.
    Returns (content, source_map).
    """
    out: list[str] = []
    map_entries: list[SourceMapEntry] = []

    # helper to resolve name
    def get_name(sid: SymbolId) -> str:
        if reloc_table and sid in reloc_table:
            return reloc_table[sid]
        return symtab[sid].local_name

    # 1. Preamble
    for line in plan.preamble:
        out.append(line)

    # 2. Global Header
    const_names = [get_name(sid) for sid in plan.header_consts]
    if const_names:
        out.append(f"$c {' '.join(const_names)} $.")

    var_names = [get_name(sid) for sid in plan.header_vars]
    if var_names:
        out.append(f"$v {' '.join(var_names)} $.")

    # 3. Body Frames
    for frame in plan.frames:
        for st in frame.stmts:
            # ConstDecl/VarDecl handled in header (shouldn't differ here, but check just in case)
            if isinstance(st, ConstDecl | VarDecl):
                continue
            
            # Map the start of this statement to the current line (1-based)
            start_line = len(out) + 1
            
            # Origin tracking: most statements have origin_ref
            if hasattr(st, "origin_ref") and st.origin_ref:
                map_entries.append(SourceMapEntry(line=start_line, origin=st.origin_ref))

            if isinstance(st, Comment):
                out.append(f"$( {st.text} $)")
            elif isinstance(st, FloatingHyp):
                lab = get_name(st.label)
                tc = get_name(st.typecode)
                v = get_name(st.var)
                out.append(f"{lab} $f {tc} {v} $.")
            elif isinstance(st, EssentialHyp):
                lab = get_name(st.label)
                tc = get_name(st.typecode)
                expr = [get_name(t) for t in st.expr]
                out.append(f"{lab} $e {tc} {' '.join(expr)} $.")
            elif isinstance(st, Axiom):
                lab = get_name(st.label)
                tc = get_name(st.typecode)
                expr = [get_name(t) for t in st.expr]
                out.append(f"{lab} $a {tc} {' '.join(expr)} $.")
            elif isinstance(st, Theorem):
                lab = get_name(st.label)
                tc = get_name(st.typecode)
                expr = [get_name(t) for t in st.expr]
                # Reconstruct proof from tokens
                proof = [get_name(t) for t in st.proof]
                out.append(f"{lab} $p {tc} {' '.join(expr)} $=")
                out.append(f"  {' '.join(proof)}")
                out.append("$.")
            elif isinstance(st, DisjointVar):
                vars_ = [get_name(v) for v in st.vars]
                out.append(f"$d {' '.join(vars_)} $.")
            elif isinstance(st, ScopeEnter):
                out.append("${")
            elif isinstance(st, ScopeExit):
                out.append("$}")

    return "\n".join(out) + "\n", SourceMap(entries=map_entries)
