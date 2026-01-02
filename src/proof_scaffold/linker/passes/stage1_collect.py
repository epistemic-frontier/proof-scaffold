from __future__ import annotations

from ...ir import (
    Axiom,
    ConstDecl,
    DisjointDecl,
    EssentialHyp,
    FloatingHyp,
    ScopeEnter,
    ScopeExit,
    SymbolRef,
    Theorem,
    VarDecl,
)
from ..context import LinkContext, UnitInfo
from ..diag_helpers import raise_link_error


def _ensure_symref(cond: bool, msg: str, primary, unit_id: str, *, chain_extra: tuple[str, ...] = ()) -> None:
    if not cond:
        raise_link_error(
            "E_RAW_TOKEN_FORBIDDEN",
            msg,
            primary=primary,
            chain=("Stage1", f"unit={unit_id}") + chain_extra,
        )


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
                    _ensure_symref(isinstance(s, SymbolRef), "ConstDecl contains non-SymbolRef token", st.origin, u.unit_id)
                    global_consts.add(s.name)
            elif isinstance(st, VarDecl):
                for s in st.symbols:
                    _ensure_symref(isinstance(s, SymbolRef), "VarDecl contains non-SymbolRef token", st.origin, u.unit_id)
                    global_vars.add(s.name)
            elif isinstance(st, FloatingHyp):
                _ensure_symref(isinstance(st.typecode, SymbolRef), "FloatingHyp.typecode must be SymbolRef", st.origin, u.unit_id)
                _ensure_symref(isinstance(st.var, SymbolRef), "FloatingHyp.var must be SymbolRef", st.origin, u.unit_id)
                lab = st.label
                label_owners.setdefault(lab, set()).add(u.unit_id)
                label_kind_by_unit[(u.unit_id, lab)] = "$f"
                labels[lab] = "$f"
                label_origin[lab] = st.origin
                v = st.var.name
                f_label_of_var[v] = lab
                if v not in f_order:
                    f_order.append(v)
            elif isinstance(st, EssentialHyp):
                _ensure_symref(isinstance(st.typecode, SymbolRef), "EssentialHyp.typecode must be SymbolRef", st.origin, u.unit_id)
                for t in st.expr:
                    _ensure_symref(isinstance(t, SymbolRef), "EssentialHyp.expr contains non-SymbolRef token", st.origin, u.unit_id)
                lab = st.label
                label_owners.setdefault(lab, set()).add(u.unit_id)
                label_kind_by_unit[(u.unit_id, lab)] = "$e"
                labels[lab] = "$e"
                label_origin[lab] = st.origin
            elif isinstance(st, Axiom):
                _ensure_symref(isinstance(st.typecode, SymbolRef), "Axiom.typecode must be SymbolRef", st.origin, u.unit_id)
                for t in st.expr:
                    _ensure_symref(isinstance(t, SymbolRef), "Axiom.expr contains non-SymbolRef token", st.origin, u.unit_id)
                lab = st.label
                label_owners.setdefault(lab, set()).add(u.unit_id)
                label_kind_by_unit[(u.unit_id, lab)] = "$a"
                labels[lab] = "$a"
                label_origin[lab] = st.origin
                assertion_stmt[lab] = [st.typecode.name] + [t.name for t in st.expr]
            elif isinstance(st, Theorem):
                _ensure_symref(isinstance(st.typecode, SymbolRef), "Theorem.typecode must be SymbolRef", st.origin, u.unit_id, chain_extra=(f"stmt={st.label}",))
                for t in st.expr:
                    _ensure_symref(isinstance(t, SymbolRef), "Theorem.expr contains non-SymbolRef token", st.origin, u.unit_id, chain_extra=(f"stmt={st.label}",))
                lab = st.label
                label_owners.setdefault(lab, set()).add(u.unit_id)
                label_kind_by_unit[(u.unit_id, lab)] = "$p"
                labels[lab] = "$p"
                label_origin[lab] = st.origin
                assertion_stmt[lab] = [st.typecode.name] + [t.name for t in st.expr]
                for tk in st.proof_tokens:
                    if not isinstance(tk, SymbolRef):
                        raise_link_error(
                            "E_RAW_TOKEN_FORBIDDEN",
                            "proof token is not a SymbolRef (raw string token forbidden)",
                            primary=st.origin,
                            chain=("Stage1", f"unit={u.unit_id}", f"stmt={lab}"),
                        )
                    step = tk.name
                    if any(label_kind_by_unit.get((own, step)) in ("$a", "$p") for own in label_owners.get(step, set())):
                        uses_assertions.add(step)
            elif isinstance(st, (ScopeEnter, ScopeExit, DisjointDecl)):
                pass
            else:  # pragma: no cover
                from ..errors import LinkerError
                raise LinkerError(f"unknown LIR stmt: {type(st)}")

        exports_set: set[str] | None
        if u.exports is None:
            exports_set = None
        else:
            exports_set = set(u.exports)

        infos.append(UnitInfo(
            unit_id=u.unit_id,
            stmts=list(u.lir),
            labels=labels,
            label_origin=label_origin,
            uses_assertions=uses_assertions,
            f_label_of_var=f_label_of_var,
            f_order=f_order,
            assertion_stmt=assertion_stmt,
            exports=exports_set,
            unit_origin=u.origin,
        ))

    # Note: We do NOT treat same label names across different units as collisions.
    # Relocation will namespace them deterministically; collision only makes sense when
    # the same (origin, local_name, kind) pair appears twice, which is not represented here.

    ctx.infos = infos
    ctx.global_consts = global_consts
    ctx.global_vars = global_vars
    ctx.label_owners = label_owners
    ctx.label_kind_by_unit = label_kind_by_unit
    ctx.exports_by_unit = {i.unit_id: i.exports for i in infos}
