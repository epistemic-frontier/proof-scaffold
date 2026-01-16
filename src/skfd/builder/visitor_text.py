# skfd/builder/visitor_text.py
from __future__ import annotations

from collections.abc import Sequence

from skfd.core.origin import OriginRef
from skfd.core.symbols import SymbolId

from .visitor import BuilderVisitor


def _clean_comment_ascii(text: str) -> str:
    """
    Keep comments safe for strict tools:
    - strip Metamath comment delimiters
    - replace non-ascii chars with '?'
    """
    t = text.replace("$(", "").replace("$)", "")
    return "".join(ch if ord(ch) < 128 else "?" for ch in t)


class TextVisitor(BuilderVisitor):
    def __init__(self, *, ascii_comments: bool = True) -> None:
        self._lines: list[str] = []
        self._ascii_comments = ascii_comments

    # scope ---------------------------------------------------------------
    def open_scope(self, origin_ref: OriginRef) -> None:
        self._lines.append("${")

    def close_scope(self, origin_ref: OriginRef) -> None:
        self._lines.append("$}")

    # comments ------------------------------------------------------------
    def comment(self, text: str, origin_ref: OriginRef) -> None:
        t = _clean_comment_ascii(text) if self._ascii_comments else text
        self._lines.append(f"$( {t} $)")

    # decls ---------------------------------------------------------------
    def const_decl(
        self, symbols: Sequence[str], ids: Sequence[SymbolId], origin_ref: OriginRef
    ) -> None:
        self._lines.append(f"$c {' '.join(symbols)} $.")

    def var_decl(
        self, symbols: Sequence[str], ids: Sequence[SymbolId], origin_ref: OriginRef
    ) -> None:
        self._lines.append(f"$v {' '.join(symbols)} $.")

    # hyps/asserts --------------------------------------------------------
    def floating_hyp(
        self,
        label_s: str,
        typecode_s: str,
        var_s: str,
        label_id: SymbolId,
        typecode_id: SymbolId,
        var_id: SymbolId,
        origin_ref: OriginRef,
    ) -> None:
        self._lines.append(f"{label_s} $f {typecode_s} {var_s} $.")

    def essential_hyp(
        self,
        label_s: str,
        typecode_s: str,
        expr_s: Sequence[str],
        label_id: SymbolId,
        typecode_id: SymbolId, 
        expr_id: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None:
        self._lines.append(f"{label_s} $e {typecode_s} {' '.join(expr_s)} $.")

    def axiom(
        self,
        label_s: str,
        typecode_s: str,
        expr_s: Sequence[str],
        label_id: SymbolId,
        typecode_id: SymbolId,
        expr_id: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None:
        self._lines.append(f"{label_s} $a {typecode_s} {' '.join(expr_s)} $.")

    def theorem(
        self,
        label_s: str,
        typecode_s: str,
        expr_s: Sequence[str],
        proof_s: Sequence[str],
        label_id: SymbolId,
        typecode_id: SymbolId,
        expr_id: Sequence[SymbolId],
        proof_id: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None:
        self._lines.append(f"{label_s} $p {typecode_s} {' '.join(expr_s)} $=")
        self._lines.append(f"  {' '.join(proof_s)}")
        self._lines.append("$.")

    def disjoint_var(
        self,
        vars_s: Sequence[str],
        vars_id: Sequence[SymbolId],
        origin_ref: OriginRef,
    ) -> None:
        self._lines.append(f"$d {' '.join(vars_s)} $.")

    def render(self) -> str:
        return "\n".join(self._lines) + ("\n" if self._lines else "")
