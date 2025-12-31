# proof_scaffold/verify.py

import subprocess
from pathlib import Path


def verify(verifier: Path, mm_file: Path, timeout_sec: int = 60) -> None:
    if not verifier.exists():
        raise FileNotFoundError(f"verifier not found: {verifier}")
    if not mm_file.exists():
        raise FileNotFoundError(f".mm file not found: {mm_file}")

    if verifier.suffix == ".jar":
        cmd = ["java", "-jar", str(verifier)]
    elif verifier.suffix == ".py":
        cmd = ["python3", str(verifier)]
    else:
        cmd = [str(verifier)]

    cmd.append(str(mm_file))

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_sec,
    )

    print(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError("Metamath verification failed")
