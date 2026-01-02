#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFIER = REPO_ROOT / "verifier" / "mmverify.py"
FIXTURES_DIR = REPO_ROOT / "fixtures" / "sanity" / "m02"


@dataclass(frozen=True)
class Case:
    name: str
    filename: str
    should_pass: bool


CASES = [
    Case("happy", "05_mp_happy.mm", True),
    Case("missing_hyp", "05_mp_missing_hyp.mm", False),
    Case("bad_proof_tokens", "05_mp_bad_proof_tokens.mm", False),
]


def run_verifier(mm_path: Path) -> subprocess.CompletedProcess[str]:
    if not VERIFIER.exists():
        raise FileNotFoundError(f"Verifier not found: {VERIFIER}")
    if not mm_path.exists():
        raise FileNotFoundError(f"Fixture not found: {mm_path}")

    # Assumption: `python verifier/mmverify.py <file>` returns exit code 0 on success.
    # If your verifier CLI differs, adjust args here (only here).
    return subprocess.run(
        [sys.executable, str(VERIFIER), str(mm_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def short_snip(s: str, max_lines: int = 12) -> str:
    lines = s.splitlines()
    if len(lines) <= max_lines:
        return s.strip()
    return "\n".join(lines[:max_lines]).strip() + "\n... (truncated)"


def main() -> int:
    print("== Sanity M0.2 / Step 05: Modus Ponens ==")
    failures = 0

    for case in CASES:
        mm_path = FIXTURES_DIR / case.filename
        proc = run_verifier(mm_path)
        ok = (proc.returncode == 0)

        verdict = "PASS" if ok else "FAIL"
        expected = "PASS" if case.should_pass else "FAIL"

        print(f"\n-- case: {case.name}")
        print(f"   fixture: {mm_path.relative_to(REPO_ROOT)}")
        print(f"   verifier: {verdict} (expected {expected})")

        # Always show a compact snippet for teaching/debugging value.
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if out:
            print("   stdout:")
            print("   " + short_snip(out).replace("\n", "\n   "))
        if err:
            print("   stderr:")
            print("   " + short_snip(err).replace("\n", "\n   "))

        if ok != case.should_pass:
            failures += 1
            print("   ==> unexpected result")

    if failures == 0:
        print("\n== OK: Step 05 sanity behavior matches expectations ==")
        return 0

    print(f"\n== ERROR: {failures} case(s) did not match expectations ==")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
