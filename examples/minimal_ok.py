"""M0.2 minimal example (happy path).

Construct a tiny verifiable Metamath program using the Builder API:
- create an OriginTable and SymbolInterner
- use MMBuilder to construct the ProofUnitIR
- link (stage1 lint + emit)
- verify and return emitted mm text

The goal is readability and determinism.
"""

from __future__ import annotations

from typing import Final

from skfd.builder import MMBuilder
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.api import LinkerV1

MODULE_ID: Final[str] = "examples.minimal_ok"
UNIT_ID: Final[str] = f"{MODULE_ID}:unit0"


def build_units() -> tuple[OriginTable, SymbolInterner, list[ProofUnitIR]]:
    ot = OriginTable()
    interner = SymbolInterner()

    mm = MMBuilder(
        interner=interner,
        origin_table=ot,
        module_id=MODULE_ID
    )

    # Minimal: declare $c/$v, declare $f, prove theorem by referencing $f label.
    (
        mm
        .c("|-")
        .v("ph")
        .f("wph", "|-", "ph")
        # NOTE: .p() takes (label, typecode, expr_str, proof)
        # emit_mm will output: label $p typecode expr_str $.
        # So we pass "ph" as expr, not "|- ph".
        .p("th1", "|-", "ph", proof=["wph"])
        .export("th1")
    )

    unit = mm.to_proof_unit(UNIT_ID)
    
    return ot, interner, [unit]


def run() -> str:
    ot, interner, units = build_units()
    res = LinkerV1.link(units=units, origin_table=ot, interner=interner)

    return res.mm_text


if __name__ == "__main__":
    print(run())
