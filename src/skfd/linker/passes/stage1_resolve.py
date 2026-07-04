# skfd/linker/passes/stage1_resolve.py
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import replace

from skfd.core.diag import Diagnostic, LinkerDiagError
from skfd.core.lir import Axiom, ConstDecl, EssentialHyp, FloatingHyp, Theorem, VarDecl
from skfd.core.symbols import SymbolId
from skfd.core.unit import ProofUnitIR, UnitKind


@dataclass(frozen=True)
class LabelDef:
    owner_unit_id: str
    owner_kind: UnitKind
    stmt_class: str


def _raise(
    unit: ProofUnitIR, stmt_origin_ref: int, code: str, msg: str, **details: object
) -> None:
    raise LinkerDiagError(
        Diagnostic(
            error_code=code,
            message=msg,
            primary_origin_ref=stmt_origin_ref,
            related_origin_refs=(unit.origin_ref,),
            origin_chain=({"stage": 1, "unit_id": unit.unit_id},),
            details=dict(details),
        )
    )


def run(
    *, ctx, units: list[ProofUnitIR], conformance_level: int = 0
) -> list[ProofUnitIR]:
    symtab = ctx.symtab

    def kind_of(tok: SymbolId) -> str | None:
        d = symtab.get(tok)
        return d.kind if d else None

    foundations = [u.unit_id for u in units if u.kind == "foundation"]
    if len(foundations) > 1:
        _raise(
            units[0],
            units[0].origin_ref,
            "E_MULTIPLE_FOUNDATIONS",
            "linked closure contains multiple foundation units",
            foundation_unit_ids=sorted(foundations),
        )

    # 1. Build Index: Label SymbolId -> defining unit and statement class.
    # Const/Var definitions are globally interned. Access control below applies
    # to proof labels because those can be assertions or local hypotheses.
    label_defs: dict[SymbolId, LabelDef] = {}
    unit_exports: dict[str, set[SymbolId]] = {}

    for u in units:
        uid = u.unit_id
        unit_exports[uid] = set(u.exports)

        for st in u.lir_stmts:
            if isinstance(st, Axiom):
                stmt_class = "axiom"
            elif isinstance(st, Theorem):
                stmt_class = "theorem"
            elif isinstance(st, FloatingHyp):
                stmt_class = "floating"
            elif isinstance(st, EssentialHyp):
                stmt_class = "essential"
            else:
                continue

            existing = label_defs.get(st.label)
            if existing is not None:
                _raise(
                    u,
                    st.origin_ref,
                    "E_DUPLICATE_LABEL_DEF",
                    "label is defined by multiple statements",
                    symbol_id=st.label,
                    first_owner_unit_id=existing.owner_unit_id,
                    second_owner_unit_id=uid,
                    first_stmt_class=existing.stmt_class,
                    second_stmt_class=stmt_class,
                )

            label_defs[st.label] = LabelDef(
                owner_unit_id=uid,
                owner_kind=u.kind,
                stmt_class=stmt_class,
            )

    def _check_math_tokens(
        unit: ProofUnitIR,
        stmt_origin_ref: int,
        expr: Sequence[SymbolId],
        *,
        field: str,
    ) -> None:
        for t in expr:
            k = kind_of(t)
            if k not in ("Const", "Var"):
                _raise(
                    unit,
                    stmt_origin_ref,
                    "E_TOKEN_KIND",
                    "expr token must be Const/Var",
                    tok_id=t,
                    tok_kind=k,
                    field=field,
                )

    def _check_cross_unit_proof_token(
        unit: ProofUnitIR,
        stmt: Theorem,
        label: SymbolId,
        label_def: LabelDef,
    ) -> None:
        if label_def.owner_unit_id == unit.unit_id:
            return

        owner_exports = unit_exports.get(label_def.owner_unit_id, set())

        if label_def.stmt_class == "floating":
            if label_def.owner_kind == "foundation" and label in owner_exports:
                return
            code = "E_SYMBOL_NOT_EXPORTED"
            message = (
                "foundation floating hypothesis is not exported"
                if label_def.owner_kind == "foundation"
                else "ordinary package floating hypothesis cannot be used cross-unit"
            )
            if label_def.owner_kind != "foundation":
                code = "E_HYPOTHESIS_LEAKAGE"
            _raise(
                unit,
                stmt.origin_ref,
                code,
                message,
                symbol_id=label,
                owner_unit_id=label_def.owner_unit_id,
                owner_kind=label_def.owner_kind,
                export_class="foundation_hypothesis"
                if label_def.owner_kind == "foundation"
                else "internal_hypothesis",
                stmt_class=label_def.stmt_class,
            )

        if label_def.stmt_class == "essential":
            _raise(
                unit,
                stmt.origin_ref,
                "E_HYPOTHESIS_LEAKAGE",
                "essential hypothesis cannot be used cross-unit",
                symbol_id=label,
                owner_unit_id=label_def.owner_unit_id,
                owner_kind=label_def.owner_kind,
                export_class="internal_hypothesis",
                stmt_class=label_def.stmt_class,
            )

        if label_def.stmt_class in {"axiom", "theorem"}:
            if label in owner_exports:
                return
            _raise(
                unit,
                stmt.origin_ref,
                "E_SYMBOL_NOT_EXPORTED",
                f"Symbol {label} is not exported by unit {label_def.owner_unit_id}",
                symbol_id=label,
                owner_unit_id=label_def.owner_unit_id,
                owner_kind=label_def.owner_kind,
                export_class="assertion",
                stmt_class=label_def.stmt_class,
            )

        _raise(
            unit,
            stmt.origin_ref,
            "E_ACCESS_CONTROL",
            "unsupported cross-unit proof reference",
            symbol_id=label,
            owner_unit_id=label_def.owner_unit_id,
            owner_kind=label_def.owner_kind,
            stmt_class=label_def.stmt_class,
        )

    for u in units:
        for st in u.lir_stmts:
            # Reserved token name check (on defs) lives in Stage0 in this bootstrap.
            if isinstance(st, FloatingHyp):
                if kind_of(st.typecode) != "Const":
                    _raise(
                        u,
                        st.origin_ref,
                        "E_TOKEN_KIND",
                        "floating hypothesis typecode must be Const",
                        tok_id=st.typecode,
                        tok_kind=kind_of(st.typecode),
                        field="typecode",
                    )
                if kind_of(st.var) != "Var":
                    _raise(
                        u,
                        st.origin_ref,
                        "E_TOKEN_KIND",
                        "floating hypothesis variable must be Var",
                        tok_id=st.var,
                        tok_kind=kind_of(st.var),
                        field="var",
                    )

            elif isinstance(st, EssentialHyp):
                if kind_of(st.typecode) != "Const":
                    _raise(
                        u,
                        st.origin_ref,
                        "E_TOKEN_KIND",
                        "essential hypothesis typecode must be Const",
                        tok_id=st.typecode,
                        tok_kind=kind_of(st.typecode),
                        field="typecode",
                    )
                _check_math_tokens(u, st.origin_ref, st.expr, field="expr")

            elif isinstance(st, Axiom):
                if kind_of(st.typecode) != "Const":
                    _raise(
                        u,
                        st.origin_ref,
                        "E_TOKEN_KIND",
                        "axiom typecode must be Const",
                        tok_id=st.typecode,
                        tok_kind=kind_of(st.typecode),
                        field="typecode",
                    )
                _check_math_tokens(u, st.origin_ref, st.expr, field="expr")

            elif isinstance(st, Theorem):
                if kind_of(st.typecode) != "Const":
                    _raise(
                        u,
                        st.origin_ref,
                        "E_TOKEN_KIND",
                        "theorem typecode must be Const",
                        tok_id=st.typecode,
                        tok_kind=kind_of(st.typecode),
                        field="typecode",
                    )
                _check_math_tokens(u, st.origin_ref, st.expr, field="expr")

                for t in st.proof:
                    k = kind_of(t)
                    if k != "Label":
                        _raise(
                            u,
                            st.origin_ref,
                            "E_PROOF_TOKEN_KIND",
                            "proof token must be Label",
                            tok_id=t,
                            tok_kind=k,
                        )

                    # Access Control Check (Level 1+)
                    if conformance_level >= 1:
                        label_def = label_defs.get(t)
                        if label_def is None:
                            _raise(
                                u,
                                st.origin_ref,
                                "E_LABEL_NOT_DEFINED",
                                "proof label is not defined in the linked closure",
                                symbol_id=t,
                            )
                        assert label_def is not None
                        _check_cross_unit_proof_token(u, st, t, label_def)

            elif isinstance(st, ConstDecl | VarDecl):
                # tokens already SymbolIds; just ensure exist and kind matches.
                expected = "Const" if isinstance(st, ConstDecl) else "Var"
                for t in st.tokens:
                    k = kind_of(t)
                    if k != expected:
                        _raise(
                            u,
                            st.origin_ref,
                            "E_DECL_KIND",
                            "declaration token kind mismatch",
                            tok_id=t,
                            expected=expected,
                            got=k,
                        )

    return [replace(u) for u in units]
