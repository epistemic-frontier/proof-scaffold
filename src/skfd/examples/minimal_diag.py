"""M0.2 minimal example (diagnostic path)."""

from __future__ import annotations

from typing import Final

from skfd.builder_v2 import MMBuilderV2
from skfd.core.diag import LinkerDiagError
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver

MODULE_ID: Final[str] = "skfd.examples.minimal_diag"
UNIT_ID: Final[str] = f"{MODULE_ID}:unit0"


def run() -> None:
    ot = OriginTable()
    interner = SymbolInterner()

    mm = MMBuilderV2(
        interner=interner,
        origin_table=ot,
        names=NameResolver(),
        unit_id=UNIT_ID,
        origin_module_id=MODULE_ID,
    )

    try:
        mm.sym.const("$bad")

        unit = mm.finish()
        LinkerV1.link(units=[unit], origin_table=ot, interner=interner)

    except LinkerDiagError as e:
        if e.diag.error_code == "E_RESERVED_TOKEN_NAME":
            raise
        raise

    raise AssertionError("expected LinkerDiagError(E_RESERVED_TOKEN_NAME)")


if __name__ == "__main__":
    run()

