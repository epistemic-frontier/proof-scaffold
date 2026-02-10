from __future__ import annotations

from typing import NamedTuple

from .dsl import DEFAULT_REQUIRE, Expr, RequireRegistry, Var
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
        
        if char == '(':
            self.pos += 1
            return Token("LPAREN", "(", self.pos - 1)
        if char == ')':
            self.pos += 1
            return Token("RPAREN", ")", self.pos - 1)
        
        # Read a "word" (contiguous non-space non-paren)
        start = self.pos
        while self.pos < self.len:
            c = self.text[self.pos]
            if c.isspace() or c in "()":
                break
            self.pos += 1
        
        value = self.text[start:self.pos]
        return Token("NAME", value, start)

# -----------------------------------------------------------------------------
# Parser
# -----------------------------------------------------------------------------

class Parser:
    def __init__(self, text: str, registry: RequireRegistry = DEFAULT_REQUIRE):
        self.tokenizer = Tokenizer(text)
        self.registry = registry
        self.current = self.tokenizer.next_token()

    def consume(self) -> Token:
        tok = self.current
        self.current = self.tokenizer.next_token()
        return tok

    def parse(self) -> Expr:
        expr = self.parse_expr(0)
        if self.current.type != "EOF":
            raise PreludeTypingError(
                _format_parse_error(
                    self.tokenizer.text,
                    self.current.pos,
                    f"Unexpected token at end: {self.current.value!r}",
                )
            )
        return expr

    def parse_expr(self, min_prec: int) -> Expr:
        left = self.parse_atom()

        while True:
            if self.current.type != "NAME":
                break
            
            op_name = self.current.value
            spec = self.registry._by_name.get(op_name)
            
            # If not a registered symbol, it's not an operator here (unless we support juxtaposition)
            if spec is None:
                break
            
            # Only infix operators (arity 2) handled here for now
            if spec.ctor.arity != 2:
                break
                
            prec = spec.precedence
            if prec < min_prec:
                break
            
            # Consume operator
            self.consume()
            
            # Associativity
            next_min = prec + 1 if spec.assoc == "left" else prec
            
            right = self.parse_expr(next_min)
            left = spec.ctor(left, right)
            
        return left

    def parse_atom(self) -> Expr:
        tok = self.consume()
        
        if tok.type == "LPAREN":
            expr = self.parse_expr(0)
            if self.current.type != "RPAREN":
                raise PreludeTypingError(
                    _format_parse_error(
                        self.tokenizer.text,
                        self.current.pos,
                        "Expected ')'",
                    )
                )
            self.consume()
            return expr
        
        if tok.type == "NAME":
            name = tok.value
            spec = self.registry._by_name.get(name)
            
            # Variable or 0-arity const
            if not spec:
                return Var(name)
            
            if spec.ctor.arity == 0:
                return spec.ctor()

            # Prefix operator (or function call style)
            # We treat any arity > 0 appearing in atom position as a prefix operator
            # consuming 'arity' arguments.
            prec = spec.precedence or 100
            args = []
            for _ in range(spec.ctor.arity):
                args.append(self.parse_expr(prec))
            return spec.ctor(*args)
            
        raise PreludeTypingError(
            _format_parse_error(
                self.tokenizer.text,
                tok.pos,
                f"Unexpected token: {tok.value!r}",
            )
        )

def wff(text: str, registry: RequireRegistry = DEFAULT_REQUIRE) -> Expr:
    """Parse a wff string into an Expr."""
    p = Parser(text, registry)
    return p.parse()
