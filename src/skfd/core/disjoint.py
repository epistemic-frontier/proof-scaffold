from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TypeAlias

from .symbols import SymbolDef, SymbolId

DVPair: TypeAlias = tuple[SymbolId, SymbolId]
DVSpec: TypeAlias = tuple[DVPair, ...]


class DisjointSpecError(ValueError):
    """Raised when an assertion-level distinct-variable specification is invalid."""


def normalize_dv_pairs(
    pairs: Iterable[Sequence[SymbolId]],
    *,
    symtab: Mapping[SymbolId, SymbolDef],
) -> DVSpec:
    """Validate, canonicalize, de-duplicate, and deterministically sort DV pairs.

    Assertion-level DV data is deliberately pair-based.  A Metamath statement
    such as ``$d x y z $.`` must be expanded by the source frontend before it
    reaches this boundary; accepting arbitrary groups here would make it too
    easy to accidentally turn ``$d x y $. $d y z $.`` into the stronger
    three-variable clique.
    """

    normalized: set[DVPair] = set()

    def symbol_key(sid: SymbolId) -> tuple[str, str, SymbolId]:
        definition = symtab.get(sid)
        if definition is None:
            raise DisjointSpecError(f"unknown SymbolId in DV pair: {sid}")
        if definition.kind != "Var":
            raise DisjointSpecError(
                f"DV pair endpoint must be a Var: {definition.local_name!r}"
            )
        return (definition.origin_module_id, definition.local_name, sid)

    for raw_pair in pairs:
        pair = tuple(raw_pair)
        if len(pair) != 2:
            raise DisjointSpecError(
                f"assertion-level DV entries must be pairs, got {len(pair)} endpoints"
            )
        left, right = pair
        left_key = symbol_key(left)
        right_key = symbol_key(right)
        if left == right:
            raise DisjointSpecError("a variable cannot be disjoint from itself")
        normalized.add((left, right) if left_key < right_key else (right, left))

    return tuple(
        sorted(
            normalized,
            key=lambda pair: (symbol_key(pair[0]), symbol_key(pair[1])),
        )
    )


__all__ = [
    "DVPair",
    "DVSpec",
    "DisjointSpecError",
    "normalize_dv_pairs",
]
