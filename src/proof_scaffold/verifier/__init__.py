# src/proof_scaffold/verify.py
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def verify(command: list[str], mm_file: Path, timeout_sec: int = 60) -> None:
    """
    Run a verifier command against a .mm file.
    
    Args:
        command: The command line to execute (e.g. ["python3", "verifier/mmverify.py"]).
                 The `.mm` file path will be appended to this command.
        mm_file: Path to the .mm file to verify.
        timeout_sec: Timeout in seconds.
    """
    mm_file = Path(mm_file)

    if not mm_file.exists():
        raise FileNotFoundError(f".mm file not found: {mm_file}")

    # command is trusted to be correct from config/caller
    full_cmd = command + [str(mm_file)]

    proc = subprocess.run(
        full_cmd,
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
            f"cmd:      {full_cmd}\n"
            f"return:   {proc.returncode}\n"
            f"output:\n{proc.stdout}"
        )
