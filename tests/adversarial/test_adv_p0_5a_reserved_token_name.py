from __future__ import annotations

import pytest
from proof_scaffold.linker.diag import LinkerDiagError
from proof_scaffold.linker.origin import OriginRecord, OriginTable
from proof_scaffold.linker.symbols import SymbolInterner


@pytest.mark.adversarial
def test_adv_p0_5a_reserved_token_rejected() -> None:
    """ADV-P0-5a (Link Model v4): reserved token names must be rejected.

    Bootstrap alignment:
    - currently rejected at interner time (Stage 0-ish), not Stage 1.
    - must be LinkerDiagError with stable details.
    """

    ot = OriginTable()
    origin_ref = ot.intern(OriginRecord(module_id="adv", file="<test>", line=1))
    interner = SymbolInterner()

    with pytest.raises(LinkerDiagError) as ei:
        _ = interner.intern(
            origin_module_id="adv",
            local_name="$bad",
            kind="Const",
            origin_ref=origin_ref,
        )

    e = ei.value
    assert e.diag.error_code == "E_RESERVED_TOKEN_NAME"
    assert e.diag.details["hint_original_token"] == "$bad"

    # Deterministic formatting contract.
    s1 = str(e)
    s2 = str(e)
    assert s1 == s2
