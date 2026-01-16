from __future__ import annotations

import pytest
from skfd.core.diag import LinkerDiagError
from skfd.core.lir import Axiom, ConstDecl, Theorem
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.api import LinkerV1


def _build_failing_units() -> tuple[list[ProofUnitIR], OriginTable, SymbolInterner]:
    # Reuse setup from P0-3 (Export Consistency Failure)
    ot = OriginTable()
    interner = SymbolInterner()

    # Shared types
    S_wff = 1

    # Define Unit A
    u1 = ProofUnitIR(
        unit_id="unitA",
        origin_ref=100,  # File A
        origin_module_id="modA",
        lir_stmts=[
            Axiom(1, 100, 10, S_wff, []),
        ],
        exports=[10]
    )
    
    # Define Unit B (Duplicate Label 10)
    u2 = ProofUnitIR(
        unit_id="unitB",
        origin_ref=200,  # File B
        origin_module_id="modB",
        lir_stmts=[
             ConstDecl(2, 200, [S_wff]),
             Theorem(3, 200, 10, S_wff, [], []), # distinct stmt_id, same label 10
        ],
        exports=[10]
    )
    return [u1, u2], ot, interner


@pytest.mark.adversarial
def test_adv_p0_6_diag_determinism() -> None:
    """ADV-P0-6: Diagnostics details are observable and deterministic.

    Trigger a diagnostic twice.
    Expect identical string representation (implies sorted keys/sets).
    """

    # Run 1
    u1, ot1, i1 = _build_failing_units()
    err1 = None
    try:
        LinkerV1.link(units=u1, origin_table=ot1, interner=i1)
    except LinkerDiagError as e:
        err1 = str(e)

    assert err1 is not None, "Expected LinkerDiagError in run 1"

    # Run 2
    u2, ot2, i2 = _build_failing_units()
    err2 = None
    try:
        LinkerV1.link(units=u2, origin_table=ot2, interner=i2)
    except LinkerDiagError as e:
        err2 = str(e)

    assert err2 is not None, "Expected LinkerDiagError in run 2"

    # Compare
    assert err1 == err2, (
        "Diagnostics must be deterministic.\n" f"Run 1: {err1!r}\n" f"Run 2: {err2!r}"
    )
