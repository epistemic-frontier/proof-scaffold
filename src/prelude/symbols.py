# prelude/symbols.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

# -----------------------------------------------------------------------------
# Prelude-level symbol system
#
# Design goals:
# - Pure / dependency-free (no linker diagnostics here)
# - Stable semantics: global interner mapping
#     (origin_module_id, local_name, kind) -> SymbolId
# - Keep minimal provenance hook via `origin_ref: Any`
# -----------------------------------------------------------------------------

SymbolId: TypeAlias = int
SymbolKind = Literal["Const", "Var", "Label"]


class PreludeSymbolError(ValueError):
    """Raised when prelude symbol constraints are violated."""


@dataclass(frozen=True)
class SymbolDef:
    id: SymbolId
    kind: SymbolKind
    origin_ref: Any  # opaque handle; core layer can pass OriginRef, tests can pass str, etc.
    local_name: str
    origin_module_id: str


SymbolKey: TypeAlias = tuple[str, str, SymbolKind]


class SymbolInterner:
    """Global interner: (origin_module_id, local_name, kind) -> SymbolId.

    Notes:
    - IDs are contiguous starting at 0.
    - If the same key is interned multiple times, returns the existing SymbolId.
    - prelude does not enforce any export/import policy; linker layer will.
    """

    def __init__(self) -> None:
        self._defs: dict[SymbolId, SymbolDef] = {}
        self._key_to_id: dict[SymbolKey, SymbolId] = {}

    def intern(
        self,
        *,
        origin_module_id: str,
        local_name: str,
        kind: SymbolKind,
        origin_ref: Any = None,
    ) -> SymbolId:
        # Keep the same "reserved token name" rule, but prelude raises a plain error.
        if local_name.startswith("$"):
            raise PreludeSymbolError(
                f"reserved token local_name: must not start with '$' (got {local_name!r}, kind={kind!r})"
            )

        key: SymbolKey = (origin_module_id, local_name, kind)
        existing = self._key_to_id.get(key)
        if existing is not None:
            return existing

        sid: SymbolId = len(self._defs)
        self._key_to_id[key] = sid
        self._defs[sid] = SymbolDef(
            id=sid,
            kind=kind,
            origin_ref=origin_ref,
            local_name=local_name,
            origin_module_id=origin_module_id,
        )
        return sid

    def symbol_table(self) -> dict[SymbolId, SymbolDef]:
        # Defensive copy to avoid external mutation.
        return dict(self._defs)

    def lookup(self, sid: SymbolId) -> SymbolDef:
        try:
            return self._defs[sid]
        except KeyError as e:
            raise PreludeSymbolError(f"unknown SymbolId: {sid}") from e

    def __len__(self) -> int:
        return len(self._defs)


__all__ = [
    "SymbolId",
    "SymbolKind",
    "SymbolDef",
    "SymbolKey",
    "PreludeSymbolError",
    "SymbolInterner",
]
