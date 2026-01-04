"""M0.2 minimal example (happy path).

Construct a tiny verifiable Metamath program in linker IR:
- create an OriginTable and SymbolInterner
- build one ProofUnitIR with LIR statements
- link (stage1 lint + emit)
- verify and return emitted mm text

The goal is readability and determinism, not new linking capability.
"""

from __future__ import annotations

from typing import Final

from proof_scaffold.linker.api import LinkerV1
from proof_scaffold.linker.lir import (
    ConstDecl,
    FloatingHyp,
    Theorem,
    VarDecl,
)
from proof_scaffold.linker.origin import OriginRecord, OriginTable
from proof_scaffold.linker.symbols import SymbolInterner
from proof_scaffold.linker.unit import ProofUnitIR

MODULE_ID: Final[str] = "examples.minimal_ok"
UNIT_ID: Final[str] = f"{MODULE_ID}:unit0"


def build_units() -> tuple[OriginTable, SymbolInterner, list[ProofUnitIR]]:
    ot = OriginTable()
    interner = SymbolInterner()

    # Use fixed, deterministic origins (no __file__/line coupling for examples).
    unit_origin = ot.intern(
        OriginRecord(module_id=MODULE_ID, file="examples/minimal_ok.py", line=1)
    )
    stmt_origin = ot.intern(
        OriginRecord(module_id=MODULE_ID, file="examples/minimal_ok.py", line=2)
    )

    # Constants
    c_turnstile = interner.intern(
        origin_ref=stmt_origin, origin_module_id=MODULE_ID, local_name="|-", kind="Const"
    )

    # Variables
    v_ph = interner.intern(
        origin_ref=stmt_origin, origin_module_id=MODULE_ID, local_name="ph", kind="Var"
    )

    # Labels
    l_wph = interner.intern(
        origin_ref=stmt_origin, origin_module_id=MODULE_ID, local_name="wph", kind="Label"
    )
    l_th1 = interner.intern(
        origin_ref=stmt_origin, origin_module_id=MODULE_ID, local_name="th1", kind="Label"
    )

    # Minimal: declare $c/$v, declare $f, prove theorem by referencing $f label.
    stmts: list[ConstDecl | VarDecl | FloatingHyp | Theorem] = [
        # NOTE: our bootstrap emitter uses the shorthand "$c ... $." where the
        # first token is interpreted as the label. We follow the current sanity
        # convention and use the constant "|-" as both typecode and constant.
        ConstDecl(stmt_id=0, origin_ref=stmt_origin, tokens=[c_turnstile]),
        VarDecl(stmt_id=1, origin_ref=stmt_origin, tokens=[v_ph]),
        FloatingHyp(
            stmt_id=2,
            origin_ref=stmt_origin,
            label=l_wph,
            typecode=c_turnstile,
            var=v_ph,
        ),
        Theorem(
            stmt_id=3,
            origin_ref=stmt_origin,
            label=l_th1,
            expr=[c_turnstile, v_ph],
            proof=[l_wph],
        ),
    ]

    unit = ProofUnitIR(
        unit_id=UNIT_ID,
        origin_ref=unit_origin,
        origin_module_id=MODULE_ID,
        lir_stmts=stmts,
        exports=[l_th1],
    )
    return ot, interner, [unit]


def run() -> str:
    ot, interner, units = build_units()
    res = LinkerV1.link(units=units, origin_table=ot, interner=interner)

    return res.mm_text


if __name__ == "__main__":
    print(run())
