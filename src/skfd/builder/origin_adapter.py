# src/skfd/builder/origin_adapter.py
from __future__ import annotations

import inspect

from skfd.core.origin import OriginRecord, OriginRef, OriginTable


class OriginProvider:
    def here_ref(self, *, depth: int = 2) -> OriginRef:
        """Capture current location and return an interned OriginRef."""
        raise NotImplementedError


class InspectOriginAdapter(OriginProvider):
    def __init__(self, table: OriginTable, module_id: str) -> None:
        self._table = table
        self._module_id = module_id

    def here_ref(self, *, depth: int = 2) -> OriginRef:
        try:
            # depth+1 because this function is also on the stack
            frame = inspect.stack()[depth]
            file = frame.filename
            line = frame.lineno
        except Exception:
            file = "unknown"
            line = 0

        rec = OriginRecord(
            module_id=self._module_id,
            file=file,
            line=line,
        )
        return self._table.intern(rec)
