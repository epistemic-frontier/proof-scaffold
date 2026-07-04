# skfd/core/unit.py
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from .lir import LIRStmt
from .origin import OriginRef
from .symbols import SymbolId

UnitId = str
UnitKind = Literal["foundation", "library", "application"]


@dataclass(frozen=True)
class ProofUnitIR:
    unit_id: UnitId
    origin_ref: OriginRef
    origin_module_id: str
    lir_stmts: Sequence[LIRStmt]
    exports: list[SymbolId] = field(default_factory=list)
    kind: UnitKind = "library"
