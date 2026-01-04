from __future__ import annotations

import tempfile
from pathlib import Path

from proof_scaffold.verifier import verify
from ..linker.api import LinkerV1
from .sanity_ir import build_sanity_ir


def run_sanity() -> None:
    origin_table, interner, units = build_sanity_ir()
    res = LinkerV1.link(units=units, origin_table=origin_table, interner=interner)

    with tempfile.TemporaryDirectory() as td:
        mm_path = Path(td) / "sanity.mm"
        mm_path.write_text(res.mm_text, encoding="utf-8")
        verifier = Path("verifier/mmverify.py")
        verify(verifier, mm_path)


def main() -> None:
    run_sanity()


if __name__ == "__main__":
    main()

