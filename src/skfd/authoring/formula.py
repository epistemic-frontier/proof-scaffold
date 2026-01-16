# skfd/authoring/formula.py
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import (
    Any,
    Generic,
    Literal,
    TypeAlias,
    TypeVar,
)

from skfd.core.symbols import SymbolId

# -----------------------------------------------------------------------------
# Sort
# -----------------------------------------------------------------------------

WffSort = Literal["wff"]
ClassSort = Literal["class"]
SetVarSort = Literal["setvar"]
Sort = Literal["wff", "class", "setvar"]

S = TypeVar("S", bound=Sort)

# -----------------------------------------------------------------------------
# Token-level Formula
# -----------------------------------------------------------------------------

TokenSeq: TypeAlias = tuple[SymbolId, ...]


@dataclass(frozen=True)
class Formula(Generic[S]):
    """A typed Metamath formula represented as a token sequence (SymbolId).

    Invariants:
    - tokens are SymbolId produced by skfd.core.symbols.SymbolInterner
    - tokens are layout-agnostic (no whitespace)
    - Formula does not carry provenance; provenance lives elsewhere (Hypothesis/IR side-table)
    """
    sort: S
    tokens: TokenSeq

    def __iter__(self) -> Iterable[SymbolId]:
        return iter(self.tokens)

    def __len__(self) -> int:
        return len(self.tokens)


Wff = Formula[WffSort]
Class = Formula[ClassSort]
SetVar = Formula[SetVarSort]


# -----------------------------------------------------------------------------
# Generic Constructors
# -----------------------------------------------------------------------------

def wff_atom(sym: SymbolId) -> Wff:
    """Construct an atomic wff from a single symbol token (usually a Var/Const)."""
    return Wff("wff", (sym,))


# -----------------------------------------------------------------------------
# Debug rendering (optional)
# -----------------------------------------------------------------------------

def render(tokens: Sequence[SymbolId], *, symtab: Mapping[SymbolId, Any]) -> str:
    """Render tokens using a symbol table (SymbolId -> SymbolDef-like with .local_name).

    This is for debugging only; do not use in emit layer.
    """
    parts: list[str] = []
    for t in tokens:
        d = symtab.get(t)
        if d is None:
            parts.append(f"<{t}>")
        else:
            parts.append(getattr(d, "local_name", str(d)))
    return " ".join(parts)


__all__ = [
    "Sort",
    "WffSort",
    "ClassSort",
    "SetVarSort",
    "Formula",
    "Wff",
    "Class",
    "SetVar",
    "TokenSeq",
    "wff_atom",
    "render",
]
