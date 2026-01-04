from __future__ import annotations

from dataclasses import dataclass

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

