"""M0.6 verification: Cross-module imports."""

from __future__ import annotations

from typing import Final

from skfd.builder import MMBuilder
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.api import LinkerV1

MODULE_A: Final[str] = "examples.multi.unitA"
UNIT_A_ID: Final[str] = f"{MODULE_A}:unit0"

MODULE_B: Final[str] = "examples.multi.unitB"
UNIT_B_ID: Final[str] = f"{MODULE_B}:unit0"


def build() -> tuple[OriginTable, SymbolInterner, list[ProofUnitIR]]:
    ot = OriginTable()
    interner = SymbolInterner()

    # --- Unit A ---
    print(f"Building {UNIT_A_ID}...")
    mm_a = MMBuilder(interner=interner, origin_table=ot, module_id=MODULE_A)
    # Declarations in A
    mm_a.c("|-", "wff", "->")
    mm_a.v("ph", "ps")
    mm_a.f("wph", "wff", "ph")
    # Axiom: ax-1 |- ph
    mm_a.a("ax-1", "|-", "|- ph")

    # Export symbols for B to use (manually extraction for this test)
    # We access protected members to get IDs for the test harness
    id_ax1 = mm_a._intern_label("ax-1")
    id_turnstile = mm_a._intern_const("|-")
    id_ph = mm_a._intern_var("ph")

    unit_a = mm_a.to_proof_unit(UNIT_A_ID)

    # --- Unit B ---
    print(f"Building {UNIT_B_ID}...")
    mm_b = MMBuilder(interner=interner, origin_table=ot, module_id=MODULE_B)

    # Import from A
    # We demonstrate aliasing: "|-" -> "turnstile"
    mm_b.import_symbols(ax_1=id_ax1, turnstile=id_turnstile, ph=id_ph)

    # Prove "th-2": |- ph using ax-1
    # Usage of imported symbols:
    # label: "th-2"
    # typecode: "turnstile" (aliased import)
    # pexpr: "turnstile ph" (aliased import + direct import)
    # proof: ["ax_1"] (imported label)
    mm_b.p("th-2", "turnstile", "turnstile ph", proof=["ax_1"])

    unit_b = mm_b.to_proof_unit(UNIT_B_ID)

    return ot, interner, [unit_a, unit_b]


def run() -> None:
    ot, interner, units = build()
    # Linker check
    print("Linking...")
    res = LinkerV1.link(units=units, origin_table=ot, interner=interner)
    print(f"SUCCESS: Linked {len(units)} units.")
    print("\n--- Generated MM Text ---")
    print(res.mm_text)


if __name__ == "__main__":
    run()
