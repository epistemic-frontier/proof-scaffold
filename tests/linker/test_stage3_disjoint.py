
from skfd.core.contracts import AssertionContract
from skfd.core.lir import Axiom, DisjointVar, ScopeEnter, ScopeExit, Theorem
from skfd.core.symbols import SymbolDef
from skfd.core.unit import ProofUnitIR
from skfd.linker.passes.stage2_contracts import ContractIndex
from skfd.linker.passes.stage3_disjoint import run as stage3_run

def test_stage3_disjoint_extraction():
    # Setup
    symtab = {}
    
    # Create valid contracts for the assertions (normally done by Stage 2)
    contracts = ContractIndex(
        contracts={
            "ax1": AssertionContract("ax1", [], []),
            "th1": AssertionContract("th1", [], []),
        },
        details={}
    )
    
    # Construct a unit with scopes and $d statements
    # Scope 0:
    #   $d x y
    #   ax1
    #   Scope 1:
    #      $d x z
    #      th1
    #   Scope 1 Exit (th1 should see {x,y}, {x,z})
    #   $d a b
    #   (nothing uses a, b)
    
    # We cheat symbol IDs as strings for this test, but strictly they are ints.
    # In integration they are properly interned. Here we rely on dataclass equality.
    
    # Let's use fake ints for symbol IDs
    S_x, S_y, S_z, S_a, S_b = 1, 2, 3, 4, 5
    
    stmts = [
        DisjointVar(1, 0, [S_x, S_y]),
        Axiom(2, 0, "ax1", 0, []),
        ScopeEnter(3, 0),
        DisjointVar(4, 0, [S_x, S_z]),
        Theorem(5, 0, "th1", 0, [], []),
        ScopeExit(6, 0),
        DisjointVar(7, 0, [S_a, S_b])
    ]
    
    unit = ProofUnitIR(
        unit_id="test_unit",
        origin_ref=0,
        origin_module_id=0,
        lir_stmts=stmts,
        exports=["th1"]
    )
    
    # Run Stage 3
    result = stage3_run([unit], symtab, contracts)
    
    # Verify ax1 contract
    c_ax1 = result.contracts["ax1"]
    # Should check equality of sets, order doesn't matter for correctness but verify extraction
    assert len(c_ax1.distinct_vars) == 1
    assert {S_x, S_y} in c_ax1.distinct_vars
    
    # Verify th1 contract
    c_th1 = result.contracts["th1"]
    assert len(c_th1.distinct_vars) == 2
    assert {S_x, S_y} in c_th1.distinct_vars
    assert {S_x, S_z} in c_th1.distinct_vars
    # Should NOT have {a, b}
    assert {S_a, S_b} not in c_th1.distinct_vars

