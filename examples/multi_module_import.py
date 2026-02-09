"""M0.6 verification: Cross-module imports."""

from __future__ import annotations

from typing import Final

from skfd.builder_v2 import MMBuilderV2
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver

MODULE_A: Final[str] = "examples.multi.unitA"
UNIT_A_ID: Final[str] = f"{MODULE_A}:unit0"

MODULE_B: Final[str] = "examples.multi.unitB"
UNIT_B_ID: Final[str] = f"{MODULE_B}:unit0"


def build() -> tuple[OriginTable, SymbolInterner, list[ProofUnitIR]]:
    ot = OriginTable()
    interner = SymbolInterner()

    # --- Unit A ---
    print(f"Building {UNIT_A_ID}...")
    mm_a = MMBuilderV2(
        interner=interner,
        origin_table=ot,
        names=NameResolver(),
        unit_id=UNIT_A_ID,
        origin_module_id=MODULE_A,
    )
    turnstile = mm_a.sym.const("|-")
    wff = mm_a.sym.const("wff")
    ph = mm_a.sym.var("ph")
    mm_a.auto.floating(ph, tc=wff)
    ax1 = mm_a.sym.label("ax-1")
    mm_a.a(ax1, tc=turnstile, expr=[ph])
    mm_a.export(turnstile, wff, ph, ax1)

    unit_a = mm_a.finish()

    # --- Unit B ---
    print(f"Building {UNIT_B_ID}...")
    mm_b = MMBuilderV2(
        interner=interner,
        origin_table=ot,
        names=NameResolver(),
        unit_id=UNIT_B_ID,
        origin_module_id=MODULE_B,
    )

    th2 = mm_b.sym.label("th-2")
    mm_b.p(th2, tc=turnstile, expr=[ph], proof=[ax1])
    mm_b.export(th2)

    unit_b = mm_b.finish()

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
