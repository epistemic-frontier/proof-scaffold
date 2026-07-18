from __future__ import annotations

from typing import NamedTuple

from skfd.core.peg import (
    Assoc,
    ExpressionRule,
    InfixOp,
    ParseError,
    TokenLike,
    TokenStream,
)

from .dsl import App, DEFAULT_REQUIRE, Expr, RequireRegistry, Var
from .typing import PreludeTypingError

# -----------------------------------------------------------------------------
# Error formatting
# -----------------------------------------------------------------------------


def _format_parse_error(text: str, pos: int, message: str) -> str:
    safe_pos = max(0, min(pos, len(text)))
    caret_line = " " * safe_pos + "^"
    return f"{message}\n{text}\n{caret_line}"


# -----------------------------------------------------------------------------
# Tokenizer
# -----------------------------------------------------------------------------


class Token(NamedTuple):
    type: str
    value: str
    pos: int


class Tokenizer:
    # Simple regex for symbols, words, parens.
    # We want to match "→", "¬", etc. as NAMEs if they are symbols.
    # \w+ matches words. But "→" is not \w in ASCII re unless we use unicode flags.
    # We'll just match non-whitespace chunks.

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.len = len(text)

    def next_token(self) -> Token:
        # Skip whitespace
        while self.pos < self.len and self.text[self.pos].isspace():
            self.pos += 1

        if self.pos >= self.len:
            return Token("EOF", "", self.pos)

        char = self.text[self.pos]

        if char == "(":
            self.pos += 1
            return Token("LPAREN", "(", self.pos - 1)
        if char == ")":
            self.pos += 1
            return Token("RPAREN", ")", self.pos - 1)

        # Read a "word" (contiguous non-space non-paren)
        start = self.pos
        while self.pos < self.len:
            c = self.text[self.pos]
            if c.isspace() or c in "()":
                break
            self.pos += 1

        value = self.text[start : self.pos]
        return Token("NAME", value, start)


# -----------------------------------------------------------------------------
# Parser
# -----------------------------------------------------------------------------


class Parser:
    def __init__(self, text: str, registry: RequireRegistry = DEFAULT_REQUIRE):
        self.text = text
        self.registry = registry
        tok = Tokenizer(text)
        tokens: list[TokenLike] = []
        while True:
            t = tok.next_token()
            tokens.append(t)
            if t.type == "EOF":
                break
        self.stream: TokenStream = TokenStream(text=text, tokens=tokens)

        def infix_of(t: TokenLike) -> InfixOp[Expr] | None:
            if t.type != "NAME":
                return None
            spec = self.registry.spec_named(t.value, arity=2)
            if spec is None:
                return None
            assoc: Assoc = spec.assoc
            ctor = spec.ctor

            def build(left: Expr, right: Expr) -> Expr:
                return ctor(left, right)

            return InfixOp(
                precedence=spec.precedence,
                assoc=assoc,
                build=build,
            )

        self._expr = ExpressionRule(atom=self._atom, infix_of=infix_of)

    def parse(self) -> Expr:
        try:
            out = self._expr.parse(self.stream, 0)
            if out is None:
                raise ParseError(self.text, 0, "Expected expression")
            expr, i = out
            tail = self.stream.peek(i)
            if tail.type != "EOF":
                raise ParseError(
                    self.text, tail.pos, f"Unexpected token at end: {tail.value!r}"
                )
            return self._collapse_ternary(expr, 0, i)
        except ParseError as e:
            raise PreludeTypingError(
                _format_parse_error(e.text, e.pos, e.message)
            ) from e

    def _collapse_ternary(self, expr: Expr, start: int, end: int) -> Expr:
        top_level_ops: list[str] = []
        depth = 0
        for pos in range(start, end):
            token = self.stream.peek(pos)
            if token.type == "LPAREN":
                depth += 1
            elif token.type == "RPAREN":
                depth -= 1
            elif token.type == "NAME" and depth == 0:
                spec = self.registry.spec_named(token.value, arity=2)
                if (
                    spec is not None
                    and spec.ctor.arity == 2
                    and isinstance(expr, App)
                    and spec.ctor.name == expr.ctor.name
                ):
                    top_level_ops.append(spec.ctor.name)
        if (
            len(top_level_ops) == 2
            and top_level_ops[0] == top_level_ops[1]
            and isinstance(expr, App)
            and len(expr.args) == 2
            and isinstance(expr.args[0], App)
            and len(expr.args[0].args) == 2
            and expr.ctor.name == top_level_ops[0]
            and expr.args[0].ctor.name == top_level_ops[0]
        ):
            ternary_spec = self.registry.spec_named(top_level_ops[0], arity=3)
            if ternary_spec is not None:
                return ternary_spec.ctor(
                    expr.args[0].args[0], expr.args[0].args[1], expr.args[1]
                )
        return expr

    def _atom(self, s: TokenStream, i: int) -> tuple[Expr, int] | None:
        tok = s.peek(i)
        if tok.type == "LPAREN":
            inner = self._expr.parse(s, i + 1)
            if inner is None:
                raise ParseError(self.text, tok.pos, "Expected expression")
            expr, j = inner
            close = s.peek(j)
            if close.type != "RPAREN":
                raise ParseError(self.text, close.pos, "Expected ')'")
            return self._collapse_ternary(expr, i + 1, j), j + 1

        if tok.type == "NAME":
            spec = self.registry.spec_named(tok.value)
            if spec is None:
                return Var(tok.value), i + 1
            if spec.ctor.arity == 0:
                return spec.ctor(), i + 1
            if spec.ctor.name == "[" and spec.ctor.arity == 3:
                prec = spec.precedence if spec.precedence > 0 else 100
                term_out = self._expr.parse(s, i + 1)
                if term_out is not None:
                    term, j = term_out
                    slash = s.peek(j)
                    if slash.type == "NAME" and slash.value == "/":
                        variable_out = self._expr.parse(s, j + 1)
                        if variable_out is None:
                            raise ParseError(
                                self.text, slash.pos + 1, "Expected variable"
                            )
                        variable, j = variable_out
                        close = s.peek(j)
                        if close.type != "NAME" or close.value != "]":
                            raise ParseError(self.text, close.pos, "Expected ']'")
                        body_out = self._expr._parse_min(s, j + 1, prec)
                        if body_out is None:
                            bad = s.peek(j + 1)
                            raise ParseError(
                                self.text, bad.pos, "Expected substitution body"
                            )
                        body, j = body_out
                        return spec.ctor(term, variable, body), j
            prec = spec.precedence if spec.precedence > 0 else 100
            args: list[Expr] = []
            j = i + 1
            for arg_index in range(spec.ctor.arity):
                # A multi-argument prefix constructor must not consume another
                # occurrence of itself as an infix operator while parsing an
                # early argument. The final argument keeps the constructor's
                # precedence so right-associated binders such as
                # ``A. x A. y ph`` nest in the body.
                arg_prec = prec + 1 if arg_index < spec.ctor.arity - 1 else prec
                arg_out = self._expr._parse_min(s, j, arg_prec)
                if arg_out is None:
                    bad = s.peek(j)
                    raise ParseError(self.text, bad.pos, "Expected expression")
                arg, j = arg_out
                args.append(arg)
            return spec.ctor(*args), j

        if tok.type == "EOF":
            return None

        raise ParseError(self.text, tok.pos, f"Unexpected token: {tok.value!r}")


def wff(text: str, registry: RequireRegistry = DEFAULT_REQUIRE) -> Expr:
    """Parse a wff string into an Expr."""
    p = Parser(text, registry)
    return p.parse()
