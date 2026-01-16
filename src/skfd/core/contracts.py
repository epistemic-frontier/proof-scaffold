# skfd/core/contracts.py
from __future__ import annotations

from dataclasses import dataclass, field

from skfd.core.symbols import SymbolId


@dataclass(frozen=True)
class AssertionContract:
    """
    The interface contract of an exported assertion ($a or $p).
    Defines what is required to use this assertion in a proof.
    """

    label: SymbolId
    mandatory_hyps: list[SymbolId]  # Ordered list of $e hypothesis labels
    mandatory_vars: list[
        SymbolId
    ]  # Ordered list of $f variable definition labels ($f typecode var)
    distinct_vars: list[set[SymbolId]] = field(
        default_factory=list
    )  # List of disjoint sets ($d x y z)


@dataclass(frozen=True)
class TheoremDetails:
    """
    Internal analysis details of a theorem ($p).
    Used for dependency analysis and optimization.
    """

    label: SymbolId
    # Direct dependencies: exact set of assertion labels referenced by the proof
    direct_dependencies: set[SymbolId] = field(default_factory=set)
