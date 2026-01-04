# scaffold/dsl/types.py
from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from proof_scaffold.theorem import Theorem
from .errors import MMDSLError

TypeCode = str
Token = str
Label = str
KindHyp = Literal["$f", "$e"]
KindAssert = Literal["$a", "$p"]
ProofStep = str | Theorem


def _join_tokens(tokens: Sequence[str]) -> str:
    return " ".join(tokens)


def expr(*tokens: str) -> tuple[str, ...]:
    """A tiny expression constructor."""
    if not tokens:
        raise MMDSLError("expr() must be non-empty")
    return tuple(tokens)
