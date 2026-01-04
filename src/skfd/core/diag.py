# skfd/core/diag.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Diagnostic:
    """Structured diagnostic per Link Model v4.

    Notes
    -----
    - `details` must be JSON-serializable.
    - Any lists inside details should be deterministically ordered by the
      producing pass.
    """

    error_code: str
    message: str
    primary_origin_ref: int
    related_origin_refs: tuple[int, ...] = field(default_factory=tuple)
    origin_chain: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    details: dict[str, Any] = field(default_factory=dict)

    def to_json_obj(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "primary_origin_ref": self.primary_origin_ref,
            "related_origin_refs": list(self.related_origin_refs),
            "origin_chain": list(self.origin_chain),
            "details": self.details,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(
            self.to_json_obj(),
            ensure_ascii=False,
            sort_keys=True,
            indent=indent,
        )


class LinkerDiagError(RuntimeError):
    def __init__(self, diag: Diagnostic):
        super().__init__(diag.message)
        self.diag = diag

    def __str__(self) -> str:  # deterministic
        obj = self.diag.to_json_obj()
        # Stable keys for deterministic snapshots.
        return json.dumps(obj, ensure_ascii=False, sort_keys=True)
