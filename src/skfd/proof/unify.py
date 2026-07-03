"""Token-level formula unification for proof lowering.

Extracted from emit.py so ProofBuilder can also use it
for automatic hypothesis matching at authoring time.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from skfd.core.symbols import SymbolDef


# ── AST nodes ──────────────────────────────────────────────


class _Ast:
    __slots__ = ()


class _Atom(_Ast):
    __slots__ = ("tok",)

    def __init__(self, tok: int) -> None:
        self.tok = tok

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Atom) and self.tok == other.tok

    def __hash__(self) -> int:
        return hash(self.tok)

    def __repr__(self) -> str:
        return f"Atom({self.tok})"


class _Not(_Ast):
    __slots__ = ("x",)

    def __init__(self, x: _Ast) -> None:
        self.x = x

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Not) and self.x == other.x

    def __hash__(self) -> int:
        return hash(("not", self.x))

    def __repr__(self) -> str:
        return f"Not({self.x!r})"


class _Bin(_Ast):
    __slots__ = ("op", "l", "r")

    def __init__(self, op: int, left: _Ast, right: _Ast) -> None:
        self.op = op
        self.l = left
        self.r = right

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, _Bin)
            and self.op == other.op
            and self.l == other.l
            and self.r == other.r
        )

    def __hash__(self) -> int:
        return hash(("bin", self.op, self.l, self.r))

    def __repr__(self) -> str:
        return f"Bin(op={self.op}, {self.l!r}, {self.r!r})"


# ── Unification context ────────────────────────────────────


class UnifyCtx:
    """Bundle of token ids needed for parsing and unification."""

    __slots__ = ("symtab", "neg", "imp", "and_", "lp", "rp", "binops")

    def __init__(
        self,
        symtab: Mapping[int, SymbolDef],
        neg: int,
        imp: int,
        and_: int,
        lp: int,
        rp: int,
        binops: Sequence[int] | None = None,
    ) -> None:
        self.symtab = symtab
        self.neg = neg
        self.imp = imp
        self.and_ = and_
        self.lp = lp
        self.rp = rp
        # Infix binary operators recognised by the parser, in the order they
        # are tried. Because every compound wff is fully parenthesised as
        # ``( left OP right )`` there is exactly one depth-0 operator, so the
        # order only affects which candidate matches first. Defaults to the
        # historical ``imp``/``and_`` pair; callers may pass extra connectives
        # (e.g. disjunction) that their logic exposes.
        self.binops: tuple[int, ...] = (
            tuple(binops) if binops is not None else (imp, and_)
        )


# ── Binary split ───────────────────────────────────────────


def split_binary(
    tokens: Sequence[int], op_token: int, *, lp: int, rp: int
) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    """Split `( left OP right )` into (left, right)."""
    toks = tuple(tokens)
    if len(toks) < 5 or toks[0] != lp or toks[-1] != rp:
        return None
    inner = toks[1:-1]
    depth = 0
    split_at: int | None = None
    for i, t in enumerate(inner):
        if t == lp:
            depth += 1
        elif t == rp:
            depth -= 1
            if depth < 0:
                return None
        elif t == op_token and depth == 0:
            split_at = i
            break
    if depth != 0 or split_at is None:
        return None
    left = inner[:split_at]
    right = inner[split_at + 1 :]
    if not left or not right:
        return None
    return tuple(left), tuple(right)


# ── Parse ──────────────────────────────────────────────────


def parse(ctx: UnifyCtx, tokens: Sequence[int]) -> _Ast:
    """Parse a token sequence into an AST."""
    toks = tuple(tokens)
    if not toks:
        raise ValueError("parse: empty tokens")
    if len(toks) == 1:
        return _Atom(toks[0])
    if toks[0] == ctx.neg:
        return _Not(parse(ctx, toks[1:]))
    for op in ctx.binops:
        parts = split_binary(toks, op, lp=ctx.lp, rp=ctx.rp)
        if parts is not None:
            left, right = parts
            return _Bin(op, parse(ctx, left), parse(ctx, right))
    raise ValueError("parse: unsupported token shape")


# ── Serialize ──────────────────────────────────────────────


def to_tokens(ctx: UnifyCtx, ast: _Ast) -> tuple[int, ...]:
    """Serialize an AST back to tokens."""
    if isinstance(ast, _Atom):
        return (ast.tok,)
    if isinstance(ast, _Not):
        return (ctx.neg, *to_tokens(ctx, ast.x))
    if isinstance(ast, _Bin):
        return (
            ctx.lp,
            *to_tokens(ctx, ast.l),
            ast.op,
            *to_tokens(ctx, ast.r),
            ctx.rp,
        )
    raise ValueError("to_tokens: unsupported ast")


# ── Substitute ─────────────────────────────────────────────


def apply_subst(ctx: UnifyCtx, ast: _Ast, subst: Mapping[int, _Ast]) -> _Ast:
    """Apply a variable substitution to an AST."""
    if isinstance(ast, _Atom) and ctx.symtab[ast.tok].kind == "Var":
        return subst.get(ast.tok, ast)
    if isinstance(ast, _Not):
        return _Not(apply_subst(ctx, ast.x, subst))
    if isinstance(ast, _Bin):
        return _Bin(
            ast.op, apply_subst(ctx, ast.l, subst), apply_subst(ctx, ast.r, subst)
        )
    return ast


# ── Unify ──────────────────────────────────────────────────


def unify(ctx: UnifyCtx, template: _Ast, target: _Ast, subst: dict[int, _Ast]) -> None:
    """Unify *template* with *target*, writing substitutions into *subst*.

    Raises ValueError on mismatch.
    """
    if isinstance(template, _Atom) and ctx.symtab[template.tok].kind == "Var":
        existing = subst.get(template.tok)
        if existing is None:
            subst[template.tok] = target
            return
        if existing != target:
            raise ValueError("unify: inconsistent substitution")
        return
    if type(template) is not type(target):
        raise ValueError("unify: node kind mismatch")
    if isinstance(template, _Atom):
        if template.tok != cast(_Atom, target).tok:
            raise ValueError("unify: atom mismatch")
        return
    if isinstance(template, _Not):
        unify(ctx, template.x, cast(_Not, target).x, subst)
        return
    if isinstance(template, _Bin):
        t = cast(_Bin, target)
        if template.op != t.op:
            raise ValueError("unify: op mismatch")
        unify(ctx, template.l, t.l, subst)
        unify(ctx, template.r, t.r, subst)
        return
    raise ValueError("unify: unsupported ast")


# ── Convenience ────────────────────────────────────────────


def unify_tokens(
    ctx: UnifyCtx,
    tmpl_tokens: Sequence[int],
    target_tokens: Sequence[int],
) -> dict[int, _Ast]:
    """Unify two token sequences, returning the variable substitution.

    Raises ValueError on mismatch.
    """
    subst: dict[int, _Ast] = {}
    unify(ctx, parse(ctx, tmpl_tokens), parse(ctx, target_tokens), subst)
    return subst


def tokens_match(
    ctx: UnifyCtx,
    a: Sequence[int],
    b: Sequence[int],
) -> bool:
    """Check if two token sequences are structurally equal (not unification)."""
    return tuple(a) == tuple(b)
