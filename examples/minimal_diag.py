"""M0.2 minimal example (diagnostic path).

This example intentionally violates Link Model v4 Stage 1 invariant:
local_name must not start with '$'.

It should raise LinkerDiagError with code E_RESERVED_TOKEN_NAME.
"""

from __future__ import annotations

from typing import Final

from proof_scaffold.linker.api import LinkerV1
from proof_scaffold.linker.diag import LinkerDiagError
from proof_scaffold.linker.lir import ConstDecl
from proof_scaffold.linker.origin import OriginRecord, OriginTable
from proof_scaffold.linker.symbols import SymbolInterner
from proof_scaffold.linker.unit import ProofUnitIR

MODULE_ID: Final[str] = "examples.minimal_diag"
UNIT_ID: Final[str] = f"{MODULE_ID}:unit0"


def run() -> None:
    ot = OriginTable()
    interner = SymbolInterner()

    unit_origin = ot.intern(
        OriginRecord(module_id=MODULE_ID, file="examples/minimal_diag.py", line=1)
    )
    stmt_origin = ot.intern(
        OriginRecord(module_id=MODULE_ID, file="examples/minimal_diag.py", line=2)
    )

    bad = interner.intern(
        origin_ref=stmt_origin, origin_module_id=MODULE_ID, local_name="$bad", kind="Const"
    )

    unit = ProofUnitIR(
        unit_id=UNIT_ID,
        origin_ref=unit_origin,
        origin_module_id=MODULE_ID,
        lir_stmts=[ConstDecl(stmt_id=0, origin_ref=stmt_origin, tokens=[bad])],
        exports=[],
    )

    try:
        LinkerV1.link(units=[unit], origin_table=ot, interner=interner)
    except LinkerDiagError:
        raise
    raise AssertionError("expected LinkerDiagError")


if __name__ == "__main__":
    run()
