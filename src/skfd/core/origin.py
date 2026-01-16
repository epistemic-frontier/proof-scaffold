# skfd/core/origin.py
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

OriginRef = int


@dataclass(frozen=True)
class OriginRecord:
    module_id: str
    file: str
    line: int


class OriginTable:
    """Deterministic origin interner."""

    def __init__(self) -> None:
        self._records: list[OriginRecord] = []
        self._index: dict[OriginRecord, OriginRef] = {}

    def intern(self, rec: OriginRecord) -> OriginRef:
        existing = self._index.get(rec)
        if existing is not None:
            return existing
        ref: OriginRef = len(self._records)
        self._records.append(rec)
        self._index[rec] = ref
        return ref

    def get(self, ref: OriginRef) -> OriginRecord:
        return self._records[ref]

    def dump(self, root: Path | None = None) -> list[dict[str, Any]]:
        """
        Return raw records for source map generation.
        If root is provided, relativize file paths against it.
        """
        records = []
        for r in self._records:
            fpath = r.file
            if root:
                try:
                    # Attempt to make relative
                    fpath = os.path.relpath(fpath, start=root)
                except ValueError:
                    # e.g., on Windows if on different drives, or if fail
                    pass
            records.append({"module": r.module_id, "file": fpath, "line": r.line})
        return records
