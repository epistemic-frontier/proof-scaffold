#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SHIM_VERSION = "metamath-shim v2026-01-01b"

# Robust success marker: tolerate minor formatting differences.
SUCCESS_RE = re.compile(r"all proofs .* were verified", re.IGNORECASE)

# Robust error markers (READ-time errors matter)
ERROR_RE_LIST = [
    # Canonical Metamath error prefix
    re.compile(r"^\s*\?error\b", re.IGNORECASE | re.MULTILINE),

    # Summary line for errors (requires a number, avoids "No errors were found.")
    re.compile(r"^\s*\d+\s+errors\s+were\s+found\.", re.IGNORECASE | re.MULTILINE),

    # Read failure
    re.compile(r"^\s*\?no source file has been read in", re.IGNORECASE | re.MULTILINE),
]


def main() -> int:
    print(f"[{SHIM_VERSION}] file={__file__}", file=sys.stderr)

    if len(sys.argv) != 2:
        print("usage: metamath.py <file.mm>", file=sys.stderr)
        return 2

    mm_file = Path(sys.argv[1]).expanduser().resolve()
    if not mm_file.exists():
        print(f".mm file not found: {mm_file}", file=sys.stderr)
        return 2

    metamath_bin = os.environ.get("METAMATH_BIN", "").strip() or "metamath"
    metamath_path = shutil.which(metamath_bin) if metamath_bin == "metamath" else metamath_bin
    if not metamath_path or not Path(metamath_path).exists():
        print(f"metamath binary not found: {metamath_bin}", file=sys.stderr)
        return 2

    workdir = mm_file.parent
    filename = mm_file.name

    script = "\n".join(
        [
            f"READ {filename}",
            "VERIFY PROOF *",
            "EXIT",
            "EXIT",
            "",
            "",
        ]
    )

    timeout = int(os.environ.get("METAMATH_TIMEOUT", "10"))

    try:
        proc = subprocess.run(
            [str(metamath_path)],
            cwd=str(workdir),
            input=script,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        if e.stdout:
            print(e.stdout)
        print(f"[{SHIM_VERSION}] timeout after {timeout}s", file=sys.stderr)
        return 124

    out = proc.stdout or ""
    print(out)

    # 1) If metamath printed any error markers, fail.
    for rx in ERROR_RE_LIST:
        if rx.search(out):
            print(f"[{SHIM_VERSION}] detected error via pattern: {rx.pattern}", file=sys.stderr)
            return 1

    # 2) If success marker present, succeed (ignore metamath exit code).
    if SUCCESS_RE.search(out):
        print(f"[{SHIM_VERSION}] success marker matched: {SUCCESS_RE.pattern}", file=sys.stderr)
        return 0

    # 3) Otherwise, fail with explanation.
    print(f"[{SHIM_VERSION}] no success marker matched; failing defensively", file=sys.stderr)
    # Helpful hint: show last 5 lines of output to debug formatting issues.
    tail = "\n".join(out.splitlines()[-5:])
    print(f"[{SHIM_VERSION}] output tail:\n{tail}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
