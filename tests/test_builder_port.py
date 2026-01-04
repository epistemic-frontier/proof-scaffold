# tests/test_builder_port.py
from skfd.builder import MMBuilder
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner


def test_builder_minimal() -> None:
    interner = SymbolInterner()
    origins = OriginTable()
    
    # Instantiate builder
    mm = MMBuilder(
        interner=interner,
        origin_table=origins,
        module_id="test_mod"
    )

    # Use DSL
    (
        mm
        .c("min", "im", "(", ")")
        .v("A", "B")
        .f("wA", "min", "A")
        .f("wB", "min", "B")
        .a("ax-1", "min", "A im ( B im A )")
    )

    # Check Text
    text = mm.render()
    print("--- Generated Text ---")
    print(text)
    assert "$c min im ( ) $." in text
    assert "$v A B $." in text
    assert "ax-1 $a min A im ( B im A ) $." in text

    # Check IR
    unit = mm.to_proof_unit("test_unit")
    print("\n--- Generated IR ---")
    print(unit)
    
    assert unit.unit_id == "test_unit"
    assert len(unit.lir_stmts) > 0
    # Basic structural check
    decl = unit.lir_stmts[0]
    # Check if we got IDs
    # Since we can't easily peek inside interner without knowing IDs, we rely on the object correctness
    assert decl.origin_ref >= 0

if __name__ == "__main__":
    test_builder_minimal()
