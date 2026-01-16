# logic/propositional/hilbert/axioms.py
from __future__ import annotations

from collections.abc import Mapping

from skfd.authoring.dsl import Expr

from ._structures import Imp, Not, chi, phi, psi

# -----------------------------------------------------------------------------
# Axioms (author-facing)
#
# These are Expr trees built from the declared constructors and formal vars.
# They are NOT token-level formulas.
#
# Compilation is performed via HilbertSystem.compile(expr).
# -----------------------------------------------------------------------------

# A1: φ → (ψ → φ)
A1: Expr = Imp(phi, Imp(psi, phi))

# A2: (φ → (ψ → χ)) → ((φ → ψ) → (φ → χ))
A2: Expr = Imp(
    Imp(phi, Imp(psi, chi)),
    Imp(Imp(phi, psi), Imp(phi, chi)),
)

# A3: (¬φ → ¬ψ) → (ψ → φ)
A3: Expr = Imp(
    Imp(Not(phi), Not(psi)),
    Imp(psi, phi),
)


def make_axioms() -> Mapping[str, Expr]:
    return  {
        "A1": A1,
        "A2": A2,
        "A3": A3,
    }


__all__ = ["A1", "A2", "A3", "make_axioms"]