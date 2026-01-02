from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .ir import Origin

ErrorCode = Literal[
    "E_SCOPE_IMBALANCE",
    "E_UNRESOLVED_LABEL",
    "E_RAW_TOKEN_FORBIDDEN",
    "E_CROSS_UNIT_HYP_LEAKAGE",
    "E_NON_EXPORTED_LABEL_REF",
    "E_DEP_CYCLE",
    "E_MISSING_ORIGIN",
    "E_SYMBOL_COLLISION",
]


@dataclass(frozen=True)
class Diagnostic:
    error_code: ErrorCode
    message: str
    primary_origin: Origin | None = None
    related_origins: tuple[Origin | None, ...] = field(default_factory=tuple)
    origin_chain: tuple[str, ...] = field(default_factory=tuple)
    details: dict[str, Any] = field(default_factory=dict)

    def to_json_obj(self) -> dict[str, Any]:
        def _origin_to_obj(o: Origin | None) -> dict[str, Any] | None:
            if o is None:
                return None
            return {"module": o.module, "file": o.file, "line": o.line}

        return {
            "error_code": self.error_code,
            "message": self.message,
            "primary_origin": _origin_to_obj(self.primary_origin),
            "related_origins": [_origin_to_obj(o) for o in self.related_origins],
            "origin_chain": list(self.origin_chain),
            "details": dict(self.details),
        }
