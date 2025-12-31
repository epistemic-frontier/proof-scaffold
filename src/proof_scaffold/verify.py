import subprocess
from pathlib import Path


def verify(mmverify_py: Path, mm_file: Path, timeout_sec: int = 60) -> None:
    if not mmverify_py.exists():
        raise FileNotFoundError(f"mmverify.py not found: {mmverify_py}")
    if not mm_file.exists():
        raise FileNotFoundError(f".mm file not found: {mm_file}")

    cmd = ["python3", str(mmverify_py)]

    # 关键：stdin 喂给它
    with mm_file.open("rb") as f:
        proc = subprocess.run(
            cmd,
            stdin=f,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_sec,
        )

    print(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError("Metamath verification failed")
