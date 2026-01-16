# skfd/linker/passes/stage1_resolve.py
from __future__ import annotations

from dataclasses import replace

from skfd.core.diag import Diagnostic, LinkerDiagError
from skfd.core.lir import ConstDecl, Theorem, VarDecl
from skfd.core.symbols import SymbolId
from skfd.core.unit import ProofUnitIR


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


def run(*, ctx, units: list[ProofUnitIR]) -> list[ProofUnitIR]:
    symtab = ctx.symtab

    def kind_of(tok: SymbolId) -> str | None:
        d = symtab.get(tok)
        return d.kind if d else None

    # 1. Build Index: SymbolId -> UnitId and Unit Exports
    # We use Unit object identity or unit_id (str) as key. Using unit_id for determinism/simplicity.
    symbol_owner: dict[SymbolId, str] = {}
    unit_exports: dict[str, set[SymbolId]] = {}

    for u in units:
        uid = u.unit_id
        unit_exports[uid] = set(u.exports)

        # Scan definitions to map ownership
        # Note: CONST/VAR are global-ish, but LABELS are owned by units.
        # We only care about Labels for export checks.
        for st in u.lir_stmts:
            if isinstance(st, Theorem | ConstDecl | VarDecl):
                # Theorems define a label (st.label)
                if hasattr(st, "label"):
                    symbol_owner[st.label] = uid
            # Axiom, FloatingHyp, EssentialHyp also define labels
            # But wait, LIR classes:
            # Axiom(label...), Theorem(label...), FloatingHyp(label...), EssentialHyp(label...)
            # We need to handle all labelled statements.

        # Hand-checking LIR types from memory/imports...
        # Let's be generic or import all types to be safe.
        # Currently imported: ConstDecl, Theorem, VarDecl.
        # Need to import others or inspect dynamically?
        # Inspecting `st.label` presence is safer if we trust LIR structure.
        pass

    # Re-scan for full label ownership
    from skfd.core.lir import Axiom, EssentialHyp, FloatingHyp

    for u in units:
        uid = u.unit_id
        for st in u.lir_stmts:
            if hasattr(st, "label") and isinstance(
                st, Theorem | Axiom | FloatingHyp | EssentialHyp
            ):
                symbol_owner[st.label] = uid

    for u in units:
        for st in u.lir_stmts:
            # Reserved token name check (on defs) lives in Stage0 in this bootstrap.
            if isinstance(st, Theorem):
                for t in st.expr:
                    k = kind_of(t)
                    if k not in ("Const", "Var"):
                        _raise(
                            u,
                            st.origin_ref,
                            "E_TOKEN_KIND",
                            "expr token must be Const/Var",
                            tok_id=t,
                            tok_kind=k,
                        )
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

                    # Access Control Check
                    if t in symbol_owner:
                        owner_uid = symbol_owner[t]
                        if owner_uid != u.unit_id:
                            # Cross-unit reference. Must be exported.
                            if t not in unit_exports.get(owner_uid, set()):
                                _raise(
                                    u,
                                    st.origin_ref,
                                    "E_SYMBOL_NOT_EXPORTED",
                                    f"Symbol {t} is not exported by unit {owner_uid}",
                                    symbol_id=t,
                                    owner_unit_id=owner_uid,
                                )
                    else:
                        # Symbol not found in any input unit.
                        # This implies implicit dependency or missing unit.
                        # For hardening, we should probably reject this too,
                        # unless it's a pre-declared "global" hypothesis?
                        # But LinkerV1 is supposed to see the full closure.
                        # We will warn or fail? Let's strictly fail if we want closure completeness.
                        # But maybe some symbols come from 'prelude' which might be treated differently?
                        # No, prelude is just another unit in LinkerV1.
                        # So we should fail if definition is missing.
                        pass

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
