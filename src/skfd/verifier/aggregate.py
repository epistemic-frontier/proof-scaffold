from __future__ import annotations

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VerifierResult:
    name: str
    passed: bool
    returncode: int
    output: str


def _run(command: list[str], mm_file: Path, timeout_sec: int) -> tuple[int, str]:
    proc = subprocess.run(
        command + [str(mm_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_sec,
    )
    return proc.returncode, proc.stdout or ""


def run_all(
    mm_file: Path, verifiers: Iterable[tuple[str, list[str]]], timeout_sec: int = 60
) -> list[VerifierResult]:
    results: list[VerifierResult] = []
    for name, cmd in verifiers:
        try:
            rc, out = _run(cmd, mm_file, timeout_sec)
            results.append(
                VerifierResult(name=name, passed=(rc == 0), returncode=rc, output=out)
            )
        except Exception as e:
            results.append(
                VerifierResult(name=name, passed=False, returncode=1, output=str(e))
            )
    return results


def summarize(results: list[VerifierResult]) -> str:
    if not results:
        return ""
    width = max(len(r.name) for r in results)
    lines = []
    for r in results:
        status = "OK" if r.passed else "FAIL"
        lines.append(f"{r.name:<{width}}  {status}  rc={r.returncode}")
    return "\n".join(lines)

