from __future__ import annotations

import pytest
from skfd.core.lir import Axiom, ScopeEnter, ScopeExit, Theorem
from skfd.core.origin import OriginRecord, OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.api import LinkerV1


@pytest.mark.adversarial
def test_adv_p0_2_closure_order_invariance() -> None:
    """ADV-P0-2: Closure computation is order-invariant.

    If Unit B depends on Unit A, but input is [B, A],
    the linker must topologically sort them to [A, B].
    """
    ot = OriginTable()
    interner = SymbolInterner()

    # Shared types (assumed pre-interned/available for simplicity in LIR)
    # For this test, we skip defining proper wffs/types to keep it minimal,
    # focusing on PROOF TOKEN dependency.
    # We use a dummy typecode "wff" (Const).

    orig_a = ot.intern(OriginRecord(module_id="A", file="a.py", line=1))
    orig_b = ot.intern(OriginRecord(module_id="B", file="b.py", line=1))

    tc_wff = interner.intern(
        origin_module_id="prelude", local_name="wff", kind="Const", origin_ref=orig_a
    )

    # Unit A: exports axiom "ax-1"
    ax_1 = interner.intern(
        origin_module_id="A", local_name="ax-1", kind="Label", origin_ref=orig_a
    )
    unit_a = ProofUnitIR(
        unit_id="A:unit",
        origin_ref=orig_a,
        origin_module_id="A",
        lir_stmts=[
            Axiom(label=ax_1, typecode=tc_wff, expr=[], stmt_id=1, origin_ref=orig_a),
            ScopeEnter(stmt_id=2, origin_ref=orig_a),
            ScopeExit(stmt_id=3, origin_ref=orig_a),
        ],
        exports=[ax_1],
    )

    # Unit B: theorem "th-1" proof uses "ax-1"
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
                proof=[ax_1],  # Dependency!
                stmt_id=1,
                origin_ref=orig_b,
            ),
            ScopeEnter(stmt_id=2, origin_ref=orig_b),
            ScopeExit(stmt_id=3, origin_ref=orig_b),
        ],
        exports=[th_1],
    )

    # Execution: Link [B, A] (Reverse topological order)
    res = LinkerV1.link(units=[unit_b, unit_a], origin_table=ot, interner=interner)
    mm = res.mm_text

    # Expect topological order: A must be emitted before B
    # We check the order of appearance of labels "$a ax-1" and "$p th-1"

    idx_a = mm.find("ax-1 $a")
    idx_b = mm.find("th-1 $p")

    assert idx_a != -1, "ax-1 not found in output"
    assert idx_b != -1, "th-1 not found in output"
    assert (
        idx_a < idx_b
    ), f"Expected A before B, but got indices A={idx_a}, B={idx_b}\nOutput:\n{mm}"
