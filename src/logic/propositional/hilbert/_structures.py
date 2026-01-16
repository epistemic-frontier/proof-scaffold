# logic/propositional/hilbert/_structures.py
from __future__ import annotations

from skfd.authoring.dsl import Constructor, Var, require
from skfd.authoring.typing import WFF

# -----------------------------------------------------------------------------
# Language skeleton (author-facing)
#
# This module declares:
# - formal variables (φ, ψ, χ, ...)
# - core constructors with arity (→, ¬, ∧)
# - require(...) declarations for signatures (wff discipline)
#
# No Builtins / SymbolInterner here.
# -----------------------------------------------------------------------------

# Formal variables
phi = Var(name="φ")
psi = Var(name="ψ")
chi = Var(name="χ")

# Core constructors (author-visible symbols)
Imp = Constructor("→", 2)
Not = Constructor("¬", 1)
And = Constructor("∧", 2)

# Signature declarations (arity/sort)
require(Imp, in_sorts=(WFF, WFF), out_sort=WFF, notes="implication")
require(Not, in_sorts=(WFF,), out_sort=WFF, notes="negation")
require(And, in_sorts=(WFF, WFF), out_sort=WFF, notes="conjunction")

__all__ = [
    "phi",
    "psi",
    "chi",
    "Imp",
    "Not",
    "And",
]
