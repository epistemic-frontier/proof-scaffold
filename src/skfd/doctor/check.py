from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from skfd.verifier import verify

from ..linker.api import LinkerV1
from .sanity_ir import build_sanity_ir


def run_sanity(verifier_cmd: list[str] | None = None) -> None:
    origin_table, interner, units = build_sanity_ir()

    # Link
    res = LinkerV1.link(units=units, origin_table=origin_table, interner=interner)
    mm_text = res.mm_text

    # Verify
    if verifier_cmd is None:
        # Fallback for tests invoking this directly without config
        import sys

        verifier_cmd = [sys.executable, "verifier/mmverify.py"]

    with TemporaryDirectory() as td:
        mm_path = Path(td) / "sanity.mm"
        mm_path.write_text(mm_text, encoding="utf-8")
        verify(verifier_cmd, mm_path)


def main() -> None:
    run_sanity()


if __name__ == "__main__":
    main()
