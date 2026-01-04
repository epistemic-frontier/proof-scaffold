# src/scaffold/verify.py
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def verify(verifier: Path, mm_file: Path, timeout_sec: int = 60) -> None:
    verifier = Path(verifier)
    mm_file = Path(mm_file)

    if not verifier.exists():
        raise FileNotFoundError(f"verifier not found: {verifier}")
    if not mm_file.exists():
        raise FileNotFoundError(f".mm file not found: {mm_file}")

    # Normalize command form:
    # - .jar: java -jar <jar> <mm_file>
    # - .py : python3 <py> <mm_file>
    # - else: <verifier> <mm_file>
    if verifier.suffix == ".jar":
        cmd = ["java", "-jar", str(verifier), str(mm_file)]
    elif verifier.suffix == ".py":
        cmd = [sys.executable, str(verifier), str(mm_file)]
    else:
        cmd = [str(verifier), str(mm_file)]

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_sec,
    )

    # Always print output so pytest captures it (helps debugging).
    if proc.stdout:
        print(proc.stdout)

    if proc.returncode != 0:
        raise RuntimeError(
            "Metamath verification failed\n"
            f"verifier: {verifier}\n"
            f"mm_file:  {mm_file}\n"
            f"cmd:      {cmd}\n"
            f"return:   {proc.returncode}\n"
            f"output:\n{proc.stdout}"
        )
