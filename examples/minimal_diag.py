"""M0.2 minimal example (diagnostic path).

This example intentionally violates Link Model v4 Stage 1 invariant:
local_name must not start with '$'.

It should raise LinkerDiagError with code E_RESERVED_TOKEN_NAME.
"""

from __future__ import annotations

from typing import Final

from skfd.builder import MMBuilder
from skfd.linker.api import LinkerV1
from skfd.core.diag import LinkerDiagError
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner

MODULE_ID: Final[str] = "examples.minimal_diag"
UNIT_ID: Final[str] = f"{MODULE_ID}:unit0"


def run() -> None:
    ot = OriginTable()
    interner = SymbolInterner()

    mm = MMBuilder(
        interner=interner,
        origin_table=ot,
        module_id=MODULE_ID
    )

    try:
        # This calls interner.intern(), which checks for '$' prefix and raises LinkerDiagError
        mm.c("$bad")
        
        # If builder check is bypassed (unlikely), link should fail
        unit = mm.to_proof_unit(UNIT_ID)
        LinkerV1.link(units=[unit], origin_table=ot, interner=interner)
        
    except LinkerDiagError as e:
        # Check specific error code
        if e.diag.error_code == "E_RESERVED_TOKEN_NAME":
            # Re-raise so CLI knows it failed (as expected)
            raise
        # If some other error, re-raise to fail noisy
        raise

    raise AssertionError("expected LinkerDiagError(E_RESERVED_TOKEN_NAME)")


if __name__ == "__main__":
    run()
