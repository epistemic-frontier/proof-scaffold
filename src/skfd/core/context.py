# skfd/core/context.py
from __future__ import annotations

from dataclasses import dataclass

from .origin import OriginTable
from .symbols import SymbolDef, SymbolId, SymbolInterner


@dataclass
class Context:
    origin_table: OriginTable
    interner: SymbolInterner
    symtab: dict[SymbolId, SymbolDef]
