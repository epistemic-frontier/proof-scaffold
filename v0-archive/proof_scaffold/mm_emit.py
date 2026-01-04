# scaffold/mm_emit.py

from __future__ import annotations

from collections.abc import Iterable


def emit_p_block(
    label: str,
    stmt: str,
    proof_labels: Iterable[str],
    *,
    comment: str | None = None,
) -> str:
    """
    Emit an uncompressed Metamath `$p` block.

    Parameters
    ----------
    label:
        The theorem label (e.g. "sanity.00").
    stmt:
        The statement, without `$=` (e.g. "|- ( ph -> ph )").
    proof_labels:
        Sequence of proof labels (RPN / stack-program form).
    comment:
        Optional Metamath comment inserted immediately above the block.

    Returns
    -------
    A string containing a complete `$p ... $= ... $.` block.
    """
    proof_body = "\n  ".join(proof_labels)

    cmt = ""
    if comment:
        # Keep comments short; this is for traceability, not documentation.
        cmt = f"\n$( {comment} $)\n"

    return f"""{cmt}{label} $p {stmt} $=
  {proof_body}
$.
"""


def append_p_block(
    mm_src: str,
    label: str,
    stmt: str,
    proof_labels: Iterable[str],
    *,
    comment: str | None = None,
) -> str:
    """
    Append a `$p` block to an existing Metamath database text.
    """
    return mm_src + "\n" + emit_p_block(label, stmt, proof_labels, comment=comment)
