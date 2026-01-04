from __future__ import annotations

import pytest
from proof_scaffold.ir import Axiom, Origin, ProofUnitIR
from proof_scaffold.linker.errors import LinkerDiagError
from proof_scaffold.linker_v0 import LinkerV0


def test_adv_m13_compat_hint_required_when_no_proof() -> None:
    # Interface-only style unit (no Theorem with proof tokens => no uses_assertions)
    o = Origin(module="test", file="compat.py", line=1)
    symtab = ("|-", "ph", "axA")
    ua = ProofUnitIR(
        unit_id="A",
        origin=o,
        symtab=symtab,
        lir=[Axiom(label="axA", typecode=0, expr=(1,), origin=o)],
        exports=["axA"],
    )

    with pytest.raises(LinkerDiagError) as ei:
        LinkerV0().link([ua], compat=True)
    assert ei.value.diag.error_code == "E_DEP_HINT_REQUIRED"


def test_adv_m13_compat_hint_incorrect_rejected() -> None:
    o = Origin(module="test", file="compat.py", line=1)
    symtab = ("|-", "ph", "axA")
    ua = ProofUnitIR(
        unit_id="A",
        origin=o,
        symtab=symtab,
        lir=[Axiom(label="axA", typecode=0, expr=(1,), origin=o)],
        exports=["axA"],
        dependencies_hint_unit_ids=["NO_SUCH_UNIT"],
    )

    with pytest.raises(LinkerDiagError) as ei:
        LinkerV0().link([ua], compat=True)
    assert ei.value.diag.error_code == "E_DEP_HINT_INVALID"
