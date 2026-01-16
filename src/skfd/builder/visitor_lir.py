# skfd/builder/visitor_lir.py
from __future__ import annotations

from collections.abc import Sequence

from skfd.core.lir import (
    Axiom,
    Comment,
    ConstDecl,
    DisjointVar,
    EssentialHyp,
    FloatingHyp,
    LIRStmt,
    ScopeEnter,
    ScopeExit,
    Theorem,
    VarDecl,
)
from skfd.core.origin import OriginRef
from skfd.core.symbols import SymbolId

from .visitor import BuilderVisitor


class LIRVisitor(BuilderVisitor):
    def __init__(self) -> None:
        self._stmts: list[LIRStmt] = []
        self._next_stmt_id: int = 0

    def _id(self) -> int:
        i = self._next_stmt_id
        self._next_stmt_id += 1
        return i

    def open_scope(self, origin_ref: OriginRef) -> None:
        self._stmts.append(ScopeEnter(self._id(), origin_ref))

    def close_scope(self, origin_ref: OriginRef) -> None:
        self._stmts.append(ScopeExit(self._id(), origin_ref))

    def comment(self, text: str, origin_ref: OriginRef) -> None:
        self._stmts.append(Comment(self._id(), origin_ref, text))

    def const_decl(
        self, symbols: Sequence[str], ids: Sequence[SymbolId], origin_ref: OriginRef
    ) -> None:
        self._stmts.append(ConstDecl(self._id(), origin_ref, list(ids)))

    def var_decl(
        self, symbols: Sequence[str], ids: Sequence[SymbolId], origin_ref: OriginRef
    ) -> None:
        self._stmts.append(VarDecl(self._id(), origin_ref, list(ids)))

    def floating_hyp(
        self,
        label_s: str,
        typecode_s: str,
        var_s: str,
        label_id: SymbolId,
        typecode_id: SymbolId,
        var_id: SymbolId,
        origin_ref: OriginRef,
    ) -> None:
        self._stmts.append(
            FloatingHyp(self._id(), origin_ref, label_id, typecode_id, var_id)
        )

    def essential_hyp(
        self,
        label_s: str,
        typecode_s: str,
        expr_s: Sequence[str],
        label_id: SymbolId,
        typecode_id: SymbolId,
        expr_id: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None:
        self._stmts.append(
            EssentialHyp(self._id(), origin_ref, label_id, typecode_id, list(expr_id))
        )

    def axiom(
        self,
        label_s: str,
        typecode_s: str,
        expr_s: Sequence[str],
        label_id: SymbolId,
        typecode_id: SymbolId,
        expr_id: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None:
        self._stmts.append(
            Axiom(self._id(), origin_ref, label_id, typecode_id, list(expr_id))
        )

    def theorem(
        self,
        label_s: str,
        typecode_s: str,
        expr_s: Sequence[str],
        proof_s: Sequence[str],
        label_id: SymbolId,
        typecode_id: SymbolId,
        expr_id: Sequence[SymbolId],
        proof_id: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None:
        self._stmts.append(
            Theorem(
                self._id(),
                origin_ref,
                label_id,
                typecode_id,
                list(expr_id),
                list(proof_id),
            )
        )

    def disjoint_var(
        self,
        vars_s: Sequence[str],
        vars_id: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None:
        self._stmts.append(DisjointVar(self._id(), origin_ref, list(vars_id)))

    def lir(self) -> list[LIRStmt]:
        return list(self._stmts)
