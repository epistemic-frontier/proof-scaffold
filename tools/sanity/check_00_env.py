# tools/sanity/check_00_env.py
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from proof_scaffold.mm_emit import append_p_block
from proof_scaffold.verify import verify


def main() -> None:
    ap = argparse.ArgumentParser(description="Step 00: environment sanity check for Metamath verifier.")
    ap.add_argument("--mmverify", required=True, help="Path to mmverify.py")
    ap.add_argument(
        "--fixture",
        default="fixtures/sanity/00_env.mm",
        help="Path to the Step 00 fixture .mm file",
    )
    args = ap.parse_args()

    mmverify_py = Path(args.mmverify).resolve()
    fixture_path = Path(args.fixture).resolve()

    mm_src = fixture_path.read_text(encoding="utf-8")

    # Step 00 theorem:
    # Re-prove the trivial axiom `ax-id` as a $p statement.
    # Important: `ax-id` requires the mandatory $f hypothesis for `ph`, i.e. `wph`.
    out_src = append_p_block(
        mm_src=mm_src,
        label="sanity.00",
        stmt="|- ( ph -> ph )",
        proof_labels=["wph", "ax-id"],
    )

    # Write to a temporary file to avoid polluting the repository.
    with tempfile.TemporaryDirectory() as td:
        out_mm = Path(td) / "out.mm"
        out_mm.write_text(out_src, encoding="utf-8")

        # Verify using the external Metamath verifier.
        verify(mmverify_py, out_mm, timeout_sec=30)

    print("SANITY 00 OK")


if __name__ == "__main__":
    main()
