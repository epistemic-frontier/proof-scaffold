# logic/propositional/hilbert/definitions.py
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from skfd.authoring.dsl import Expr
from skfd.authoring.typing import PreludeTypingError

from ._structures import Imp, Not

# -----------------------------------------------------------------------------
# Definition schema (author-facing)
#
# A definition is a macro:
#   - It introduces a new *name* for an Expr pattern.
#   - It must be expandable into core language constructs.
#   - It does NOT add new axioms or inference rules.
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Definition:
    """A definitional macro.

    - name: human-readable name (e.g. 'Or')
    - arity: number of arguments
    - body: function mapping Expr arguments to an Expr
    """
    name: str
    arity: int
    body: Callable[..., Expr]

    def apply(self, *args: Expr) -> Expr:
        if len(args) != self.arity:
            raise PreludeTypingError(
                f"definition {self.name!r}: expects {self.arity} args, got {len(args)}"
            )
        return self.body(*args)

    def expand(self, *args: Expr) -> Expr:
        """Expand the definition into core language Expr."""
        return self.apply(*args)


# -----------------------------------------------------------------------------
# Concrete definitions
# -----------------------------------------------------------------------------

# Or(φ, ψ) := ¬φ → ψ
Or = Definition(
    name="Or",
    arity=2,
    body=lambda a, b: Imp(Not(a), b),
)


# Collect definitions for convenience / introspection
DEFINITIONS: Mapping[str, Definition] = {
    "Or": Or,
}

__all__ = ["Definition", "Or", "DEFINITIONS"]
