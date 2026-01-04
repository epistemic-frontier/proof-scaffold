from __future__ import annotations

from proof_scaffold.linker_v1.api import LinkerV1
from proof_scaffold.linker_v1.sanity.build_sanity_ir import build_sanity_ir


def test_m0p1_determinism_bytes_identical() -> None:
    ot1, interner1, units1 = build_sanity_ir()
    ot2, interner2, units2 = build_sanity_ir()

    out1 = LinkerV1.link(units=units1, origin_table=ot1, interner=interner1).mm_text
    out2 = LinkerV1.link(units=units2, origin_table=ot2, interner=interner2).mm_text

    assert out1 == out2

