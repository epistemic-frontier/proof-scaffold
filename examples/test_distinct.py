import sys

from skfd.builder.builder import MMBuilder
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.linker.api import LinkerV1


def main() -> None:
    print("Verifying Distinct Variable ($d) Support...")
    
    interner = SymbolInterner()
    origin_table = OriginTable()

    # Create a builder instance
    mm = MMBuilder(
        interner=interner,
        origin_table=origin_table,
        module_id="test_distinct",
        ascii_comments=True
    )

    # Build a simple module with $d
    mm.c("wff", "|-", "->")
    mm.v("ph", "ps", "ch")
    
    mm.f("wph", "wff", "ph")
    mm.f("wps", "wff", "ps")
    mm.f("wch", "wff", "ch")
    
    # Assert disjointness - 2 vars
    mm.d("ph", "ps")
    
    # Assert disjointness - 3 vars
    mm.d("ph", "ps", "ch")
    
    # Assert disjointness in scope
    with mm.block():
        mm.d("ch", "ph")
    
    # Generate IR
    unit = mm.to_proof_unit("unit_d")
    
    # Link and emit
    res = LinkerV1.link(
        units=[unit],
        origin_table=origin_table,
        interner=interner
    )
    
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
