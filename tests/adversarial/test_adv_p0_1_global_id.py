from __future__ import annotations

import pytest
from skfd.core.origin import OriginRecord, OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.core.lir import ConstDecl, ScopeEnter, ScopeExit
from skfd.linker.api import LinkerV1

@pytest.mark.adversarial
def test_adv_p0_1_global_id_relocation() -> None:
    """ADV-P0-1: Global SymbolId space prevents token-relocation collision.
    
    Two units declare local symbols with the same local name. 
    The linker must emit them as distinct tokens.
    """
    ot = OriginTable()
    interner = SymbolInterner()

    # Unit A defines const "c"
    orig_a = ot.intern(OriginRecord(module_id="A", file="a.py", line=1))
    c_a = interner.intern(
        origin_module_id="A", 
        local_name="c", 
        kind="Const", 
        origin_ref=orig_a
    )
    unit_a = ProofUnitIR(
        unit_id="A:unit",
        origin_ref=orig_a,
        origin_module_id="A",
        lir_stmts=[
            ConstDecl(tokens=(c_a,), stmt_id=1, origin_ref=orig_a),
            ScopeEnter(stmt_id=2, origin_ref=orig_a),
            ScopeExit(stmt_id=3, origin_ref=orig_a),
        ],
        exports=[],
    )

    # Unit B defines const "c" (different origin, different ID)
    orig_b = ot.intern(OriginRecord(module_id="B", file="b.py", line=1))
    c_b = interner.intern(
        origin_module_id="B", 
        local_name="c", 
        kind="Const", 
        origin_ref=orig_b
    )
    unit_b = ProofUnitIR(
        unit_id="B:unit",
        origin_ref=orig_b,
        origin_module_id="B",
        lir_stmts=[
            ConstDecl(tokens=(c_b,), stmt_id=1, origin_ref=orig_b),
            ScopeEnter(stmt_id=2, origin_ref=orig_b),
            ScopeExit(stmt_id=3, origin_ref=orig_b),
        ],
        exports=[],
    )

    assert c_a != c_b, "Interner must assign distinct IDs for different origins"

    # Execution: Link [A, B]
    res = LinkerV1.link(units=[unit_a, unit_b], origin_table=ot, interner=interner)
    mm = res.mm_text

    # Extract $c declaration line
    # Should look like "$c c c0 $." or similar, NOT "$c c c $."
    
    # Simple parsing to check for duplicates in $c
    c_lines = [line for line in mm.splitlines() if line.startswith("$c")]
    assert len(c_lines) == 1
    content = c_lines[0].strip()[3:-3] # remove "$c " and " $."
    tokens = content.split()
    
    assert len(tokens) == 2, f"Expected 2 constants emitted, got {len(tokens)}: {tokens}"
    assert len(set(tokens)) == 2, f"Collision detected! Emitted tokens: {tokens}"
