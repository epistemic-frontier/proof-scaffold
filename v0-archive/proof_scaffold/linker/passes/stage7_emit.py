from __future__ import annotations

from proof_scaffold.ir import (
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


def _tok_name(info: UnitInfo, tok: int) -> str:
    """Resolve a token id to its string name."""
    if info.symtab and 0 <= tok < len(info.symtab):
        return str(info.symtab[tok])
    return str(tok)


def run(ctx: LinkContext) -> str:
    out: list[str] = []

    # Reset debug slice buffers for a deterministic build.
    ctx.proof_tokens = []
    ctx.theorem_to_span = {}
    ctx.emitted_step_to_step_id = {}

    # Header: $c / $v
    if ctx.global_consts:
        out.append(f"$c {' '.join(stable_sorted(ctx.global_consts))} $.")
    if ctx.global_vars:
        out.append(f"$v {' '.join(stable_sorted(ctx.global_vars))} $.")

    plan = ctx.linear_plan
    if plan is None:
        raise ValueError("Stage7 requires ctx.linear_plan (Stage5) to be present")

    info_by_unit: dict[str, UnitInfo] = {
        i.unit_id: i for i in (ctx.ordered_infos or ctx.infos)
    }

    # Body: per-frame emission
    for frame in plan.frames:
        info = info_by_unit[frame.unit_id]
        out.append("${")
        for fs in frame.stmts:
            st = fs.stmt
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
                step_ids: list[int] = []
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

                # Align step_ids with relocated proof token list.
                # When proof_step_ids is present, it must have the same length.
                if st.proof_step_ids:
                    if len(st.proof_step_ids) != len(st.proof_tokens):
                        raise ValueError(
                            f"proof_step_ids length mismatch for theorem {info.unit_id}:{st.label}"
                        )
                    step_ids = list(st.proof_step_ids)
                else:
                    # Fallback: if generator didn't provide step ids, use 0.
                    step_ids = [0 for _ in st.proof_tokens]

                # Record span in the global linear proof token stream.
                start = len(ctx.proof_tokens)
                ctx.proof_tokens.extend(steps)
                end = len(ctx.proof_tokens)
                ctx.theorem_to_span[(info.unit_id, st.label)] = (start, end)

                # Path A sidecar: emitted_step_index (1-based) -> step_id
                # emitted_step_index aligns with the global linear proof token stream.
                for i, sid in enumerate(step_ids, start=start + 1):
                    ctx.emitted_step_to_step_id[i] = sid

                out.append(f"{lab} $p {tc} {expr} $=")
                out.append("  " + " ".join(steps))
                out.append("$.")
            elif isinstance(st, (ConstDecl, VarDecl)):
                continue
            else:  # ScopeEnter/Exit handled by framing (outer ${/$}) or unit local scope
                continue
        out.append("$}")

    return "\n".join(out) + ("\n" if out else "")
