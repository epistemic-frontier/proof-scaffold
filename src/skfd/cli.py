# skfd/cli.py
"""
skfd: The ProofScaffold CLI
"""

from __future__ import annotations

import argparse
import importlib
import os
import pkgutil
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


def _normalize_pkg_name(name: str) -> str:
    return name.strip().replace("-", "_")


def _init_gitignore(path: Path) -> None:
    entry = ".skfd"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if entry in existing.splitlines():
            return
        text = existing.rstrip("\n") + "\n" + entry + "\n"
        path.write_text(text, encoding="utf-8")
        return
    _write_text(path, entry + "\n")


def _init_skfd(path: Path) -> None:
    _write_text(path, "active = ['mmverify']\n")


def _init_pyproject(path: Path, *, project_name: str) -> None:
    text = f"""[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{project_name}"
version = "0.0.1"
requires-python = ">=3.10"

# Keep dependencies minimal for scaffolded projects.
dependencies = [
  "proof-scaffold",
]

[tool.setuptools.packages.find]
where = ["src"]
"""
    _write_text(path, text)


def _init_proof_template(path: Path) -> None:
    text = """from logic.propositional.hilbert import HilbertSystem
from logic.propositional.hilbert.lemmas import LemmaBuilder, LemmaProof


def prove_minimal(sys: HilbertSystem) -> LemmaProof:
    \"\"\"Minimal proof template: ph -> ph (A1 + MP).\"\"\"
    lb = LemmaBuilder(sys, "minimal")

    # Hypothesis
    h1 = lb.hyp("h1", "ph")

    # A1: ph -> (ps -> ph)
    s1 = lb.step("s1", "ph -> ( ps -> ph )", "A1")

    # MP h1, s1 => ps -> ph
    s2 = lb.mp("s2", h1, s1)

    return lb.build(s2)
"""
    _write_text(path, text)


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


def _cmd_init(args: argparse.Namespace) -> int:
    """Initialize a new ProofScaffold project."""
    root = Path(args.name).resolve()
    mode = args.mode
    pkg_name = _normalize_pkg_name(args.package or args.name)

    if root.exists() and any(root.iterdir()):
        print(f"Error: target directory not empty: {root}", file=sys.stderr)
        return 1

    root.mkdir(parents=True, exist_ok=True)

    _init_skfd(root / ".skfd")
    _init_gitignore(root / ".gitignore")

    if mode == "package":
        _init_pyproject(root / "pyproject.toml", project_name=pkg_name)
        pkg_dir = root / "src" / pkg_name
        pkg_dir.mkdir(parents=True, exist_ok=True)
        _write_text(pkg_dir / "__init__.py", "")
    else:
        _init_proof_template(root / "proof.py")

    print(f"Initialized {mode} project at {root}")
    return 0


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


def _cmd_list_lemmas(args: argparse.Namespace) -> int:
    """Reflect over lemma constructors and print a simple index."""
    package = args.package
    rel_module = getattr(args, "module", "propositional.hilbert.lemmas")

    if rel_module:
        module_name = f"{package}.{rel_module}"
    else:
        module_name = package

    try:
        root_module = importlib.import_module(module_name)
    except Exception as e:
        print(f"Error: Failed to import module '{module_name}': {e}", file=sys.stderr)
        return 1

    modules: list[object] = []
    if hasattr(root_module, "__path__"):
        modules.append(root_module)
        for info in pkgutil.walk_packages(root_module.__path__, root_module.__name__ + "."):
            try:
                submod = importlib.import_module(info.name)
            except Exception:
                continue
            modules.append(submod)
    else:
        modules.append(root_module)

    seen: dict[str, str] = {}
    for module in modules:
        for attr_name in dir(module):
            if not attr_name.startswith("prove_"):
                continue
            fn = getattr(module, attr_name, None)
            if not callable(fn):
                continue
            lemma_id = attr_name[len("prove_") :]
            doc = fn.__doc__ or ""
            first_line = ""
            for line in doc.strip().splitlines():
                stripped = line.strip()
                if stripped:
                    first_line = stripped
                    break
            if lemma_id not in seen:
                seen[lemma_id] = first_line

    if not seen:
        print(f"No lemma constructors found under '{module_name}'.")
        return 0

    rows = sorted(seen.items(), key=lambda r: r[0])
    width = max(len(name) for name, _ in rows)

    print(f"Lemmas under {module_name}:")
    for name, desc in rows:
        print(f"  {name:<{width}}  {desc}")
    return 0


def _cmd_list_defs(args: argparse.Namespace) -> int:
    """Reflect over definitional macros and print a simple index."""
    package = args.package
    rel_module = getattr(args, "module", "propositional.hilbert.definitions")

    if rel_module:
        module_name = f"{package}.{rel_module}"
    else:
        module_name = package

    try:
        root_module = importlib.import_module(module_name)
    except Exception as e:
        print(f"Error: Failed to import module '{module_name}': {e}", file=sys.stderr)
        return 1

    modules: list[object] = []
    if hasattr(root_module, "__path__"):
        modules.append(root_module)
        for info in pkgutil.walk_packages(root_module.__path__, root_module.__name__ + "."):
            try:
                submod = importlib.import_module(info.name)
            except Exception:
                continue
            modules.append(submod)
    else:
        modules.append(root_module)

    collected: dict[str, object] = {}
    for module in modules:
        definitions = getattr(module, "DEFINITIONS", None)
        if not isinstance(definitions, dict):
            continue
        for name, definition in definitions.items():
            if name not in collected:
                collected[name] = definition

    if not collected:
        print(f"No DEFINITIONS mapping found under '{module_name}'.")
        return 0

    rows: list[tuple[str, str]] = []
    for name in sorted(collected):
        definition = collected[name]
        doc = getattr(definition, "doc", "") or ""
        first_line = ""
        for line in str(doc).strip().splitlines():
            stripped = line.strip()
            if stripped:
                first_line = stripped
                break
        rows.append((name, first_line))

    width = max(len(name) for name, _ in rows)
    print(f"Definitions under {module_name}:")
    for name, desc in rows:
        print(f"  {name:<{width}}  {desc}")
    return 0


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

    # --- init ---
    p_init = sub.add_parser("init", help="Initialize a new project")
    p_init.add_argument("name", help="Project directory name")
    p_init.add_argument(
        "--mode",
        choices=["package", "proof"],
        default="package",
        help="Project mode (default: package)",
    )
    p_init.add_argument(
        "--package",
        help="Python package name (package mode only; defaults to project name)",
    )
    p_init.set_defaults(func=_cmd_init)

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

    # --- list-lemmas (doc tooling) ---
    p_list = sub.add_parser(
        "list-lemmas", help="List lemma constructors for a logic package"
    )
    p_list.add_argument("package", help="Root package (e.g. 'logic')")
    p_list.add_argument(
        "--module",
        default="propositional.hilbert.lemmas",
        help="Module path relative to package (default: 'propositional.hilbert.lemmas')",
    )
    p_list.set_defaults(func=_cmd_list_lemmas)

    # --- list-defs (doc tooling) ---
    p_defs = sub.add_parser(
        "list-defs", help="List definitional macros for a logic package"
    )
    p_defs.add_argument("package", help="Root package (e.g. 'logic')")
    p_defs.add_argument(
        "--module",
        default="propositional.hilbert.definitions",
        help="Module path relative to package (default: 'propositional.hilbert.definitions')",
    )
    p_defs.set_defaults(func=_cmd_list_defs)

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
