# prelude/axioms.py
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from skfd.authoring.formula import Formula, Sort
from skfd.authoring.typing import PreludeTypingError

F = TypeVar("F", bound=Formula[Sort])


@dataclass(frozen=True)
class AxiomSchema(Generic[F]):
    """A parameterized axiom schema.

    This is a *formula generator*, not an inference rule.
    It is intended as a human-facing writing tool:
      - name: schema identifier
      - arity: number of formula arguments
      - instantiate: callable that constructs the resulting formula
    """
    name: str
    arity: int
    instantiate: Callable[..., F]

    def apply(self, *args: F) -> F:
        if len(args) != self.arity:
            raise PreludeTypingError(
                f"axiom schema {self.name!r}: expects {self.arity} args, got {len(args)}"
            )
        return self.instantiate(*args)


__all__ = ["AxiomSchema"]
