import sys

from skfd.builder_v2 import MMBuilderV2
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver


def main() -> None:
    print("Verifying Distinct Variable ($d) Support...")

    interner = SymbolInterner()
    origin_table = OriginTable()

    # Create a builder instance
    mm = MMBuilderV2(
        interner=interner,
        origin_table=origin_table,
        names=NameResolver(),
        unit_id="unit_d",
        origin_module_id="test_distinct",
    )

    # Build a simple module with $d
    ph = mm.sym.var("ph")
    ps = mm.sym.var("ps")
    ch = mm.sym.var("ch")

    # Assert disjointness - 2 vars
    mm.d(ph, ps)

    # Assert disjointness - 3 vars
    mm.d(ph, ps, ch)

    # Assert disjointness in scope
    with mm.block():
        mm.d(ch, ph)

    unit = mm.finish()

    # Link and emit
    res = LinkerV1.link(units=[unit], origin_table=origin_table, interner=interner)

    print("--- EMITTED METAMATH TEXT ---")
    print(res.mm_text)
    print("-----------------------------")

    # Basic assertions
    if "$d ph ps $." not in res.mm_text:
        print("FAIL: Missing $d ph ps $.")
        sys.exit(1)

    if "$d ph ps ch $." not in res.mm_text:
        print("FAIL: Missing $d ph ps ch $.")
        sys.exit(1)

    if "$d ch ph $." not in res.mm_text:
        print("FAIL: Missing scoped $d ch ph $.")
        sys.exit(1)

    print("SUCCESS: distinct variables emitted correctly.")


if __name__ == "__main__":
    main()
