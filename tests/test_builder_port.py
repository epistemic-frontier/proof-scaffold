# tests/test_builder_port.py
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.builder_v2 import MMBuilderV2
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver


def test_builder_minimal() -> None:
    interner = SymbolInterner()
    origins = OriginTable()

    # Instantiate builder
    mm = MMBuilderV2(
        interner=interner,
        origin_table=origins,
        names=NameResolver(),
        unit_id="test_unit",
        origin_module_id="test_mod",
    )

    min_tc = mm.sym.const("min")
    im = mm.sym.const("im")
    lp = mm.sym.const("(")
    rp = mm.sym.const(")")
    a = mm.sym.var("A")
    b = mm.sym.var("B")

    mm.f(mm.sym.label("wA"), tc=min_tc, var=a)
    mm.f(mm.sym.label("wB"), tc=min_tc, var=b)
    mm.a(mm.sym.label("ax-1"), tc=min_tc, expr=[a, im, lp, b, im, a, rp])

    unit = mm.finish()
    res = LinkerV1.link(
        units=[unit],
        origin_table=origins,
        interner=interner,
        conformance_level=0,
    )
    text = res.mm_text
    print("--- Generated Text ---")
    print(text)
    assert "ax-1 $a min A im ( B im A ) $." in text
    assert "$c" in text and "min" in text and "im" in text
    assert "$v" in text and "A" in text and "B" in text

    assert unit.unit_id == "test_unit"
    assert len(unit.lir_stmts) > 0
    # Basic structural check
    decl = unit.lir_stmts[0]
    # Check if we got IDs
    # Check if we got IDs
    # Since we can't easily peek inside interner without knowing IDs, we rely on the object correctness
    assert decl.origin_ref >= 0


if __name__ == "__main__":
    test_builder_minimal()
