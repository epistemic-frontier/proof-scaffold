from __future__ import annotations

import pytest
from skfd.core.diag import LinkerDiagError
from skfd.core.lir import Axiom, ScopeEnter, ScopeExit, Theorem
from skfd.core.origin import OriginRecord, OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.api import LinkerV1


@pytest.mark.adversarial
def test_adv_p0_3_export_consistency() -> None:
    """ADV-P0-3: Export-aware resolution consistency.

    Referencing a non-exported label from another unit implies
    a violation of the interface contract. The linker must reject it.
    """
    ot = OriginTable()
    interner = SymbolInterner()

    orig_a = ot.intern(OriginRecord(module_id="A", file="a.py", line=1))
    orig_b = ot.intern(OriginRecord(module_id="B", file="b.py", line=1))

    tc_wff = interner.intern(
        origin_module_id="prelude", local_name="wff", kind="Const", origin_ref=orig_a
    )

    # Unit A: defines axiom "ax-private" but DOES NOT export it
    ax_priv = interner.intern(
        origin_module_id="A", local_name="ax-private", kind="Label", origin_ref=orig_a
    )
    unit_a = ProofUnitIR(
        unit_id="A:unit",
        origin_ref=orig_a,
        origin_module_id="A",
        lir_stmts=[
            Axiom(
                label=ax_priv, typecode=tc_wff, expr=[], stmt_id=1, origin_ref=orig_a
            ),
            ScopeEnter(stmt_id=2, origin_ref=orig_a),
            ScopeExit(stmt_id=3, origin_ref=orig_a),
        ],
        exports=[],  # Empty!
    )

    # Unit B: tries to use "ax-private"
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
                expr=[],
                proof=[ax_priv],  # Illegal usage of private symbol
                stmt_id=1,
                origin_ref=orig_b,
            ),
            ScopeEnter(stmt_id=2, origin_ref=orig_b),
            ScopeExit(stmt_id=3, origin_ref=orig_b),
        ],
        exports=[th_1],
    )

    # Expect Failure
    with pytest.raises(LinkerDiagError) as excinfo:
        LinkerV1.link(
            units=[unit_a, unit_b], origin_table=ot, interner=interner, conformance_level=1
        )

    e = excinfo.value
    # Check for specific error code (e.g. E_SYMBOL_NOT_EXPORTED)
    # Since we haven't implemented it yet, we just check specifically that it fails.
    # But ideally it should be a meaningful error.
    assert e.diag.error_code in (
        "E_SYMBOL_NOT_EXPORTED",
        "E_ACCESS_CONTROL",
    ), f"Unexpected error code: {e.diag.error_code}"
