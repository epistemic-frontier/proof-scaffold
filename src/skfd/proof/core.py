from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, TypeAlias

from skfd.authoring.dsl import Expr
from skfd.authoring.formula import Wff
from skfd.authoring.typing import HypothesisAny
from skfd.core.symbols import SymbolInterner

Tactic: TypeAlias = Any
TacticRegistry: TypeAlias = Mapping[str, Tactic]


class SystemCore(Protocol):
    @property
    def interner(self) -> SymbolInterner:
        ...

    def compile(self, expr: Expr, *, ctx: str = "compile") -> Wff:
        ...

    def compile_axioms(self) -> Mapping[str, Wff]:
        ...

    def apply(self, rule: str, hyps: Sequence[HypothesisAny], *, ctx: str) -> Wff:
        ...


class HasTactics(Protocol):
    def tactics(self) -> TacticRegistry:
        ...
