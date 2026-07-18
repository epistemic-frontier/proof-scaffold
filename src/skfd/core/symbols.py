# skfd/core/symbols.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from skfd.core.diag import Diagnostic, LinkerDiagError

from .origin import OriginRef

SymbolId = int
SymbolKind = Literal["Const", "Var", "Label"]


@dataclass(frozen=True)
class SymbolDef:
    id: SymbolId
    kind: SymbolKind
    origin_ref: OriginRef
    local_name: str
    origin_module_id: str


SymbolKey = tuple[str, str, SymbolKind]


class SymbolInterner:
    """Global interner: (origin_module_id, local_name, kind) -> SymbolId."""

    def __init__(self) -> None:
        self._defs: dict[SymbolId, SymbolDef] = {}
        self._key_to_id: dict[SymbolKey, SymbolId] = {}

    def intern(
        self,
        *,
        origin_module_id: str,
        local_name: str,
        kind: SymbolKind,
        origin_ref: OriginRef,
    ) -> SymbolId:
        if local_name.startswith("$"):
            raise LinkerDiagError(
                Diagnostic(
                    error_code="E_RESERVED_TOKEN_NAME",
                    message="token local_name must not start with '$'",
                    primary_origin_ref=origin_ref,
                    related_origin_refs=(),
                    origin_chain=(),
                    details={"hint_original_token": local_name, "kind": kind},
                )
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
        return dict(self._defs)

    def get(self, symbol_id: SymbolId) -> SymbolDef | None:
        """Return one immutable symbol definition without copying the full table."""
        return self._defs.get(symbol_id)
