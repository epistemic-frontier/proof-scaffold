# src/skfd/builder/emitter_lir.py
from __future__ import annotations

from collections.abc import Sequence

from skfd.core.lir import (
    LIRStmt,
    ConstDecl,
    VarDecl,
    FloatingHyp,
    EssentialHyp,
    Axiom,
    Theorem,
    Comment,
    ScopeEnter,
    ScopeExit,
)
from skfd.core.origin import OriginRef
from skfd.core.symbols import SymbolId


class LIREmitter:
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

    def const_decl(self, symbols: Sequence[SymbolId], origin_ref: OriginRef) -> None:
        self._stmts.append(ConstDecl(self._id(), origin_ref, list(symbols)))

    def var_decl(self, symbols: Sequence[SymbolId], origin_ref: OriginRef) -> None:
        self._stmts.append(VarDecl(self._id(), origin_ref, list(symbols)))

    def floating_hyp(
        self, label: SymbolId, typecode: SymbolId, var: SymbolId, origin_ref: OriginRef
    ) -> None:
        self._stmts.append(FloatingHyp(self._id(), origin_ref, label, typecode, var))

    def essential_hyp(
        self,
        label: SymbolId,
        expr: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None:
        self._stmts.append(EssentialHyp(self._id(), origin_ref, label, list(expr)))

    def axiom(
        self,
        label: SymbolId,
        expr: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None:
        self._stmts.append(Axiom(self._id(), origin_ref, label, list(expr)))

    def theorem(
        self,
        label: SymbolId,
        expr: Sequence[SymbolId],
        proof: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None:
        self._stmts.append(
            Theorem(self._id(), origin_ref, label, list(expr), list(proof))
        )

    def lir(self) -> list[LIRStmt]:
        return list(self._stmts)
