from __future__ import annotations

from dataclasses import dataclass

from .origin import OriginTable
from .symbols import SymbolDef, SymbolId, SymbolInterner


@dataclass
class LinkerContext:
    origin_table: OriginTable
    interner: SymbolInterner
    symtab: dict[SymbolId, SymbolDef]
