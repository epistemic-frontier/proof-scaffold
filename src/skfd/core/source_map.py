from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skfd.core.origin import OriginRef


@dataclass(frozen=True)
class SourceMapEntry:
    """Mapping from a generated line number (1-indexed) to an origin."""

    line: int
    origin: OriginRef


@dataclass(frozen=True)
class SourceMap:
    """A collection of source map entries."""

    entries: list[SourceMapEntry] = field(default_factory=list)

    def to_json(self) -> list[dict[str, Any]]:
        """Serialize to JSON-friendly format."""
        return [
            {
                "line": e.line,
                "origin_ref": e.origin,
            }
            for e in self.entries
        ]
