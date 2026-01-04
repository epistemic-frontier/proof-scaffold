from __future__ import annotations

from pathlib import Path

import pytest
from proof_scaffold.dsl import MMBuilder
from proof_scaffold.ir import (
    Axiom,
    ConstDecl,
    EssentialHyp,
    FloatingHyp,
    ProofUnitIR,
    ScopeEnter,
    ScopeExit,
    VarDecl,
)
from proof_scaffold.ir import (
    Theorem as LIRTheorem,
)
from proof_scaffold.linker_v0 import LinkerV0

from tests._sanity_utils import verify_expect_ok


def _assert_no_string_tokens_in_lir(u: ProofUnitIR) -> None:
    for st in u.lir:
        if isinstance(st, ConstDecl):
            assert all(isinstance(s, int) for s in st.symbols)
        elif isinstance(st, VarDecl):
            assert all(isinstance(s, int) for s in st.symbols)
        elif isinstance(st, FloatingHyp):
            assert isinstance(st.typecode, int)
            assert isinstance(st.var, int)
        elif isinstance(st, EssentialHyp):
            assert isinstance(st.typecode, int)
            assert all(isinstance(t, int) for t in st.expr)
        elif isinstance(st, Axiom):
            assert isinstance(st.typecode, int)
            assert all(isinstance(t, int) for t in st.expr)
        elif isinstance(st, LIRTheorem):
            assert isinstance(st.typecode, int)
            assert all(isinstance(t, int) for t in st.expr)
            assert all(isinstance(tk, int) for tk in st.proof_tokens)
        elif isinstance(st, (ScopeEnter, ScopeExit)):
            # structural, no tokens
            pass
        else:  # pragma: no cover - future proof if new LIRStmt types are added
            raise AssertionError(f"unexpected LIRStmt type in test: {type(st)}")


def _write(tmp_path: Path, mm_src: str) -> Path:
    p = tmp_path / "linked.mm"
    p.write_text(mm_src, encoding="utf-8")
    return p


@pytest.mark.sanity
def test_sanity_m12_symbol_resolution_smoke(tmp_path: Path) -> None:
    """
    A1. Minimal single-unit IR -> Stage 1 via LinkerV0 -> emit & verify.
    Assertions:
      - LIR contains no raw string tokens (all are int ids)
      - Link succeeds and produces a verifiable Metamath file
    """
    mm = MMBuilder()
    mm.c("wff", "(", ")", "->", "|-")
    mm.v("ph")
    mm.f("wph", "wff", "ph")
    mm.a("ax-id", "|-", ("(", "ph", "->", "ph", ")"))
    with mm.block():
        mm.p("t", "|-", ("(", "ph", "->", "ph", ")"), proof=["wph", "ax-id"])

    u = mm.to_proof_unit("sanity.m12.smoke")

    # Structural assertion: all tokens are int ids (no raw strings)
    _assert_no_string_tokens_in_lir(u)

    # Link & verify
    mm_src = LinkerV0().link([u])
    verify_expect_ok(_write(tmp_path, mm_src))
