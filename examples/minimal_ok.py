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

from skfd.builder_v2 import MMBuilderV2
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver

MODULE_ID: Final[str] = "examples.minimal_ok"
UNIT_ID: Final[str] = f"{MODULE_ID}:unit0"


def build_units() -> tuple[OriginTable, SymbolInterner, list[ProofUnitIR]]:
    ot = OriginTable()
    interner = SymbolInterner()

    mm = MMBuilderV2(
        interner=interner,
        origin_table=ot,
        names=NameResolver(),
        unit_id=UNIT_ID,
        origin_module_id=MODULE_ID,
    )

    turnstile = mm.sym.const("|-")
    ph = mm.sym.var("ph")
    wph = mm.sym.label("wph")
    th1 = mm.sym.label("th1")

    mm.f(wph, tc=turnstile, var=ph)
    mm.p(th1, tc=turnstile, expr=[ph], proof=[wph])
    mm.export(th1)

    unit = mm.finish()

    return ot, interner, [unit]


def run() -> str:
    ot, interner, units = build_units()
    res = LinkerV1.link(units=units, origin_table=ot, interner=interner)

    return res.mm_text


if __name__ == "__main__":
    print(run())
