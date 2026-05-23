from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from skfd.core.peg import (
    ExpressionRule,
    ForwardRule,
    InfixOp,
    ParseError,
    Rule,
    TokenStream,
)


@dataclass(frozen=True)
class _Tok:
    type: str
    value: str
    pos: int


def _stream(*values: str) -> TokenStream[str]:
    toks = [_Tok("SYM", value, i) for i, value in enumerate(values)]
    return TokenStream(text=" ".join(values), tokens=toks)


def _atom(s: TokenStream[str], i: int) -> tuple[str, int] | None:
    tok = s.peek(i)
    if tok.value.isalpha():
        return tok.value, i + 1
    return None


def test_token_stream_peek_clamps_to_stream_edges() -> None:
    s = _stream("a", "+", "b")

    assert s.peek(-1).value == "a"
    assert s.peek(99).value == "b"
    assert s.peek(1).value == "+"


def test_rule_memoizes_success_and_failure() -> None:
    calls: list[int] = []

    def parse_a(s: TokenStream[str], i: int) -> tuple[str, int] | None:
        calls.append(i)
        if s.peek(i).value == "a":
            return "A", i + 1
        return None

    rule = Rule("a", parse_a)
    s = _stream("a", "b")

    assert rule(s, 0) == ("A", 1)
    assert rule(s, 0) == ("A", 1)
    assert rule(s, 1) is None
    assert rule(s, 1) is None
    assert calls == [0, 1]


def test_forward_rule_requires_target_before_use() -> None:
    s = _stream("a")
    fwd: ForwardRule[str] = ForwardRule("expr")

    with pytest.raises(RuntimeError, match="unset"):
        fwd(s, 0)

    fwd.set(Rule("atom", _atom))
    assert fwd(s, 0) == ("a", 1)


def test_expression_rule_respects_left_and_right_associativity() -> None:
    def infix(tok: Any) -> InfixOp[str] | None:
        if tok.value == "+":
            return InfixOp(
                precedence=10,
                assoc="left",
                build=lambda left, right: f"({left}+{right})",
            )
        if tok.value == "^":
            return InfixOp(
                precedence=20,
                assoc="right",
                build=lambda left, right: f"({left}^{right})",
            )
        return None

    left = ExpressionRule(atom=_atom, infix_of=infix)
    assert left.parse(_stream("a", "+", "b", "+", "c"), 0) == ("((a+b)+c)", 5)

    right = ExpressionRule(atom=_atom, infix_of=infix)
    assert right.parse(_stream("a", "^", "b", "^", "c"), 0) == ("(a^(b^c))", 5)


def test_expression_rule_fails_for_missing_atom_or_rhs() -> None:
    expr = ExpressionRule(
        atom=_atom,
        infix_of=lambda tok: InfixOp(10, "left", lambda left, right: f"{left}+{right}")
        if tok.value == "+"
        else None,
    )

    assert expr.parse(_stream("+", "a"), 0) is None
    assert expr.parse(_stream("a", "+"), 0) is None


def test_parse_error_carries_location_and_message() -> None:
    err = ParseError("a +", 2, "expected atom")
    assert err.text == "a +"
    assert err.pos == 2
    assert err.message == "expected atom"
