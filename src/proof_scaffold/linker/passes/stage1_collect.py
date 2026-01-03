from __future__ import annotations

from ...ir import (
    Axiom,
    ConstDecl,
    DisjointDecl,
    EssentialHyp,
    FloatingHyp,
    ScopeEnter,
    ScopeExit,
    Theorem,
    VarDecl,
)
from ..context import LinkContext, UnitInfo, UseEdgeProvenance
from ..diag_helpers import raise_link_error
from ..policy import stable_sorted


def _is_token_allowed(tok: object) -> bool:
    return isinstance(tok, int)


def _tok_name(u, tok: object) -> str:
    if isinstance(tok, int):
        # tolerate empty symtab in compat: unknown id -> placeholder string
        return u.symtab[tok] if u.symtab and 0 <= tok < len(u.symtab) else str(tok)
    # strings should not appear here; return as-is for diagnostics if they do
    return str(tok)


def run(ctx: LinkContext) -> None:
    infos: list[UnitInfo] = []
    global_consts: set[str] = set()
    global_vars: set[str] = set()
    label_owners: dict[str, set[str]] = {}
    label_kind_by_unit: dict[tuple[str, str], str] = {}

    for u in ctx.units:
        labels: dict[str, str] = {}
        from ...ir import Origin as _Origin
        label_origin: dict[str, _Origin | None] = {}
        uses_assertions: set[str] = set()
        uses_prov: dict[str, UseEdgeProvenance] = {}
        f_label_of_var: dict[str, str] = {}
        f_order: list[str] = []
        assertion_stmt: dict[str, list[str]] = {}

        # Scope balance guard
        depth = 0
        for st in u.lir:
            if isinstance(st, ScopeEnter):
                depth += 1
            elif isinstance(st, ScopeExit):
                depth -= 1
                if depth < 0:
                    raise_link_error(
                        "E_SCOPE_IMBALANCE",
                        f"scope imbalance detected in unit {u.unit_id}: extra ScopeExit",
                        primary=u.origin,
                        chain=("Stage1", f"unit={u.unit_id}"),
                    )
        if depth != 0:
            raise_link_error(
                "E_SCOPE_IMBALANCE",
                f"scope imbalance detected in unit {u.unit_id}: unmatched ScopeEnter/ScopeExit",
                primary=u.origin,
                chain=("Stage1", f"unit={u.unit_id}"),
            )

        for st in u.lir:
            if isinstance(st, ConstDecl):
                for s in st.symbols:
                    if not _is_token_allowed(s):
                        raise_link_error(
                            "E_RAW_TOKEN_FORBIDDEN",
                            "ConstDecl contains non-int token",
                            primary=st.origin,
                            chain=("Stage1", f"unit={u.unit_id}"),
                        )
                    global_consts.add(_tok_name(u, s))
            elif isinstance(st, VarDecl):
                for s in st.symbols:
                    if not _is_token_allowed(s):
                        raise_link_error(
                            "E_RAW_TOKEN_FORBIDDEN",
                            "VarDecl contains non-int token",
                            primary=st.origin,
                            chain=("Stage1", f"unit={u.unit_id}"),
                        )
                    global_vars.add(_tok_name(u, s))
            elif isinstance(st, FloatingHyp):
                if not _is_token_allowed(st.typecode):
                    raise_link_error(
                        "E_RAW_TOKEN_FORBIDDEN",
                        "FloatingHyp.typecode must be int",
                        primary=st.origin,
                        chain=("Stage1", f"unit={u.unit_id}"),
                    )
                if not _is_token_allowed(st.var):
                    raise_link_error(
                        "E_RAW_TOKEN_FORBIDDEN",
                        "FloatingHyp.var must be int",
                        primary=st.origin,
                        chain=("Stage1", f"unit={u.unit_id}"),
                    )
                lab = st.label
                label_owners.setdefault(lab, set()).add(u.unit_id)
                label_kind_by_unit[(u.unit_id, lab)] = "$f"
                labels[lab] = "$f"
                label_origin[lab] = st.origin
                v = _tok_name(u, st.var)
                f_label_of_var[v] = lab
                if v not in f_order:
                    f_order.append(v)
            elif isinstance(st, EssentialHyp):
                if not _is_token_allowed(st.typecode):
                    raise_link_error(
                        "E_RAW_TOKEN_FORBIDDEN",
                        "EssentialHyp.typecode must be int",
                        primary=st.origin,
                        chain=("Stage1", f"unit={u.unit_id}"),
                    )
                for t in st.expr:
                    if not _is_token_allowed(t):
                        raise_link_error(
                            "E_RAW_TOKEN_FORBIDDEN",
                            "EssentialHyp.expr contains non-int token",
                            primary=st.origin,
                            chain=("Stage1", f"unit={u.unit_id}"),
                        )
                lab = st.label
                label_owners.setdefault(lab, set()).add(u.unit_id)
                label_kind_by_unit[(u.unit_id, lab)] = "$e"
                labels[lab] = "$e"
                label_origin[lab] = st.origin
            elif isinstance(st, Axiom):
                if not _is_token_allowed(st.typecode):
                    raise_link_error(
                        "E_RAW_TOKEN_FORBIDDEN",
                        "Axiom.typecode must be int",
                        primary=st.origin,
                        chain=("Stage1", f"unit={u.unit_id}"),
                    )
                for t in st.expr:
                    if not _is_token_allowed(t):
                        raise_link_error(
                            "E_RAW_TOKEN_FORBIDDEN",
                            "Axiom.expr contains non-int token",
                            primary=st.origin,
                            chain=("Stage1", f"unit={u.unit_id}"),
                        )
                lab = st.label
                label_owners.setdefault(lab, set()).add(u.unit_id)
                label_kind_by_unit[(u.unit_id, lab)] = "$a"
                labels[lab] = "$a"
                label_origin[lab] = st.origin
                assertion_stmt[lab] = [_tok_name(u, st.typecode)] + [_tok_name(u, t) for t in st.expr]
            elif isinstance(st, Theorem):
                if not _is_token_allowed(st.typecode):
                    raise_link_error(
                        "E_RAW_TOKEN_FORBIDDEN",
                        "Theorem.typecode must be int",
                        primary=st.origin,
                        chain=("Stage1", f"unit={u.unit_id}", f"stmt={st.label}"),
                    )
                for t in st.expr:
                    if not _is_token_allowed(t):
                        raise_link_error(
                            "E_RAW_TOKEN_FORBIDDEN",
                            "Theorem.expr contains non-int token",
                            primary=st.origin,
                            chain=("Stage1", f"unit={u.unit_id}", f"stmt={st.label}"),
                        )
                lab = st.label
                label_owners.setdefault(lab, set()).add(u.unit_id)
                label_kind_by_unit[(u.unit_id, lab)] = "$p"
                labels[lab] = "$p"
                label_origin[lab] = st.origin
                assertion_stmt[lab] = [_tok_name(u, st.typecode)] + [_tok_name(u, t) for t in st.expr]
                for tk in st.proof_tokens:
                    if not _is_token_allowed(tk):
                        raise_link_error(
                            "E_RAW_TOKEN_FORBIDDEN",
                            "proof token is not an int (raw token forbidden)",
                            primary=st.origin,
                            chain=("Stage1", f"unit={u.unit_id}", f"stmt={lab}"),
                        )
                    step = _tok_name(u, tk)
                    owners = label_owners.get(step, set())
                    if any(label_kind_by_unit.get((own, step)) in ("$a", "$p") for own in owners):
                        uses_assertions.add(step)
                        # record first provenance (stable enough for MVP)
                        if step not in uses_prov:
                            uses_prov[step] = UseEdgeProvenance(
                                used_label=step,
                                ref_origin=st.origin,
                                ref_stmt_label=lab,
                                proof_step_idx=None,
                            )
            elif isinstance(st, (ScopeEnter, ScopeExit, DisjointDecl)):
                pass
            else:  # pragma: no cover
                from ..errors import LinkerError
                raise LinkerError(f"unknown LIR stmt: {type(st)}")

        # NOTE: If exports is not provided, default policy is "$a/$p are exported".
        # Some unit tests expect an omitted exports list to behave as "export all".
        exports_set: set[str] | None
        if u.exports is None:
            exports_set = set(stable_sorted([lab for (uid, lab), k in label_kind_by_unit.items() if uid == u.unit_id and k in ("$a", "$p")]))
        else:
            exports_set = set(u.exports)

        infos.append(UnitInfo(
            unit_id=u.unit_id,
            stmts=list(u.lir),
            symtab=u.symtab,
            labels=labels,
            label_origin=label_origin,
            uses_assertions=tuple(stable_sorted(uses_assertions)),
            f_label_of_var=f_label_of_var,
            f_order=f_order,
            assertion_stmt=assertion_stmt,
            exports=exports_set,
            unit_origin=u.origin,
            uses_provenance=uses_prov,
        ))

    ctx.infos = infos
    ctx.global_consts = global_consts
    ctx.global_vars = global_vars
    ctx.label_owners = label_owners
    ctx.label_kind_by_unit = label_kind_by_unit
    ctx.exports_by_unit = {i.unit_id: i.exports for i in infos}
