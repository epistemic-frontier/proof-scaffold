# skfd/linker/passes/stage6_relocation.py
from __future__ import annotations

from skfd.core.symbols import SymbolDef, SymbolId


def run(symtab: dict[SymbolId, SymbolDef]) -> dict[SymbolId, str]:
    """
    Compute a deterministic relocation table.
    Maps SymbolId -> emitted_name (str).
    Ensures no collisions in the output namespace.
    """
    reloc_table: dict[SymbolId, str] = {}
    used_names: set[str] = set()

    # Deterministic iteration order: by SymbolId
    sorted_ids = sorted(symtab.keys())

    for sid in sorted_ids:
        defn = symtab[sid]
        base_name = defn.local_name
        candidate = base_name

        # Collision resolution strategy: append numeric suffix
        # Deterministic because input order is deterministic.
        counter = 0
        while candidate in used_names:
            candidate = f"{base_name}{counter}"
            counter += 1

        used_names.add(candidate)
        reloc_table[sid] = candidate

    return reloc_table
