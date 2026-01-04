from __future__ import annotations

import pytest
from proof_scaffold.dsl import MMBuilder
from proof_scaffold.ir import FloatingHyp, Origin, ProofUnitIR
from proof_scaffold.ir import (
    Theorem as LIRTheorem,
)
from proof_scaffold.linker.errors import LinkerDiagError
from proof_scaffold.linker_v0 import LinkerV0


@pytest.mark.adversarial
def test_adv_m12_missing_origin_rejected_stage0() -> None:
    # Construct a unit with a stmt missing origin
    u = ProofUnitIR(
        unit_id="adv.missing.origin",
        lir=[
            FloatingHyp(label="wph", typecode=0, var=1, origin=None),
        ],
        origin=Origin(file="adv.py", line=0),
        symtab=("wff", "ph"),
    )
    with pytest.raises(LinkerDiagError) as ei:
        LinkerV0().link([u])
    d = ei.value.diag
    assert d.error_code == "E_MISSING_ORIGIN"
    # Stage 0.5 must be present in the chain
    assert any(seg.startswith("Stage0.5") for seg in d.origin_chain)


@pytest.mark.adversarial
def test_adv_m12_forbid_raw_string_tokens_default_off() -> None:
    # Build a unit manually that sneaks a raw string into proof_tokens
    u = ProofUnitIR(
        unit_id="adv.raw.token",
        lir=[
            FloatingHyp(
                label="wph", typecode=0, var=1, origin=Origin(file="adv.py", line=1)
            ),
            LIRTheorem(
                label="t",
                typecode=0,
                expr=(1,),
                proof_tokens=("wph",),  # type: ignore[arg-type]
                origin=Origin(file="adv.py", line=2),
            ),
        ],
        origin=Origin(file="adv.py", line=0),
        symtab=("wff", "ph"),
    )
    with pytest.raises(LinkerDiagError) as ei:
        LinkerV0().link([u])
    assert ei.value.diag.error_code == "E_RAW_TOKEN_FORBIDDEN"


@pytest.mark.adversarial
def test_adv_m12_forbid_cross_unit_hyp_leakage() -> None:
    # Unit A exports only an axiom; it also has a floating hyp label wph
    ma = MMBuilder()
    ma.c("wff")
    ma.v("ph")
    ma.f("wph", "wff", "ph")
    with ma.block():
        ma.a("ax", "wff", ("ph",))
    ua = ma.to_proof_unit("unit.A")

    # Unit B tries to use A's $f label directly in a theorem
    ub = ProofUnitIR(
        unit_id="unit.B",
        lir=[
            FloatingHyp(
                label="wphB", typecode=0, var=1, origin=Origin(file="B.py", line=1)
            ),
            LIRTheorem(
                label="tb",
                typecode=0,
                expr=(1,),
                proof_tokens=(2,),  # refers to A's $f (by name via symtab)
                origin=Origin(file="B.py", line=2),
            ),
        ],
        origin=Origin(file="B.py", line=0),
        symtab=("wff", "ph", "wph"),
    )

    with pytest.raises(LinkerDiagError) as ei:
        LinkerV0().link([ua, ub])
    assert ei.value.diag.error_code == "E_CROSS_UNIT_HYP_LEAKAGE"


@pytest.mark.adversarial
def test_adv_m12_forbid_non_export_label_reference() -> None:
    # Unit A defines an axiom but marks no exports
    ma = MMBuilder()
    ma.c("wff")
    ma.v("ph")
    ma.f("wph", "wff", "ph")
    with ma.block():
        ma.a("ax", "wff", ("ph",))
    ua = ma.to_proof_unit("unit.A")
    # explicitly restrict exports to empty so ax is non-exported
    ua.exports = []

    # Unit B tries to use A.ax
    ub = ProofUnitIR(
        unit_id="unit.B",
        lir=[
            FloatingHyp(
                label="wphB", typecode=0, var=1, origin=Origin(file="B.py", line=1)
            ),
            LIRTheorem(
                label="tb",
                typecode=0,
                expr=(1,),
                proof_tokens=(2,),
                origin=Origin(file="B.py", line=2),
            ),
        ],
        origin=Origin(file="B.py", line=0),
        symtab=("wff", "ph", "ax"),
    )

    with pytest.raises(LinkerDiagError) as ei:
        LinkerV0().link([ua, ub])
    assert ei.value.diag.error_code == "E_NON_EXPORTED_LABEL_REF"
