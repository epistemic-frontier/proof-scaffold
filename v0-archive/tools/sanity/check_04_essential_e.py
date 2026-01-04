# tools/sanity/check_04_essential_e.py

from __future__ import annotations

import argparse
from pathlib import Path

from proof_scaffold.verify import verify


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mmverify", required=True)
    ap.add_argument("--mini", default="fixtures/sanity/04_essential_e.mm")
    args = ap.parse_args()

    mm_verifier = Path(args.mmverify).resolve()
    mini_path = Path(args.mini).resolve()
    # This sanity case tests the core $e mechanism using the proof embedded
    # in the fixture itself (label: "sanity.e1" inside the local scope).
    # We simply verify the fixture database as-is with the selected verifier.

    verify(mm_verifier, mini_path, timeout_sec=30)

    print("SANITY 04 OK")


if __name__ == "__main__":
    main()
