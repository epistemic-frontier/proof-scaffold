from __future__ import annotations

from dataclasses import replace

from ..diag import Diagnostic, LinkerDiagError
from ..ir_lir import ConstDecl, Theorem, VarDecl
from ..symbols import SymbolId
from ..unit import ProofUnitIR


def _raise(unit: ProofUnitIR, stmt_origin_ref: int, code: str, msg: str, **details: object) -> None:
    raise LinkerDiagError(
        Diagnostic(
            error_code=code,
            message=msg,
            primary_origin_ref=stmt_origin_ref,
            related_origin_refs=(unit.origin_ref,),
            origin_chain=(
                {"stage": 1, "unit_id": unit.unit_id},
            ),
            details=dict(details),
        )
    )


def run(*, ctx, units: list[ProofUnitIR]) -> list[ProofUnitIR]:
    symtab = ctx.symtab

    def kind_of(tok: SymbolId) -> str | None:
        d = symtab.get(tok)
        return d.kind if d else None

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
            elif isinstance(st, (ConstDecl, VarDecl)):
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

