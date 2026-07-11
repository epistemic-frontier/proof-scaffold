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


class _Ter(_Ast):
    __slots__ = ("op", "a", "b", "c")

    def __init__(self, op: int, first: _Ast, second: _Ast, third: _Ast) -> None:
        self.op = op
        self.a = first
        self.b = second
        self.c = third

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, _Ter)
            and self.op == other.op
            and self.a == other.a
            and self.b == other.b
            and self.c == other.c
        )

    def __hash__(self) -> int:
        return hash(("ter", self.op, self.a, self.b, self.c))

    def __repr__(self) -> str:
        return f"Ter(op={self.op}, {self.a!r}, {self.b!r}, {self.c!r})"


class _Pre3(_Ast):
    __slots__ = ("op", "a", "b", "c")

    def __init__(self, op: int, first: _Ast, second: _Ast, third: _Ast) -> None:
        self.op = op
        self.a = first
        self.b = second
        self.c = third

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, _Pre3)
            and self.op == other.op
            and self.a == other.a
            and self.b == other.b
            and self.c == other.c
        )

    def __hash__(self) -> int:
        return hash(("pre3", self.op, self.a, self.b, self.c))


class _Pre2(_Ast):
    __slots__ = ("op", "a", "b")

    def __init__(self, op: int, first: _Ast, second: _Ast) -> None:
        self.op = op
        self.a = first
        self.b = second

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, _Pre2)
            and self.op == other.op
            and self.a == other.a
            and self.b == other.b
        )

    def __hash__(self) -> int:
        return hash(("pre2", self.op, self.a, self.b))


class _Substitution(_Ast):
    __slots__ = ("a", "b", "c")

    def __init__(self, first: _Ast, second: _Ast, third: _Ast) -> None:
        self.a = first
        self.b = second
        self.c = third

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, _Substitution)
            and self.a == other.a
            and self.b == other.b
            and self.c == other.c
        )

    def __hash__(self) -> int:
        return hash(("substitution", self.a, self.b, self.c))


class _BareBin(_Ast):
    __slots__ = ("op", "l", "r")

    def __init__(self, op: int, left: _Ast, right: _Ast) -> None:
        self.op = op
        self.l = left
        self.r = right

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, _BareBin)
            and self.op == other.op
            and self.l == other.l
            and self.r == other.r
        )

    def __hash__(self) -> int:
        return hash(("bare-bin", self.op, self.l, self.r))


# ── Unification context ────────────────────────────────────


class UnifyCtx:
    """Bundle of token ids needed for parsing and unification."""

    __slots__ = (
        "symtab",
        "neg",
        "imp",
        "and_",
        "lp",
        "rp",
        "binops",
        "bare_binops",
        "prefix2",
        "prefix3",
        "substitution",
    )

    def __init__(
        self,
        symtab: Mapping[int, SymbolDef],
        neg: int,
        imp: int,
        and_: int,
        lp: int,
        rp: int,
        binops: Sequence[int] | None = None,
        bare_binops: Sequence[int] | None = None,
        prefix2: Sequence[int] | None = None,
        prefix3: Sequence[int] | None = None,
        substitution: tuple[int, int, int] | None = None,
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
        self.bare_binops: tuple[int, ...] = (
            tuple(bare_binops) if bare_binops is not None else ()
        )
        self.prefix2: tuple[int, ...] = tuple(prefix2) if prefix2 is not None else ()
        self.prefix3: tuple[int, ...] = tuple(prefix3) if prefix3 is not None else ()
        self.substitution = substitution


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


def split_ternary(
    tokens: Sequence[int], op_token: int, *, lp: int, rp: int
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]] | None:
    """Split `( first OP second OP third )` into its three operands."""
    toks = tuple(tokens)
    if len(toks) < 7 or toks[0] != lp or toks[-1] != rp:
        return None
    inner = toks[1:-1]
    depth = 0
    split_at: list[int] = []
    for i, token in enumerate(inner):
        if token == lp:
            depth += 1
        elif token == rp:
            depth -= 1
            if depth < 0:
                return None
        elif token == op_token and depth == 0:
            split_at.append(i)
    if depth != 0 or len(split_at) != 2:
        return None
    first = inner[: split_at[0]]
    second = inner[split_at[0] + 1 : split_at[1]]
    third = inner[split_at[1] + 1 :]
    if not first or not second or not third:
        return None
    return tuple(first), tuple(second), tuple(third)


def _substitution_delimiters(
    ctx: UnifyCtx, tokens: Sequence[int], start: int
) -> tuple[int, int] | None:
    if ctx.substitution is None or tokens[start] != ctx.substitution[0]:
        return None
    sb_lb, sb_slash, sb_rb = ctx.substitution
    depth = 0
    slash_at: int | None = None
    for pos in range(start, len(tokens)):
        token = tokens[pos]
        if token == sb_lb:
            depth += 1
        elif token == sb_rb:
            depth -= 1
            if depth == 0:
                return None if slash_at is None else (slash_at, pos)
        elif token == sb_slash and depth == 1:
            slash_at = pos
    return None


def _take_wff(ctx: UnifyCtx, tokens: Sequence[int], start: int) -> int:
    if start >= len(tokens):
        raise ValueError("parse: missing prefix operand")
    token = tokens[start]
    if ctx.substitution is not None and token == ctx.substitution[0]:
        delimiters = _substitution_delimiters(ctx, tokens, start)
        if delimiters is None:
            raise ValueError("parse: malformed substitution expression")
        slash_at, close_at = delimiters
        if slash_at == start + 1 or close_at == slash_at + 1:
            raise ValueError("parse: empty substitution operand")
        return _take_wff(ctx, tokens, close_at + 1)
    if token == ctx.neg:
        return _take_wff(ctx, tokens, start + 1)
    if token in ctx.prefix2:
        end = start + 1
        for _ in range(2):
            end = _take_wff(ctx, tokens, end)
        return end
    if token in ctx.prefix3:
        end = start + 1
        for _ in range(3):
            end = _take_wff(ctx, tokens, end)
        return end
    if token == ctx.lp:
        depth = 0
        for pos in range(start, len(tokens)):
            if tokens[pos] == ctx.lp:
                depth += 1
            elif tokens[pos] == ctx.rp:
                depth -= 1
                if depth == 0:
                    return pos + 1
        raise ValueError("parse: unclosed parenthesis")
    end = start + 1
    if end < len(tokens) and tokens[end] in ctx.bare_binops:
        return _take_wff(ctx, tokens, end + 1)
    return end


def split_substitution(
    ctx: UnifyCtx, tokens: Sequence[int]
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]] | None:
    """Split ``[ term / variable ] body`` into its three operands."""
    if ctx.substitution is None:
        return None
    sb_lb, _, _ = ctx.substitution
    toks = tuple(tokens)
    if not toks or toks[0] != sb_lb:
        return None
    delimiters = _substitution_delimiters(ctx, toks, 0)
    if delimiters is None:
        return None
    slash_at, close_at = delimiters
    try:
        body_end = _take_wff(ctx, toks, close_at + 1)
    except ValueError:
        return None
    if body_end != len(toks):
        return None
    first = toks[1:slash_at]
    second = toks[slash_at + 1 : close_at]
    third = toks[close_at + 1 :]
    if not first or not second or not third:
        return None
    return first, second, third


def split_prefix3(
    ctx: UnifyCtx, tokens: Sequence[int], op_token: int
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]] | None:
    toks = tuple(tokens)
    if not toks or toks[0] != op_token:
        return None
    bounds = [1]
    try:
        for _ in range(3):
            bounds.append(_take_wff(ctx, toks, bounds[-1]))
    except ValueError:
        return None
    if bounds[-1] != len(toks):
        return None
    return (
        toks[bounds[0] : bounds[1]],
        toks[bounds[1] : bounds[2]],
        toks[bounds[2] : bounds[3]],
    )


def split_prefix2(
    ctx: UnifyCtx, tokens: Sequence[int], op_token: int
) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    toks = tuple(tokens)
    if not toks or toks[0] != op_token:
        return None
    try:
        middle = _take_wff(ctx, toks, 1)
        end = _take_wff(ctx, toks, middle)
    except ValueError:
        return None
    if end != len(toks):
        return None
    return toks[1:middle], toks[middle:end]


def split_bare_binary(
    ctx: UnifyCtx, tokens: Sequence[int], op_token: int
) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    toks = tuple(tokens)
    depth = 0
    for pos, token in enumerate(toks):
        if token == ctx.lp:
            depth += 1
        elif token == ctx.rp:
            depth -= 1
        elif token == op_token and depth == 0:
            if pos == 0 or pos == len(toks) - 1:
                return None
            return toks[:pos], toks[pos + 1 :]
    return None


# ── Parse ──────────────────────────────────────────────────


def parse(ctx: UnifyCtx, tokens: Sequence[int]) -> _Ast:
    """Parse a token sequence into an AST."""
    toks = tuple(tokens)
    if not toks:
        raise ValueError("parse: empty tokens")
    if len(toks) == 1:
        return _Atom(toks[0])
    substitution_parts = split_substitution(ctx, toks)
    if substitution_parts is not None:
        first, second, third = substitution_parts
        return _Substitution(parse(ctx, first), parse(ctx, second), parse(ctx, third))
    if toks[0] in ctx.prefix2:
        prefix2_parts = split_prefix2(ctx, toks, toks[0])
        if prefix2_parts is None:
            raise ValueError("parse: malformed binary prefix expression")
        first, second = prefix2_parts
        return _Pre2(toks[0], parse(ctx, first), parse(ctx, second))
    if toks[0] in ctx.prefix3:
        prefix_parts = split_prefix3(ctx, toks, toks[0])
        if prefix_parts is None:
            raise ValueError("parse: malformed ternary prefix expression")
        first, second, third = prefix_parts
        return _Pre3(toks[0], parse(ctx, first), parse(ctx, second), parse(ctx, third))
    if toks[0] == ctx.neg:
        return _Not(parse(ctx, toks[1:]))
    for op in ctx.bare_binops:
        bare_parts = split_bare_binary(ctx, toks, op)
        if bare_parts is not None:
            left, right = bare_parts
            return _BareBin(op, parse(ctx, left), parse(ctx, right))
    for op in ctx.binops:
        parts3 = split_ternary(toks, op, lp=ctx.lp, rp=ctx.rp)
        if parts3 is not None:
            first, second, third = parts3
            return _Ter(op, parse(ctx, first), parse(ctx, second), parse(ctx, third))
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
    if isinstance(ast, _Ter):
        return (
            ctx.lp,
            *to_tokens(ctx, ast.a),
            ast.op,
            *to_tokens(ctx, ast.b),
            ast.op,
            *to_tokens(ctx, ast.c),
            ctx.rp,
        )
    if isinstance(ast, _Pre3):
        return (
            ast.op,
            *to_tokens(ctx, ast.a),
            *to_tokens(ctx, ast.b),
            *to_tokens(ctx, ast.c),
        )
    if isinstance(ast, _Pre2):
        return (ast.op, *to_tokens(ctx, ast.a), *to_tokens(ctx, ast.b))
    if isinstance(ast, _Substitution):
        if ctx.substitution is None:
            raise ValueError("to_tokens: missing substitution delimiters")
        sb_lb, sb_slash, sb_rb = ctx.substitution
        return (
            sb_lb,
            *to_tokens(ctx, ast.a),
            sb_slash,
            *to_tokens(ctx, ast.b),
            sb_rb,
            *to_tokens(ctx, ast.c),
        )
    if isinstance(ast, _BareBin):
        return (*to_tokens(ctx, ast.l), ast.op, *to_tokens(ctx, ast.r))
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
    if isinstance(ast, _Ter):
        return _Ter(
            ast.op,
            apply_subst(ctx, ast.a, subst),
            apply_subst(ctx, ast.b, subst),
            apply_subst(ctx, ast.c, subst),
        )
    if isinstance(ast, _Pre3):
        return _Pre3(
            ast.op,
            apply_subst(ctx, ast.a, subst),
            apply_subst(ctx, ast.b, subst),
            apply_subst(ctx, ast.c, subst),
        )
    if isinstance(ast, _Pre2):
        return _Pre2(
            ast.op,
            apply_subst(ctx, ast.a, subst),
            apply_subst(ctx, ast.b, subst),
        )
    if isinstance(ast, _Substitution):
        return _Substitution(
            apply_subst(ctx, ast.a, subst),
            apply_subst(ctx, ast.b, subst),
            apply_subst(ctx, ast.c, subst),
        )
    if isinstance(ast, _BareBin):
        return _BareBin(
            ast.op,
            apply_subst(ctx, ast.l, subst),
            apply_subst(ctx, ast.r, subst),
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
    if isinstance(template, _Ter):
        ternary_target = cast(_Ter, target)
        if template.op != ternary_target.op:
            raise ValueError("unify: op mismatch")
        unify(ctx, template.a, ternary_target.a, subst)
        unify(ctx, template.b, ternary_target.b, subst)
        unify(ctx, template.c, ternary_target.c, subst)
        return
    if isinstance(template, _Pre3):
        prefix_target = cast(_Pre3, target)
        if template.op != prefix_target.op:
            raise ValueError("unify: op mismatch")
        unify(ctx, template.a, prefix_target.a, subst)
        unify(ctx, template.b, prefix_target.b, subst)
        unify(ctx, template.c, prefix_target.c, subst)
        return
    if isinstance(template, _Pre2):
        prefix2_target = cast(_Pre2, target)
        if template.op != prefix2_target.op:
            raise ValueError("unify: op mismatch")
        unify(ctx, template.a, prefix2_target.a, subst)
        unify(ctx, template.b, prefix2_target.b, subst)
        return
    if isinstance(template, _Substitution):
        substitution_target = cast(_Substitution, target)
        unify(ctx, template.a, substitution_target.a, subst)
        unify(ctx, template.b, substitution_target.b, subst)
        unify(ctx, template.c, substitution_target.c, subst)
        return
    if isinstance(template, _BareBin):
        bare_target = cast(_BareBin, target)
        if template.op != bare_target.op:
            raise ValueError("unify: op mismatch")
        unify(ctx, template.l, bare_target.l, subst)
        unify(ctx, template.r, bare_target.r, subst)
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
