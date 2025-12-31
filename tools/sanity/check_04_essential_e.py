# tools/sanity/check_04_essential_e.py

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from proof_scaffold.mm_emit import append_p_block
from proof_scaffold.verify import verify


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mmverify", required=True)
    ap.add_argument("--mini", default="fixtures/sanity/04_essential_e.mm")
    args = ap.parse_args()

    mm_verifier = Path(args.mmverify).resolve()
    mini_path = Path(args.mini).resolve()
    mm_src = mini_path.read_text(encoding="utf-8")

    # This sanity case tests the core $e mechanism:
    #
    # In mini_e.mm we have:
    #   wph $f wff ph $.
    #   hph $e |- ph $.
    #   id-e $a |- ph $.   (with hph as an essential hypothesis in scope)
    #
    # Therefore, to apply id-e, the stack must contain:
    #   1) mandatory $f for ph: wph
    #   2) essential hypothesis: hph
    # Then we can use id-e.
    proof = ["wph", "hph", "id-e"]

    out_src = append_p_block(
        mm_src=mm_src,
        label="sanity.e1",
        stmt="|- ph",
        proof_labels=proof,
    )

    with tempfile.TemporaryDirectory() as td:
        out_mm = Path(td) / "out.mm"
        out_mm.write_text(out_src, encoding="utf-8")
        verify(mm_verifier, out_mm, timeout_sec=30)

    print("SANITY_E OK")


if __name__ == "__main__":
    main()
