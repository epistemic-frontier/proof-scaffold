from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import TypeAlias

from .ids import Digest

JsonValue: TypeAlias = None | bool | int | float | str | Sequence["JsonValue"] | Mapping[str, "JsonValue"]


def canonical_digest(document: Mapping[str, JsonValue]) -> Digest:
    """Hash an explicit, versioned JSON projection deterministically."""
    encoded = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return Digest(hashlib.sha256(encoded).hexdigest())
