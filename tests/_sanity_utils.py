# tests/_sanity_utils.py
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

ENV_VERBOSE = "PROOF_SCAFFOLD_VERIFIERS_VERBOSE"
ENV_SEM = "PROOF_SCAFFOLD_SEMANTIC_VERIFIERS"
ENV_LINT = "PROOF_SCAFFOLD_LINT_VERIFIERS"


def _vprint(msg: str) -> None:
    if os.environ.get(ENV_VERBOSE, "").strip() == "1":
        print(msg, file=sys.stderr)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_list(env_name: str, default_csv: str) -> List[Path]:
    root = repo_root()
    spec = os.environ.get(env_name, "").strip() or default_csv
    out: List[Path] = []
    for part in spec.split(","):
        part = part.strip()
        if part:
            out.append((root / part).resolve())
    return out


def semantic_verifiers() -> List[Path]:
    # proof-checking oracles
    return _parse_list(ENV_SEM, "verifier/mmverify.py,verifier/shims/metamath.py")


def lint_verifiers() -> List[Path]:
    # parser/lint tools (may not validate proofs)
    return _parse_list(ENV_LINT, "verifier/metamath-knife")


def fixture(relpath: str) -> Path:
    p = (repo_root() / relpath).resolve()
    if not p.exists():
        raise FileNotFoundError(f"fixture not found: {p}")
    return p


def _run(verifier: Path, mm_file: Path, timeout_sec: int = 60) -> Tuple[int, str, List[str]]:
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
    return proc.returncode, proc.stdout or "", cmd


def verify_expect_ok(mm_file: Path) -> None:
    sem = semantic_verifiers()
    lint = lint_verifiers()
    _vprint(f"[verify-ok] {mm_file}\n  semantic={sem}\n  lint={lint}")

    for v in sem + lint:
        rc, out, cmd = _run(v, mm_file)
        if out:
            print(out)
        assert rc == 0, (
            "Metamath verification failed\n"
            f"verifier: {v}\n"
            f"mm_file:  {mm_file}\n"
            f"cmd:      {cmd}\n"
            f"return:   {rc}\n"
            f"output:\n{out}"
        )


def verify_expect_fail(mm_file: Path) -> None:
    sem = semantic_verifiers()
    _vprint(f"[verify-fail] {mm_file}\n  semantic={sem}")

    # Only semantic verifiers are required to fail.
    for v in sem:
        rc, out, cmd = _run(v, mm_file)
        if out:
            print(out)
        assert rc != 0, (
            "Expected semantic verifier to fail, but it succeeded\n"
            f"verifier: {v}\n"
            f"mm_file:  {mm_file}\n"
            f"cmd:      {cmd}\n"
            f"return:   {rc}\n"
            f"output:\n{out}"
        )


def run_sanity_script_for_all_verifiers(script: Path) -> None:
    # For M0.1 scripts: run only on semantic verifiers (they define correctness).
    # Lint verifiers are not guaranteed to implement proof checking.
    if not script.exists():
        raise FileNotFoundError(f"sanity script not found: {script}")

    for v in semantic_verifiers():
        _vprint(f"[sanity-script] run {script} --mmverify {v}")
        proc = subprocess.run(
            [sys.executable, str(script), "--mmverify", str(v)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.returncode == 0, (
            f"sanity script failed\n"
            f"script:   {script}\n"
            f"verifier: {v}\n"
            f"output:\n{proc.stdout}"
        )
