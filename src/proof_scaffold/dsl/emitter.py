# proof_scaffold/dsl/emitter.py
from __future__ import annotations

from collections.abc import Sequence

from ..ir import (
    Axiom as LIRAxiom,
)
from ..ir import (
    ConstDecl as LIRConstDecl,
)
from ..ir import (
    EssentialHyp as LIREssentialHyp,
)
from ..ir import (
    FloatingHyp as LIRFloatingHyp,
)
from ..ir import (
    LIRStmt,
    Origin,
)
from ..ir import (
    ScopeEnter as LIRScopeEnter,
)
from ..ir import (
    ScopeExit as LIRScopeExit,
)
from ..ir import (
    Theorem as LIRTheorem,
)
from ..ir import (
    VarDecl as LIRVarDecl,
)
from .types import _join_tokens


def _clean_comment_ascii(text: str) -> str:
    """
    Keep comments safe for strict tools:
    - strip Metamath comment delimiters
    - replace non-ascii chars with '?'
    """
    t = text.replace("$(", "").replace("$)", "")
    return "".join(ch if ord(ch) < 128 else "?" for ch in t)


class TextEmitter:
    def __init__(self, *, ascii_comments: bool = True) -> None:
        self._lines: list[str] = []
        self._ascii_comments = ascii_comments

    # scope ---------------------------------------------------------------
    def open_scope(self, origin: Origin | None = None) -> None:
        self._lines.append("${")

    def close_scope(self, origin: Origin | None = None) -> None:
        self._lines.append("$}")

    # comments ------------------------------------------------------------
    def comment(self, text: str, origin: Origin | None = None) -> None:
        t = _clean_comment_ascii(text) if self._ascii_comments else text
        self._lines.append(f"$( {t} $)")

    # decls ---------------------------------------------------------------
    def const_decl(self, symbols: Sequence[str], origin: Origin | None = None) -> None:
        self._lines.append(f"$c {_join_tokens(symbols)} $.")

    def var_decl(self, symbols: Sequence[str], origin: Origin | None = None) -> None:
        self._lines.append(f"$v {_join_tokens(symbols)} $.")

    # hyps/asserts --------------------------------------------------------
    def floating_hyp(self, label: str, typecode: str, var: str, origin: Origin | None = None) -> None:
        self._lines.append(f"{label} $f {typecode} {var} $.")

    def essential_hyp(self, label: str, typecode: str, expr_tokens: Sequence[str], origin: Origin | None = None) -> None:
        self._lines.append(f"{label} $e {typecode} {_join_tokens(expr_tokens)} $.")

    def axiom(self, label: str, typecode: str, expr_tokens: Sequence[str], origin: Origin | None = None) -> None:
        self._lines.append(f"{label} $a {typecode} {_join_tokens(expr_tokens)} $.")

    def theorem(self, label: str, typecode: str, expr_tokens: Sequence[str], proof_tokens: Sequence[str], origin: Origin | None = None) -> None:
        self._lines.append(f"{label} $p {typecode} {_join_tokens(expr_tokens)} $=")
        self._lines.append(f"  {_join_tokens(proof_tokens)}")
        self._lines.append("$.")

    def render(self) -> str:
        return "\n".join(self._lines) + ("\n" if self._lines else "")


class LIREmitter:
    def __init__(self) -> None:
        self._lir: list[LIRStmt] = []
        self._symtab: list[str] = []  # retained for debug/compat

    # scope ---------------------------------------------------------------
    def open_scope(self, origin: Origin | None = None) -> None:
        self._lir.append(LIRScopeEnter(origin=origin))

    def close_scope(self, origin: Origin | None = None) -> None:
        self._lir.append(LIRScopeExit(origin=origin))

    # comments: ignored in LIR -------------------------------------------
    def comment(self, text: str, origin: Origin | None = None) -> None:
        pass

    # decls ---------------------------------------------------------------
    def const_decl(self, symbols: Sequence[str], origin: Origin | None = None) -> None:
        from ..ir import SymbolRef
        self._lir.append(LIRConstDecl(tuple(SymbolRef(s) for s in symbols), origin=origin))

    def var_decl(self, symbols: Sequence[str], origin: Origin | None = None) -> None:
        from ..ir import SymbolRef
        self._lir.append(LIRVarDecl(tuple(SymbolRef(s) for s in symbols), origin=origin))

    # hyps/asserts --------------------------------------------------------
    def floating_hyp(self, label: str, typecode: str, var: str, origin: Origin | None = None) -> None:
        from ..ir import SymbolRef
        self._lir.append(LIRFloatingHyp(label=label, typecode=SymbolRef(typecode), var=SymbolRef(var), origin=origin))

    def essential_hyp(self, label: str, typecode: str, expr_tokens: Sequence[str], origin: Origin | None = None) -> None:
        from ..ir import SymbolRef
        self._lir.append(LIREssentialHyp(label=label, typecode=SymbolRef(typecode), expr=tuple(SymbolRef(t) for t in expr_tokens), origin=origin))

    def axiom(self, label: str, typecode: str, expr_tokens: Sequence[str], origin: Origin | None = None) -> None:
        from ..ir import SymbolRef
        self._lir.append(LIRAxiom(label=label, typecode=SymbolRef(typecode), expr=tuple(SymbolRef(t) for t in expr_tokens), origin=origin))

    def theorem(self, label: str, typecode: str, expr_tokens: Sequence[str], proof_tokens: Sequence[str], origin: Origin | None = None) -> None:
        from ..ir import SymbolRef
        self._lir.append(LIRTheorem(label=label, typecode=SymbolRef(typecode), expr=tuple(SymbolRef(t) for t in expr_tokens), proof_tokens=tuple(SymbolRef(t) for t in proof_tokens), origin=origin))

    def lir(self) -> list[LIRStmt]:
        return list(self._lir)

    def symtab(self) -> tuple[str, ...]:
        return tuple(self._symtab)





class CompositeEmitter:
    def __init__(self, text: TextEmitter, lir: LIREmitter) -> None:
        self.text = text
        self.lir = lir

    # Delegate all methods to both emitters --------------------------------
    def open_scope(self, origin: Origin | None = None) -> None:
        self.text.open_scope(origin)
        self.lir.open_scope(origin)

    def close_scope(self, origin: Origin | None = None) -> None:
        self.text.close_scope(origin)
        self.lir.close_scope(origin)

    def comment(self, text: str, origin: Origin | None = None) -> None:
        self.text.comment(text, origin)
        self.lir.comment(text, origin)

    def const_decl(self, symbols: Sequence[str], origin: Origin | None = None) -> None:
        self.text.const_decl(symbols, origin)
        self.lir.const_decl(symbols, origin)

    def var_decl(self, symbols: Sequence[str], origin: Origin | None = None) -> None:
        self.text.var_decl(symbols, origin)
        self.lir.var_decl(symbols, origin)

    def floating_hyp(self, label: str, typecode: str, var: str, origin: Origin | None = None) -> None:
        self.text.floating_hyp(label, typecode, var, origin)
        self.lir.floating_hyp(label, typecode, var, origin)

    def essential_hyp(self, label: str, typecode: str, expr_tokens: Sequence[str], origin: Origin | None = None) -> None:
        self.text.essential_hyp(label, typecode, expr_tokens, origin)
        self.lir.essential_hyp(label, typecode, expr_tokens, origin)

    def axiom(self, label: str, typecode: str, expr_tokens: Sequence[str], origin: Origin | None = None) -> None:
        self.text.axiom(label, typecode, expr_tokens, origin)
        self.lir.axiom(label, typecode, expr_tokens, origin)

    def theorem(self, label: str, typecode: str, expr_tokens: Sequence[str], proof_tokens: Sequence[str], origin: Origin | None = None) -> None:
        self.text.theorem(label, typecode, expr_tokens, proof_tokens, origin)
        self.lir.theorem(label, typecode, expr_tokens, proof_tokens, origin)

    # convenience accessors -------------------------------------------------
    def render_text(self) -> str:
        return self.text.render()

    def lir_list(self) -> list[LIRStmt]:
        return self.lir.lir()

    def symtab(self) -> tuple[str, ...]:
        return self.lir.symtab()
