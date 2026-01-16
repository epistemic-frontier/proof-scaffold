# prelude/formula.py
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import (
    Any,
)

from skfd.authoring.formula import TokenSeq, Wff
from skfd.core.symbols import SymbolId, SymbolInterner

# -----------------------------------------------------------------------------
# Reserved / builtin tokens (by name)
# -----------------------------------------------------------------------------

GLOBAL_PRELUDE_MODULE_ID: str = "__prelude__"


@dataclass(frozen=True)
class Builtins:
    """Builtin constant tokens used by early propositional logic.

    These are Const symbols in the interner, not magic.
    """
    lp: SymbolId     # "("
    rp: SymbolId     # ")"
    imp: SymbolId    # "->"
    neg: SymbolId    # "~"
    and_: SymbolId   # "/\\"

    @staticmethod
    def ensure(
        interner: SymbolInterner,
        *,
        origin_module_id: str = GLOBAL_PRELUDE_MODULE_ID,
        origin_ref: Any = None,
    ) -> Builtins:
        """Intern builtin tokens.

        IMPORTANT:
        - Use a fixed origin_module_id by default so builtin tokens are global-stable.
        - If you override origin_module_id, you are intentionally creating a distinct builtin set.
        """
        lp = interner.intern(
            origin_module_id=origin_module_id, local_name="(", kind="Const", origin_ref=origin_ref
        )
        rp = interner.intern(
            origin_module_id=origin_module_id, local_name=")", kind="Const", origin_ref=origin_ref
        )
        imp = interner.intern(
            origin_module_id=origin_module_id, local_name="->", kind="Const", origin_ref=origin_ref
        )
        neg = interner.intern(
            origin_module_id=origin_module_id, local_name="~", kind="Const", origin_ref=origin_ref
        )
        and_ = interner.intern(
            origin_module_id=origin_module_id, local_name="/\\", kind="Const", origin_ref=origin_ref
        )
        return Builtins(lp=lp, rp=rp, imp=imp, neg=neg, and_=and_)


# -----------------------------------------------------------------------------
# Constructors
# -----------------------------------------------------------------------------

def wff_atom(sym: SymbolId) -> Wff:
    """Construct an atomic wff from a single symbol token (usually a Var/Const)."""
    return Wff("wff", (sym,))


def imp(b: Builtins, phi: Wff, psi: Wff) -> Wff:
    """Construct ( phi -> psi ) at token level."""
    return Wff("wff", (b.lp, *phi.tokens, b.imp, *psi.tokens, b.rp))


def wn(b: Builtins, phi: Wff) -> Wff:
    """Construct ~phi."""
    return Wff("wff", (b.neg, *phi.tokens))


def wa(b: Builtins, phi: Wff, psi: Wff) -> Wff:
    """Construct ( phi /\ psi )."""
    return Wff("wff", (b.lp, *phi.tokens, b.and_, *psi.tokens, b.rp))


# -----------------------------------------------------------------------------
# Shape matching for implication
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class ImpShape:
    phi: TokenSeq
    psi: TokenSeq


def try_parse_imp(b: Builtins, tokens: Sequence[SymbolId]) -> ImpShape | None:
    """Parse tokens as ( phi -> psi ) with parenthesis balancing.

    Accepts only the outermost form:
      '('  <phi>  '->'  <psi>  ')'
    where <phi> and <psi> are non-empty token sequences.
    """
    toks: TokenSeq = tuple(tokens)

    if len(toks) < 5:
        return None
    if toks[0] != b.lp or toks[-1] != b.rp:
        return None

    inner = toks[1:-1]
    if not inner:
        return None

    # Find the top-level '->' in inner: balance parentheses.
    depth = 0
    split_at: int | None = None

    for i, t in enumerate(inner):
        if t == b.lp:
            depth += 1
        elif t == b.rp:
            depth -= 1
            if depth < 0:
                return None
        elif t == b.imp and depth == 0:
            split_at = i
            break

    if depth != 0:
        return None
    if split_at is None:
        return None

    left = inner[:split_at]
    right = inner[split_at + 1 :]
    if not left or not right:
        return None

    return ImpShape(phi=left, psi=right)


@dataclass(frozen=True)
class NegShape:
    body: TokenSeq


def try_parse_wn(b: Builtins, tokens: Sequence[SymbolId]) -> NegShape | None:
    toks = tuple(tokens)
    if len(toks) < 2:
        return None
    if toks[0] != b.neg:
        return None
    return NegShape(body=toks[1:])


@dataclass(frozen=True)
class AndShape:
    left: TokenSeq
    right: TokenSeq


def try_parse_wa(b: Builtins, tokens: Sequence[SymbolId]) -> AndShape | None:
    toks = tuple(tokens)
    if len(toks) < 5:
        return None
    if toks[0] != b.lp or toks[-1] != b.rp:
        return None

    inner = toks[1:-1]
    depth = 0
    split_at = None
    for i, t in enumerate(inner):
        if t == b.lp:
            depth += 1
        elif t == b.rp:
            depth -= 1
        elif t == b.and_ and depth == 0:
            split_at = i
            break

    if split_at is None or depth != 0:
        return None

    left = inner[:split_at]
    right = inner[split_at + 1 :]
    if not left or not right:
        return None

    return AndShape(left=left, right=right)


__all__ = [
    "GLOBAL_PRELUDE_MODULE_ID",
    "Builtins",
    "wff_atom",
    "imp",
    "wn",
    "wa",
    "ImpShape",
    "try_parse_imp",
    "NegShape",
    "try_parse_wn",
    "AndShape",
    "try_parse_wa",
]
