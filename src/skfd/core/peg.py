from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Generic, Literal, Protocol, TypeVar

T = TypeVar("T")


class TokenLike(Protocol):
    @property
    def type(self) -> str: ...

    @property
    def value(self) -> str: ...

    @property
    def pos(self) -> int: ...


Assoc = Literal["left", "right", "none"]


@dataclass(frozen=True)
class ParseError(Exception):
    text: str
    pos: int
    message: str


@dataclass
class TokenStream(Generic[T]):
    text: str
    tokens: Sequence[TokenLike]
    _memo: dict[tuple[int, int], object] = field(default_factory=dict)

    def peek(self, i: int) -> TokenLike:
        if i < 0:
            return self.tokens[0]
        if i >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[i]


ParseResult = tuple[T, int] | None


class Rule(Generic[T]):
    _next_id = 1

    def __init__(self, name: str, fn: Callable[[TokenStream, int], ParseResult[T]]):
        self.name = name
        self.fn = fn
        self._id = Rule._next_id
        Rule._next_id += 1

    def __call__(self, s: TokenStream, i: int) -> ParseResult[T]:
        key = (self._id, i)
        cached = s._memo.get(key)
        if cached is not None:
            if cached is False:
                return None
            return cached  # type: ignore[return-value]
        out = self.fn(s, i)
        s._memo[key] = out if out is not None else False
        return out


class ForwardRule(Generic[T]):
    def __init__(self, name: str):
        self.name = name
        self._target: Rule[T] | None = None

    def set(self, target: Rule[T]) -> None:
        self._target = target

    def __call__(self, s: TokenStream, i: int) -> ParseResult[T]:
        if self._target is None:
            raise RuntimeError(f"ForwardRule {self.name!r} is unset")
        return self._target(s, i)


@dataclass(frozen=True)
class InfixOp(Generic[T]):
    precedence: int
    assoc: Assoc
    build: Callable[[T, T], T]


class ExpressionRule(Generic[T]):
    def __init__(
        self,
        *,
        atom: Callable[[TokenStream, int], ParseResult[T]],
        infix_of: Callable[[TokenLike], InfixOp[T] | None],
    ):
        self._atom = atom
        self._infix_of = infix_of
        self._memo: dict[tuple[int, int], ParseResult[T]] = {}

    def parse(self, s: TokenStream, i: int) -> ParseResult[T]:
        return self._parse_min(s, i, 0)

    def _parse_min(self, s: TokenStream, i: int, min_prec: int) -> ParseResult[T]:
        key = (i, min_prec)
        cached = self._memo.get(key)
        if cached is not None:
            return cached

        atom_out = self._atom(s, i)
        if atom_out is None:
            self._memo[key] = None
            return None

        left, j = atom_out
        while True:
            tok = s.peek(j)
            op = self._infix_of(tok)
            if op is None:
                break
            if op.precedence < min_prec:
                break

            right_min = op.precedence + 1 if op.assoc == "left" else op.precedence
            right_out = self._parse_min(s, j + 1, right_min)
            if right_out is None:
                self._memo[key] = None
                return None
            right, k = right_out
            left = op.build(left, right)
            j = k

        out: ParseResult[T] = (left, j)
        self._memo[key] = out
        return out
