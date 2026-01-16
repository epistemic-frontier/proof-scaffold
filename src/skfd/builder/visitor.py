# skfd/builder/visitor.py
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from skfd.core.origin import OriginRef
from skfd.core.symbols import SymbolId


class BuilderVisitor(ABC):
    """
    Abstract Visitor for the Metamath Builder DSL.
    Allows multiple backends (LIR, Text, etc.) to hook into the builder.
    """

    @abstractmethod
    def open_scope(self, origin_ref: OriginRef) -> None: ...

    @abstractmethod
    def close_scope(self, origin_ref: OriginRef) -> None: ...

    @abstractmethod
    def comment(self, text: str, origin_ref: OriginRef) -> None: ...

    @abstractmethod
    def const_decl(
        self, symbols: Sequence[str], ids: Sequence[SymbolId], origin_ref: OriginRef
    ) -> None: ...

    @abstractmethod
    def var_decl(
        self, symbols: Sequence[str], ids: Sequence[SymbolId], origin_ref: OriginRef
    ) -> None: ...

    @abstractmethod
    def floating_hyp(
        self,
        label_s: str,
        typecode_s: str,
        var_s: str,
        label_id: SymbolId,
        typecode_id: SymbolId,
        var_id: SymbolId,
        origin_ref: OriginRef,
    ) -> None: ...

    @abstractmethod
    def essential_hyp(
        self,
        label_s: str,
        typecode_s: str,
        expr_s: Sequence[str],
        label_id: SymbolId,
        typecode_id: SymbolId,
        expr_id: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None: ...

    @abstractmethod
    def axiom(
        self,
        label_s: str,
        typecode_s: str,
        expr_s: Sequence[str],
        label_id: SymbolId,
        typecode_id: SymbolId,
        expr_id: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None: ...

    @abstractmethod
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
    ) -> None: ...

    @abstractmethod
    def disjoint_var(
        self,
        vars_s: Sequence[str],
        vars_id: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None: ...
