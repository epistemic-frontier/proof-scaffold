from __future__ import annotations

from skfd.core.lir import (
    Axiom,
    ConstDecl,
    FloatingHyp,
    ScopeEnter,
    ScopeExit,
    Theorem,
    VarDecl,
)
from skfd.core.origin import OriginRecord, OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.emit.emit_mm import emit_mm
from skfd.linker.passes.stage5_scope import run as stage5


def test_golden_scope_planning_determinism() -> None:
    """
    Verify that Stage 5 + Stage 7 pipeline produces deterministic output
    that matches a known 'golden' string for a complex unit.
    Also ensures that the new pipeline (stage5 -> emit_mm) works as expected.
    """
    ot = OriginTable()
    interner = SymbolInterner()

    # 1. Setup a "Complex" Unit with global deps, local hyps, and structure.
    orig = ot.intern(OriginRecord(module_id="gold", file="gold.py", line=1))

    # Globals (Consts) defined in unit (implicit)
    c_wff = interner.intern(
        origin_module_id="gold", local_name="wff", kind="Const", origin_ref=orig
    )
    c_term = interner.intern(
        origin_module_id="gold", local_name="term", kind="Const", origin_ref=orig
    )

    # Variables
    v_ph = interner.intern(
        origin_module_id="gold", local_name="ph", kind="Var", origin_ref=orig
    )

    # Labels
    l_wffph = interner.intern(
        origin_module_id="gold", local_name="wffph", kind="Label", origin_ref=orig
    )
    l_ax1 = interner.intern(
        origin_module_id="gold", local_name="ax1", kind="Label", origin_ref=orig
    )
    l_th1 = interner.intern(
        origin_module_id="gold", local_name="th1", kind="Label", origin_ref=orig
    )

    unit = ProofUnitIR(
        unit_id="gold:unit",
        origin_ref=orig,
        origin_module_id="gold",
        lir_stmts=[
            # Declarations (Stage 5 should hoist these to header)
            ConstDecl(tokens=[c_wff, c_term], stmt_id=1, origin_ref=orig),
            VarDecl(tokens=[v_ph], stmt_id=2, origin_ref=orig),
            # Body content
            ScopeEnter(stmt_id=3, origin_ref=orig),
            FloatingHyp(
                label=l_wffph, typecode=c_wff, var=v_ph, stmt_id=4, origin_ref=orig
            ),
            Axiom(
                label=l_ax1, typecode=c_wff, expr=[v_ph], stmt_id=5, origin_ref=orig
            ),
            Theorem(
                label=l_th1,
                typecode=c_wff,
                expr=[v_ph],
                proof=[l_ax1],
                stmt_id=6,
                origin_ref=orig,
            ),
            ScopeExit(stmt_id=7, origin_ref=orig),
        ],
        exports=[l_ax1, l_th1],
    )

    # 2. Run Pipeline manually
    # We simulate what LinkerV1.link does internally

    # Context
    symtab = interner.symbol_table()

    # Stage 5: Planning
    # Note: Linker passes usually run on resolved list[Unit]
    plan = stage5([unit], symtab)

    # Stage 7: Emission
    output = emit_mm(symtab=symtab, plan=plan)

    # 3. Validation
    # We expect:
    # 1. Header with $c wff term $. and $v ph $. (Order deterministic by ID)
    # 2. Body with local floating hyp and assertions.

    # Note: order of $c depends on SymbolId order.
    # Since we interned wff then term, ids are wff=0, term=1?
    # No, intern("gold", "wff") -> 0, intern("gold", "term") -> 1.
    # But wait, python sets/dicts preserve insertion order?
    # Spec says sorted by SymbolId.
    # SymbolId is int. So wff (0) comes before term (1)?
    # ACTUALLY, I interned 'wff' first, then 'term'.
    # So wff < term.
    # Let's check my expected string: "$c term wff $."
    # Wait, 'term' comes AFTER 'wff' alphabetically, but alphabetical order doesn't matter for IDs.
    # Implementation of stage5_scope:
    # sorted_syms = sorted(..., key=lambda x: x[0])  <-- sorts by SymbolId
    # So if wff is ID 0 and term is ID 1, output should be "$c wff term $."

    # Let's try to match exactly what will happen.
    # IDs are likely monotonic.
    # wff: 0
    # term: 1
    # ph: 2
    # wffph: 3
    # ax1: 4
    # th1: 5

    # So header: $c wff term $.

    expected_corrected = """$c wff term $.
$v ph $.
${
wffph $f wff ph $.
ax1 $a wff ph $.
th1 $p wff ph $=
  ax1
$.
$}
"""

    assert (
        output == expected_corrected
    ), f"Output mismatch!\nGot:\n{output}\nExpected:\n{expected_corrected}"
