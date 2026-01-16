# skfd/cli.py
"""
skfd: The ProofScaffold CLI
"""

from __future__ import annotations

import argparse
import os
import platform
import sys
from pathlib import Path

from skfd.core.diag import LinkerDiagError
from skfd.driver.runner import DriverRunner
from skfd.verifier import verify

from .config import VerifierConfig, load_config, save_config
from .doctor.check import run_sanity
from .doctor.slice import slice_package

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


def _cmd_doctor_slice(args: argparse.Namespace) -> int:
    """Run debug slice on a package."""
    root = (args.root or Path.cwd()) / "target"
    pkg = args.package
    label = args.label

    mm_file = root / f"{pkg}_full.mm"
    map_file = root / f"{pkg}_full.mm.map"

    try:
        report = slice_package(mm_file, map_file, label)
        print(report.render())
        return 0
    except Exception as e:
        print(f"Slice failed: {e}", file=sys.stderr)
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


def _cmd_verify(args: argparse.Namespace) -> int:
    """Run driver verification for a package."""
    root = (args.root or Path.cwd()) / "src"
    target = (args.root or Path.cwd()) / "target"

    if not root.exists():
        print(f"Error: Source directory not found: {root}", file=sys.stderr)
        return 1

    print(f"Initializing build driver (src={root}, target={target})...")
    runner = DriverRunner(root, target)

    try:
        # Build phase
        print("Building all packages...")
        runner.execute_all()

        # Verify phase
        pkg = args.package
        if pkg not in runner.lirs and "." in pkg:
            root_pkg = pkg.split(".", 1)[0]
            if root_pkg in runner.lirs:
                print(
                    f"Package '{pkg}' not found as a build unit; "
                    f"falling back to top-level package '{root_pkg}'."
                )
                pkg = root_pkg
        level = getattr(args, "level", 0)
        print(f"Verifying package '{pkg}' (Level {level})...")
        runner.verify_package(pkg, conformance_level=level)

        # Now run configured verifiers
        outfile = target / f"{pkg}_full.mm"
        if not outfile.exists():
            print(f"Error: Verification artifact not found: {outfile}", file=sys.stderr)
            return 1

        cfg = load_config(args.root)
        active_cmds = cfg.get_active_commands()

        if not active_cmds:
            print("Warning: No active verifiers configured.", file=sys.stderr)

        all_passed = True
        for name, cmd in active_cmds:
            print(f"[{name}] Verifying {outfile.name}... ", end="", flush=True)
            try:
                verify(cmd, outfile)
                print("OK")
            except Exception as e:
                print("FAIL")
                print(f"    Error: {e}")
                all_passed = False

        if all_passed:
            print("Verification completed successfully.")
            return 0
        else:
            print("Verification FAILED (some verifiers failed).", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Verification failed: {e}", file=sys.stderr)
        return 1


def _cmd_debug(args: argparse.Namespace) -> int:
    """Build a package and print mm + source context for a specific label."""
    root = (args.root or Path.cwd()) / "src"
    target = (args.root or Path.cwd()) / "target"

    if not root.exists():
        print(f"Error: Source directory not found: {root}", file=sys.stderr)
        return 1

    print(f"Initializing build driver (src={root}, target={target})...")
    runner = DriverRunner(root, target)

    try:
        print("Building all packages...")
        runner.execute_all()

        pkg = args.package
        if pkg not in runner.lirs and "." in pkg:
            root_pkg = pkg.split(".", 1)[0]
            if root_pkg in runner.lirs:
                print(
                    f"Package '{pkg}' not found as a build unit; "
                    f"falling back to top-level package '{root_pkg}'."
                )
                pkg = root_pkg

        level = getattr(args, "level", 0)
        print(f"Verifying package '{pkg}' (Level {level}) to emit monolith...")
        runner.verify_package(pkg, conformance_level=level)

        mm_file = target / f"{pkg}_full.mm"
        map_file = target / f"{pkg}_full.mm.map"

        if not mm_file.exists():
            print(f"Error: Verification artifact not found: {mm_file}", file=sys.stderr)
            return 1

        if not map_file.exists():
            print(f"Error: Source map not found: {map_file}", file=sys.stderr)
            return 1

        label = args.label
        context_radius = getattr(args, "context", 4)

        try:
            with open(mm_file, encoding="utf-8") as f_mm:
                mm_lines = f_mm.read().splitlines()
        except Exception as e:
            print(f"Error: Failed to read {mm_file}: {e}", file=sys.stderr)
            return 1

        label_line_idx: int | None = None
        for i, line in enumerate(mm_lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("$("):
                continue
            first = stripped.split()[0]
            if first == label:
                label_line_idx = i
                break

        if label_line_idx is None:
            print(
                f"Error: Label '{label}' not found in {mm_file}", file=sys.stderr
            )
            return 1

        try:
            import json

            with open(map_file, encoding="utf-8") as f_map:
                map_data = json.load(f_map)
        except Exception as e:
            print(f"Error: Failed to read source map {map_file}: {e}", file=sys.stderr)
            return 1

        origin_ref = None
        mm_line_no = label_line_idx + 1
        for entry in map_data.get("mappings", []):
            if entry.get("line") == mm_line_no:
                origin_ref = entry.get("origin_ref")
                break

        origin_str = ""
        if origin_ref is not None:
            origins = map_data.get("origins", [])
            if isinstance(origin_ref, int) and 0 <= origin_ref < len(origins):
                orig = origins[origin_ref]
                src_file = orig.get("file", "??")
                src_line = orig.get("line", "??")
                origin_str = f"{src_file}:{src_line}"

        start = max(0, label_line_idx - context_radius)
        end = min(len(mm_lines), label_line_idx + context_radius + 1)
        print(f"Debugging label '{label}' in package '{pkg}':\n")
        if origin_str:
            print(f"--> Source Origin: {origin_str}")
        print(f"--> MM context around line {mm_line_no} in {mm_file}:\n")
        for i in range(start, end):
            prefix = ">" if i == label_line_idx else " "
            print(f"{prefix} {i+1:6d}: {mm_lines[i]}")

        return 0

    except Exception as e:
        print(f"Debug failed: {e}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="skfd", description="ProofScaffold CLI")
    p.add_argument("--root", type=Path, help="Project root", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- doctor ---
    # --- doctor ---
    p_doctor = sub.add_parser("doctor", help="Diagnostic tools")
    doc_sub = p_doctor.add_subparsers(dest="doc_cmd", required=True)

    # check
    p_doc_check = doc_sub.add_parser(
        "check", help="Check environment and toolchain health"
    )
    p_doc_check.set_defaults(func=_cmd_doctor)

    # slice
    p_doc_slice = doc_sub.add_parser("slice", help="Debug slice a statement")
    p_doc_slice.add_argument("package", help="Package name (e.g. logic)")
    p_doc_slice.add_argument("label", help="Target label (e.g. th-1)")
    p_doc_slice.set_defaults(func=_cmd_doctor_slice)

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

    # --- verify (driver) ---
    p_verify = sub.add_parser("verify", help="Build and verify a package")
    p_verify.add_argument(
        "package", help="Name of the package to verify (e.g. 'logic')"
    )
    p_verify.add_argument(
        "--level",
        type=int,
        default=0,
        choices=[0, 1, 2],
        help="Conformance level (0=Loose, 1=Strict Interface, 2=FOL)",
    )
    p_verify.set_defaults(func=_cmd_verify)

    # --- debug (mm slice) ---
    p_debug = sub.add_parser(
        "debug", help="Build package and show mm + source context for a label"
    )
    p_debug.add_argument(
        "package", help="Name of the package to debug (e.g. 'logic')"
    )
    p_debug.add_argument("label", help="Metamath label to inspect (e.g. 'L1_id')")
    p_debug.add_argument(
        "--level",
        type=int,
        default=0,
        choices=[0, 1, 2],
        help="Conformance level (0=Loose, 1=Strict Interface, 2=FOL)",
    )
    p_debug.add_argument(
        "--context",
        type=int,
        default=4,
        help="Number of lines of context to show before/after the label line",
    )
    p_debug.set_defaults(func=_cmd_debug)

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
