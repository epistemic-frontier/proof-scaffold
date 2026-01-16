from __future__ import annotations

import pytest
from skfd.core.origin import OriginRecord, OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.core.lir import Axiom, Theorem, ScopeEnter, ScopeExit
from skfd.core.diag import LinkerDiagError
from skfd.linker.api import LinkerV1

def _build_failing_units() -> tuple[list[ProofUnitIR], OriginTable, SymbolInterner]:
    # Reuse setup from P0-3 (Export Consistency Failure)
    ot = OriginTable()
    interner = SymbolInterner()

    orig_a = ot.intern(OriginRecord(module_id="A", file="a.py", line=1))
    orig_b = ot.intern(OriginRecord(module_id="B", file="b.py", line=1))
    
    tc_wff = interner.intern(
        origin_module_id="prelude", local_name="wff", kind="Const", origin_ref=orig_a
    )

    ax_priv = interner.intern(
        origin_module_id="A", local_name="ax-private", kind="Label", origin_ref=orig_a
    )
    unit_a = ProofUnitIR(
        unit_id="A:unit",
        origin_ref=orig_a,
        origin_module_id="A",
        lir_stmts=[
            Axiom(label=ax_priv, typecode=tc_wff, expr=(), stmt_id=1, origin_ref=orig_a),
            ScopeEnter(stmt_id=2, origin_ref=orig_a),
            ScopeExit(stmt_id=3, origin_ref=orig_a),
        ],
        exports=[], 
    )

    th_1 = interner.intern(
        origin_module_id="B", local_name="th-1", kind="Label", origin_ref=orig_b
    )
    unit_b = ProofUnitIR(
        unit_id="B:unit",
        origin_ref=orig_b,
        origin_module_id="B",
        lir_stmts=[
            Theorem(
                label=th_1, 
                typecode=tc_wff, 
                expr=(), 
                proof=(ax_priv,), 
                stmt_id=1, 
                origin_ref=orig_b
            ),
            ScopeEnter(stmt_id=2, origin_ref=orig_b),
            ScopeExit(stmt_id=3, origin_ref=orig_b),
        ],
        exports=[th_1],
    )
    return [unit_a, unit_b], ot, interner


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
        "Diagnostics must be deterministic.\n"
        f"Run 1: {err1!r}\n"
        f"Run 2: {err2!r}"
    )
