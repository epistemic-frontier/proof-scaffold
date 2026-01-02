from __future__ import annotations

import pytest

from proof_scaffold.dsl import MMBuilder
from proof_scaffold.ir import (
    Axiom,
    ConstDecl,
    EssentialHyp,
    FloatingHyp,
    Origin,
    ProofUnitIR,
    ScopeEnter,
    ScopeExit,
    SymbolRef,
    VarDecl,
)
from proof_scaffold.ir import (
    Theorem as LIRTheorem,
)
from proof_scaffold.linker.errors import LinkerDiagError
from proof_scaffold.linker_v0 import LinkerV0

# D1. After Stage 1, there must be no string tokens anywhere; all tokens are SymbolRef

def _assert_no_string_tokens_in_lir(u: ProofUnitIR) -> None:
    for st in u.lir:
        if isinstance(st, ConstDecl):
            assert all(isinstance(s, SymbolRef) for s in st.symbols)
        elif isinstance(st, VarDecl):
            assert all(isinstance(s, SymbolRef) for s in st.symbols)
        elif isinstance(st, FloatingHyp):
            assert isinstance(st.typecode, SymbolRef)
            assert isinstance(st.var, SymbolRef)
        elif isinstance(st, EssentialHyp):
            assert isinstance(st.typecode, SymbolRef)
            assert all(isinstance(t, SymbolRef) for t in st.expr)
        elif isinstance(st, Axiom):
            assert isinstance(st.typecode, SymbolRef)
            assert all(isinstance(t, SymbolRef) for t in st.expr)
        elif isinstance(st, LIRTheorem):
            assert isinstance(st.typecode, SymbolRef)
            assert all(isinstance(t, SymbolRef) for t in st.expr)
            assert all(isinstance(tk, SymbolRef) for tk in st.proof_tokens)
        elif isinstance(st, (ScopeEnter, ScopeExit)):
            # structural, no tokens
            pass
        else:  # pragma: no cover - future proof if new LIRStmt types are added
            raise AssertionError(f"unexpected LIRStmt type in test: {type(st)}")


@pytest.mark.structural
def test_struct_m12_no_string_tokens_after_stage1() -> None:
    mm = MMBuilder()
    mm.c("wff", "(", ")", "->", "|-")
    mm.v("ph")
    mm.f("wph", "wff", "ph")
    with mm.block():
        mm.a("ax-id", "|-", ("(", "ph", "->", "ph", ")"))
        mm.p("t", "|-", ("(", "ph", "->", "ph", ")"), proof=["wph", "ax-id"])

    u = mm.to_proof_unit("struct.m12.stage1.tokens")

    # Link through Stage 1+ to ensure any raw token would be rejected before this point
    # If raw tokens exist, LinkerV0.link will raise E_RAW_TOKEN_FORBIDDEN in Stage 1.
    LinkerV0().link([u])

    # Structural assertion on IR payload (tokens are SymbolRef)
    _assert_no_string_tokens_in_lir(u)


# D2. Any Stage 1 error must include pass name and unit_id in origin_chain

@pytest.mark.structural
def test_struct_m12_origin_chain_contains_pass_and_unit() -> None:
    # Construct a unit that triggers a Stage 1 error (raw string in proof tokens)
    u = ProofUnitIR(
        unit_id="struct.m12.chain",
        lir=[
            FloatingHyp(label="wph", typecode=SymbolRef("wff"), var=SymbolRef("ph"), origin=Origin(file="chain.py", line=1)),
            LIRTheorem(
                label="bad",
                typecode=SymbolRef("wff"),
                expr=(SymbolRef("ph"),),
                proof_tokens=("wph",),  # type: ignore[arg-type]
                origin=Origin(file="chain.py", line=2),
            ),
        ],
        origin=Origin(file="chain.py", line=0),
    )

    with pytest.raises(LinkerDiagError) as ei:
        LinkerV0().link([u])

    d = ei.value.diag
    assert d.error_code == "E_RAW_TOKEN_FORBIDDEN"
    # chain should contain Stage1 and unit id
    assert any(seg == "Stage1" for seg in d.origin_chain)
    assert any(seg == f"unit={u.unit_id}" for seg in d.origin_chain)
