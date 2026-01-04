"""
skfd: The ProofScaffold CLI
"""

from __future__ import annotations

import argparse
import os
import platform
import sys
from pathlib import Path

from skfd.verifier import verify

from .config import VerifierConfig, load_config, save_config
from .doctor.check import run_sanity
from skfd.core.diag import LinkerDiagError

# Hack: ensure CWD is in path so we can import examples/user code
cwd = str(Path.cwd())
if cwd not in sys.path:
    # Use insert(1) if 0 is script path, or just 0.
    sys.path.insert(0, cwd)


def _build_dir(*parts: str) -> Path:
    # Repo convention: all runtime artifacts live under ./build
    return Path("build").joinpath(*parts)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_example_minimal_ok(verifier_cmd: list[str], *, write_mm: bool = True) -> None:
    from examples.minimal_ok import run as run_example

    mm_text = run_example()
    if write_mm:
        _write_text(_build_dir("examples", "minimal_ok", "out.mm"), mm_text)

    # Verify from a temp file (verifier reads from disk).
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as td:
        mm_path = Path(td) / "minimal_ok.mm"
        mm_path.write_text(mm_text, encoding="utf-8")
        verify(verifier_cmd, mm_path)


def _run_example_minimal_diag(*, write_mm: bool = False) -> None:
    from examples.minimal_diag import run as run_example

    run_example()
    # minimal_diag is expected to fail before emission; keep side effects minimal.
    if write_mm:
        raise AssertionError("minimal_diag should not emit")


def _cmd_doctor(args: argparse.Namespace) -> int:
    """Check environment and toolchain health."""
    cfg = load_config(args.root)
    active_cmds = cfg.get_active_commands()

    print("skfd doctor: checking environment...")
    print(f"  Python: {platform.python_version()} ({sys.executable})")
    print(f"  Platform: {platform.platform()}")
    print(f"  Active Verifiers: {[name for name, _ in active_cmds]}")

    print("  Checking internal sanity (memory-only)... ", end="", flush=True)
    try:
        # Run sanity just once for internal linker check (backend agnostic)
        # using the first available verifier or just generic
        if active_cmds:
            run_sanity(active_cmds[0][1])
        else:
            print("[No active verifier for internal check] ", end="")
        print("OK")
    except Exception as e:
        print("FAIL")
        print(e)
        return 1

    all_passed = True
    for name, cmd in active_cmds:
        print(f"  [{name}] Running sanity check... ", end="", flush=True)
        try:
            run_sanity(cmd)
            print("OK")
        except Exception as e:
            print("FAIL")
            print(f"    Error: {e}")
            all_passed = False

    if all_passed:
        print("Doctor check passed.")
        return 0
    else:
        print("Doctor check FAILED (some verifiers failed).")
        return 1


def _cmd_smoke(args: argparse.Namespace) -> int:
    """Legacy smoke test: runs sanity + minimal_ok."""
    cfg = load_config(args.root)
    active_cmds = cfg.get_active_commands()

    for name, cmd in active_cmds:
        print(f"===[{name}]===")
        print("Running sanity check...")
        run_sanity(cmd)
        print("Running minimal_ok example...")
        _run_example_minimal_ok(cmd, write_mm=not args.no_write)
        print(f"[{name}] accepted")

    return 0


def _cmd_example(args: argparse.Namespace) -> int:
    cfg = load_config(args.root)
    active_cmds = cfg.get_active_commands()

    name = args.name

    if name == "minimal_ok":
        for v_name, cmd in active_cmds:
            print(f"[{v_name}] Running minimal_ok...")
            _run_example_minimal_ok(cmd, write_mm=not args.no_write)
        print("accepted")
        return 0

    if name == "minimal_diag":
        _run_example_minimal_diag(write_mm=not args.no_write)
        # If it didn't raise, it's unexpected.
        print("unexpected: minimal_diag did not fail")
        return 2

    print(f"unknown example: {name}", file=sys.stderr)
    return 2


def _cmd_verifier_list(args: argparse.Namespace) -> int:
    cfg = load_config(args.root)
    active_set = set(cfg.active_verifiers)
    print("Configured verifiers:")
    for name, v in sorted(cfg.verifiers.items()):
        prefix = "* " if name in active_set else "  "
        print(f"{prefix}{name:<15} -> {v.command} {' '.join(v.args)}")
    return 0


def _cmd_verifier_add(args: argparse.Namespace) -> int:
    cfg = load_config(args.root)
    name = args.name
    command = args.command
    cmd_args = args.args or []

    # Resolve command to absolute path if it is a file and exists
    cmd_path = Path(command)
    # Check if it looks like a path (contains separators) or exists in CWD
    if os.path.sep in command or cmd_path.exists():
        resolved = cmd_path.resolve()
        if resolved.exists() and resolved.is_file():
            command = str(resolved)

    cfg.verifiers[name] = VerifierConfig(command=command, args=cmd_args)
    if name not in cfg.active_verifiers:
        cfg.active_verifiers.append(name)

    save_config(cfg, args.root)
    print(f"Added and activated verifier '{name}'")
    return 0


def _cmd_verifier_remove(args: argparse.Namespace) -> int:
    cfg = load_config(args.root)
    name = args.name
    if name not in cfg.verifiers:
        print(f"Error: verifier '{name}' not found", file=sys.stderr)
        return 1

    del cfg.verifiers[name]
    if name in cfg.active_verifiers:
        cfg.active_verifiers.remove(name)

    save_config(cfg, args.root)
    print(f"Removed verifier '{name}'")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="skfd", description="ProofScaffold CLI")
    p.add_argument("--root", type=Path, help="Project root", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- doctor ---
    p_doctor = sub.add_parser("doctor", help="Check environment and toolchain health")
    p_doctor.set_defaults(func=_cmd_doctor)

    # --- smoke (legacy) ---
    p_smoke = sub.add_parser("smoke", help="[Legacy] run sanity + minimal_ok")
    p_smoke.add_argument(
        "--no-write", action="store_true", help="do not write build/* artifacts"
    )
    p_smoke.set_defaults(func=_cmd_smoke)

    # --- example ---
    p_example = sub.add_parser("example", help="run a named example")
    p_example.add_argument("name", choices=["minimal_ok", "minimal_diag"])
    p_example.add_argument(
        "--no-write", action="store_true", help="do not write build/* artifacts"
    )
    p_example.set_defaults(func=_cmd_example)

    # --- verifier ---
    p_ver = sub.add_parser("verifier", help="Manage verifiers")
    ver_sub = p_ver.add_subparsers(dest="ver_cmd", required=True)

    p_ver_list = ver_sub.add_parser("list", help="List verifiers")
    p_ver_list.set_defaults(func=_cmd_verifier_list)

    p_ver_add = ver_sub.add_parser("add", help="Add a verifier")
    p_ver_add.add_argument("name", help="Name of the verifier")
    p_ver_add.add_argument("command", help="Command to execute")
    p_ver_add.add_argument("args", nargs="*", help="Arguments for the command")
    p_ver_add.set_defaults(func=_cmd_verifier_add)

    p_ver_rm = ver_sub.add_parser("remove", help="Remove a verifier")
    p_ver_rm.add_argument("name", help="Name of the verifier")
    p_ver_rm.set_defaults(func=_cmd_verifier_remove)

    args = p.parse_args(argv)

    # Handle root override if needed for sys.path?
    if args.root:
        sys.path.insert(0, str(args.root.resolve()))

    try:
        if hasattr(args, "func"):
            return int(args.func(args))
        return 0
    except LinkerDiagError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    # Repo convention: all runtime artifacts live under ./build
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
