"""
skfd: The ProofScaffold CLI
"""
from __future__ import annotations

import argparse
import sys
import platform
import subprocess
from pathlib import Path

from .linker.diag import LinkerDiagError
from .doctor.check import run_sanity
from proof_scaffold.verifier import verify


def _build_dir(*parts: str) -> Path:
    # Repo convention: all runtime artifacts live under ./build
    return Path("build").joinpath(*parts)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_example_minimal_ok(*, write_mm: bool = True) -> None:
    from examples.minimal_ok import run as run_example

    mm_text = run_example()
    if write_mm:
        _write_text(_build_dir("examples", "minimal_ok", "out.mm"), mm_text)

    # Verify from a temp file (verifier reads from disk).
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as td:
        mm_path = Path(td) / "minimal_ok.mm"
        mm_path.write_text(mm_text, encoding="utf-8")
        verify(Path("verifier/mmverify.py"), mm_path)


def _run_example_minimal_diag(*, write_mm: bool = False) -> None:
    from examples.minimal_diag import run as run_example

    run_example()
    # minimal_diag is expected to fail before emission; keep side effects minimal.
    if write_mm:
        raise AssertionError("minimal_diag should not emit")


def _cmd_doctor(_args: argparse.Namespace) -> int:
    """Check environment and verification chain."""
    print(f"skfd doctor: checking environment...")
    print(f"  Python: {platform.python_version()} ({sys.executable})")
    print(f"  Platform: {platform.platform()}")
    
    print("  Checking internal sanity (memory-only)... ", end="", flush=True)
    try:
        run_sanity()
        print("OK")
    except Exception as e:
        print("FAIL")
        print(e)
        return 1

    print("  Checking verifier... ", end="", flush=True)
    verifier_path = Path("verifier/mmverify.py")
    if verifier_path.exists():
        print(f"Found ({verifier_path})")
    else:
        print("MISSING")
        print(f"  Warning: {verifier_path} not found. 'verify' command might fail.")
    
    print("Doctor check passed.")
    return 0


def _cmd_smoke(args: argparse.Namespace) -> int:
    """Legacy smoke test: runs sanity + minimal_ok."""
    print("Running sanity check...")
    run_sanity()
    print("Running minimal_ok example...")
    _run_example_minimal_ok(write_mm=not args.no_write)
    print("accepted")
    return 0


def _cmd_example(args: argparse.Namespace) -> int:
    name = args.name
    if name == "minimal_ok":
        _run_example_minimal_ok(write_mm=not args.no_write)
        print("accepted")
        return 0
    if name == "minimal_diag":
        _run_example_minimal_diag(write_mm=not args.no_write)
        # If it didn't raise, it's unexpected.
        print("unexpected: minimal_diag did not fail")
        return 2

    print(f"unknown example: {name}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="skfd", description="ProofScaffold CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- doctor ---
    p_doctor = sub.add_parser("doctor", help="Check environment and toolchain health")
    p_doctor.set_defaults(func=_cmd_doctor)

    # --- smoke (legacy) ---
    p_smoke = sub.add_parser("smoke", help="[Legacy] run sanity + minimal_ok")
    p_smoke.add_argument("--no-write", action="store_true", help="do not write build/* artifacts")
    p_smoke.set_defaults(func=_cmd_smoke)

    # --- example ---
    p_example = sub.add_parser("example", help="run a named example")
    p_example.add_argument("name", choices=["minimal_ok", "minimal_diag"])
    p_example.add_argument("--no-write", action="store_true", help="do not write build/* artifacts")
    p_example.set_defaults(func=_cmd_example)

    args = p.parse_args(argv)

    try:
        if hasattr(args, "func"):
            return int(args.func(args))
        return 0
    except LinkerDiagError as e:
        # Stable, deterministic rendering.
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
