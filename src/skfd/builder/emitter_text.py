# src/skfd/builder/emitter_text.py
from __future__ import annotations

from collections.abc import Sequence


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
    def open_scope(self) -> None:
        self._lines.append("${")

    def close_scope(self) -> None:
        self._lines.append("$}")

    # comments ------------------------------------------------------------
    def comment(self, text: str) -> None:
        t = _clean_comment_ascii(text) if self._ascii_comments else text
        self._lines.append(f"$( {t} $)")

    # decls ---------------------------------------------------------------
    def const_decl(self, symbols: Sequence[str]) -> None:
        self._lines.append(f"$c {' '.join(symbols)} $.")

    def var_decl(self, symbols: Sequence[str]) -> None:
        self._lines.append(f"$v {' '.join(symbols)} $.")

    # hyps/asserts --------------------------------------------------------
    def floating_hyp(
        self, label: str, typecode: str, var: str
    ) -> None:
        self._lines.append(f"{label} $f {typecode} {var} $.")

    def essential_hyp(
        self,
        label: str,
        typecode: str,
        expr_tokens: Sequence[str],
    ) -> None:
        self._lines.append(f"{label} $e {typecode} {' '.join(expr_tokens)} $.")

    def axiom(
        self,
        label: str,
        typecode: str,
        expr_tokens: Sequence[str],
    ) -> None:
        self._lines.append(f"{label} $a {typecode} {' '.join(expr_tokens)} $.")

    def theorem(
        self,
        label: str,
        typecode: str,
        expr_tokens: Sequence[str],
        proof_tokens: Sequence[str],
    ) -> None:
        self._lines.append(f"{label} $p {typecode} {' '.join(expr_tokens)} $=")
        self._lines.append(f"  {' '.join(proof_tokens)}")
        self._lines.append("$.")

    def render(self) -> str:
        return "\n".join(self._lines) + ("\n" if self._lines else "")
