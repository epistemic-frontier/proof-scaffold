# skfd/cli.py
"""
skfd: The ProofScaffold CLI
"""

from __future__ import annotations

import argparse
import importlib
import logging
import os
import pkgutil
import platform
import sys
import traceback
from pathlib import Path

from skfd.core.diag import LinkerDiagError
from skfd.driver.runner import DriverRunner
from skfd.verifier import verify
from skfd.verifier.aggregate import VerifierResult, summarize
from skfd.api_v2 import BuildConfig
from skfd.web.theorem_browser import (
    build_mm_context_bundle,
    build_theorem_graph,
    serve as serve_theorem_browser,
)

from .config import VerifierConfig, load_config, save_config
from .doctor.alignment import check_alignment
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
    from skfd.examples.minimal_ok import run as run_example

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
    from skfd.examples.minimal_diag import run as run_example

    run_example()
    # minimal_diag is expected to fail before emission; keep side effects minimal.
    if write_mm:
        raise AssertionError("minimal_diag should not emit")


def _cmd_doctor_align(args: argparse.Namespace) -> int:
    """Check alignment with set.mm and Hilbert systems."""
    try:
        check_alignment()
        return 0
    except Exception as e:
        print(f"Alignment check failed: {e}", file=sys.stderr)
        return 1


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

    all_passed = True
    agg_results: list[VerifierResult] = []

    for name, cmd in active_cmds:
        print(f"===[{name}]===")
        try:
            print("Running sanity check...")
            run_sanity(cmd)
            print("Running minimal_ok example...")
            _run_example_minimal_ok(cmd, write_mm=not args.no_write)
            print(f"[{name}] accepted")
            agg_results.append(
                VerifierResult(name=name, passed=True, returncode=0, output="")
            )
        except Exception as e:
            print(f"[{name}] failed")
            print(f"    Error: {e}")
            agg_results.append(
                VerifierResult(name=name, passed=False, returncode=1, output=str(e))
            )
            all_passed = False

    if agg_results:
        print("\nSummary:")
        print(summarize(agg_results))

    return 0 if all_passed else 1


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


def _cmd_init_pkg(args: argparse.Namespace) -> int:
    """Initialize a new logic package."""
    name = args.name
    root = (args.root or Path.cwd())
    pkg_name = name.replace("-", "_")
    pkg_dir = root / "src" / pkg_name

    if pkg_dir.exists():
        print(f"Error: Directory {pkg_dir} already exists.", file=sys.stderr)
        return 1

    print(f"Initializing package '{name}' at {pkg_dir}...")
    pkg_dir.mkdir(parents=True)

    # __init__.py
    (pkg_dir / "__init__.py").touch()

    # build.py
    build_py = pkg_dir / "build.py"
    build_py.write_text("""
from logic.propositional.hilbert import HilbertSystem
from skfd.core.symbols import SymbolInterner

def build():
    interner = SymbolInterner()
    # Create your system here
    sys = HilbertSystem.make(interner=interner)
    return sys
""".strip() + "\n", encoding="utf-8")

    # pyproject.toml
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.exists():
        pyproject_path.write_text(
            f"""[build-system]
requires = [\"setuptools>=68\", \"wheel\"]
build-backend = \"setuptools.build_meta\"

[project]
name = \"{pkg_name}\"
version = \"0.0.1\"
requires-python = \">=3.10\"

dependencies = [
  \"proof-scaffold\",
]

[tool.setuptools.packages.find]
where = [\"src\"]
""",
            encoding="utf-8",
        )

    # .skfd config in root
    cfg_path = root / ".skfd"
    if not cfg_path.exists():
        print(f"Creating default config at {cfg_path}...")
        # Create default config with mmverify
        from .config import SkfdConfig, save_config
        cfg = SkfdConfig(active_verifiers=["mmverify"])
        save_config(cfg, root)

    print("Done.")
    return 0


def _cmd_init_proof(args: argparse.Namespace) -> int:
    """Initialize a standalone proof script."""
    name = args.name
    if not name.endswith(".py"):
        name += ".py"

    path = Path(name)
    if path.exists():
        print(f"Error: File {path} already exists.", file=sys.stderr)
        return 1

    root = (args.root or Path.cwd())
    cfg_path = root / ".skfd"
    if not cfg_path.exists():
        print(f"Creating default config at {cfg_path}...")
        from .config import SkfdConfig, save_config
        cfg = SkfdConfig(active_verifiers=["mmverify"])
        save_config(cfg, root)

    print(f"Creating proof script '{path}'...")
    path.write_text("""
import sys
from pathlib import Path
import tempfile
import os

# Helper to ensure project root is in path if needed
ROOT = Path(__file__).resolve().parents[1]

from skfd.core.symbols import SymbolInterner
from skfd.builder_v2 import MMBuilderV2
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver
from skfd.authoring.emit import emit_axioms, emit_lemmas
from skfd.verifier.aggregate import run_all, summarize
from skfd.core.origin import OriginTable
from skfd.config import load_config

from logic.propositional.hilbert import HilbertSystem
from logic.propositional.hilbert.lemmas import LemmaBuilder, LemmaProof

def verify_proofs(hs: HilbertSystem, proofs: list[LemmaProof]) -> None:
    print(f"\\nVerifying {len(proofs)} proofs...")
    
    with tempfile.NamedTemporaryFile(suffix=".mm", delete=False, mode="w") as tmp:
        mm_path = Path(tmp.name)
    
    try:
        origin_table = OriginTable()
        names = NameResolver()
        mm = MMBuilderV2(
            interner=hs.interner,
            origin_table=origin_table,
            names=names,
            unit_id="manual_verify",
            origin_module_id="manual_verify",
        )
        mm.sym.const("wff")
        emit_axioms(mm, hs)
        emit_lemmas(mm, hs, proofs)

        unit = mm.finish()
        res = LinkerV1.link(
            units=[unit],
            origin_table=origin_table,
            interner=hs.interner,
            conformance_level=0,
        )
        mm_path.write_text(res.mm_text, encoding="utf-8")
        print(f"Generated .mm file at: {mm_path}")

        # Use skfd config to find verifiers
        cfg = load_config(ROOT)
        active_cmds = cfg.get_active_commands()
        
        if not active_cmds:
            print("Warning: No active verifiers found in .skfd. Using default mmverify.")
            # Fallback logic is handled by cfg.get_active_commands() usually returning mmverify if empty?
            # Actually load_config defaults to mmverify if active list is empty.
        
        results = run_all(mm_path, active_cmds)
        print("\\n" + "="*20 + " VERIFICATION SUMMARY " + "="*20)
        print(summarize(results))
        
        failed = False
        for r in results:
            if not r.passed:
                failed = True
                print(f"\\n❌ {r.name} FAILED:\\n{r.output}")
        
        if failed:
            sys.exit(1)
                
    finally:
        # os.unlink(mm_path)
        print(f"(Temporary file kept at {mm_path})")

def prove_example(sys: HilbertSystem) -> LemmaProof:
    lb = LemmaBuilder(sys, "example_lemma")
    # A simple proof: ph -> ph
    h1 = lb.step("s1", "ph -> ph", "A1 with (phi, psi)=(ph, ph)") 
    # This is just a dummy step, normally you use A1 properly
    # See logic.propositional.hilbert.lemmas for real examples
    
    # Real L1_id proof for demonstration:
    # 1. ph -> (ph -> ph) (A1)
    # 2. (ph -> ((ph -> ph) -> ph)) -> ((ph -> (ph -> ph)) -> (ph -> ph)) (A2)
    # ...
    # For now let's just assume we want to prove something simple or use existing lemmas
    
    # Let's just return a dummy proof object to show it works
    # In reality you would use lb.step(), lb.mp() etc.
    # Here we just re-use a known lemma construction if available or fail
    
    return lb.build(lb.step("dummy", "ph -> (ps -> ph)", "A1"))

def run():
    interner = SymbolInterner()
    sys = HilbertSystem.make(interner=interner)
    
    print("Constructing proofs...")
    # proof = prove_example(sys)
    # verify_proofs(sys, [proof])
    print("Edit this script to add your proofs!")
    
    # Example usage:
    # verify_proofs(sys, [])

if __name__ == "__main__":
    run()
""".strip() + "\n", encoding="utf-8")

    print("Done. Run it with: skfd verify " + str(path))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    """Run driver verification for a package OR execute a proof script."""

    # Check if 'package' argument looks like a file script
    target_arg = args.package
    target_path = Path(target_arg)

    if target_path.suffix == ".py" or (target_path.exists() and target_path.is_file()):
        print(f"Verifying script: {target_path} ...")
        # Magic Runner Mode
        from skfd.driver.script_runner import verify_script
        return verify_script(target_path, args.root)

    root = (args.root or Path.cwd()) / "src"
    target = (args.root or Path.cwd()) / "target"

    if not root.exists():
        print(f"Error: Source directory not found: {root}", file=sys.stderr)
        return 1

    print(f"Initializing build driver (src={root}, target={target})...")
    runner = DriverRunner(root, target)
    level = getattr(args, "level", 0)
    runner.cfg = BuildConfig(
        auto_f=getattr(getattr(runner, "cfg", None), "auto_f", True),
        warn_raw=True,
        forbid_raw=level >= 1,
    )

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
        agg_results: list[VerifierResult] = []
        for name, cmd in active_cmds:
            print(f"[{name}] Verifying {outfile.name}... ", end="", flush=True)
            try:
                verify(cmd, outfile)
                print("OK")
                agg_results.append(VerifierResult(name=name, passed=True, returncode=0, output=""))
            except Exception as e:
                print("FAIL")
                print(f"    Error: {e}")
                agg_results.append(VerifierResult(name=name, passed=False, returncode=1, output=str(e)))
                all_passed = False

        if all_passed:
            print("Verification completed successfully.")
            print("\nSummary:")
            print(summarize(agg_results))
            return 0
        else:
            print("Verification FAILED (some verifiers failed).", file=sys.stderr)
            print("\nSummary:")
            print(summarize(agg_results))
            return 1

    except Exception as e:
        print(f"Verification failed: {e}", file=sys.stderr)
        _print_friendly_hint(e)
        traceback.print_exc()
        return 1


def _cmd_serve(args: argparse.Namespace) -> int:
    root_dir = args.root or Path.cwd()
    root = root_dir / "src"
    target = root_dir / "target"

    if not root.exists():
        print(f"Error: Source directory not found: {root}", file=sys.stderr)
        return 1

    print(f"Initializing build driver (src={root}, target={target})...")
    runner = DriverRunner(root, target)
    level = getattr(args, "level", 0)
    runner.cfg = BuildConfig(
        auto_f=getattr(getattr(runner, "cfg", None), "auto_f", True),
        warn_raw=True,
        forbid_raw=level >= 1,
    )

    try:
        print("Building all packages...")
        runner.execute_all()

        if not runner.lirs:
            print(
                f"Error: No build units discovered under {root} (expected build.py files).",
                file=sys.stderr,
            )
            return 1

        pkg = args.package
        if pkg not in runner.lirs and "." in pkg:
            root_pkg = pkg.split(".", 1)[0]
            if root_pkg in runner.lirs:
                print(
                    f"Package '{pkg}' not found as a build unit; "
                    f"falling back to top-level package '{root_pkg}'."
                )
                pkg = root_pkg

        if pkg not in runner.lirs:
            print(
                f"Error: Build unit '{pkg}' not found (discovered: {sorted(runner.lirs.keys())}).",
                file=sys.stderr,
            )
            return 1

        chain = runner._get_transitive_deps(pkg)
        chain.append(pkg)
        units = [runner.lirs[n] for n in chain]
        graph = build_theorem_graph(
            units=units,
            origin_table=runner.origin_table,
            interner=runner.interner,
            conformance_level=level,
            project_root=root_dir,
        )
        mm = build_mm_context_bundle(
            units=units,
            origin_table=runner.origin_table,
            interner=runner.interner,
            conformance_level=level,
        )

        host = getattr(args, "host", "127.0.0.1")
        port = int(getattr(args, "port", 8000))
        print(f"Serving theorem browser for '{pkg}' on http://{host}:{port}/")
        serve_theorem_browser(
            graph=graph, mm=mm, host=host, port=port, project_root=root_dir
        )
        return 0
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    except Exception as e:
        print(f"Serve failed: {e}", file=sys.stderr)
        _print_friendly_hint(e)
        traceback.print_exc()
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
    level = getattr(args, "level", 0)
    runner.cfg = BuildConfig(
        auto_f=getattr(getattr(runner, "cfg", None), "auto_f", True),
        warn_raw=True,
        forbid_raw=level >= 1,
    )

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
        _print_friendly_hint(e)
        traceback.print_exc()
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


def _configure_path(root: Path | None) -> None:
    """Auto-configure sys.path for workspace layouts."""
    if not root:
        root = Path.cwd()

    # 1. Add root
    sys.path.insert(0, str(root))

    # 2. Add 'src' if exists
    src = root / "src"
    if src.exists():
        sys.path.insert(0, str(src))

    # 3. Add '*/src' (e.g. metamath-logic/src)
    for p in root.glob("*/src"):
        if p.is_dir():
            sys.path.insert(0, str(p))


def _configure_logging() -> None:
    """Enable default logging for CLI runs."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s",
    )


def _print_friendly_hint(exc: Exception) -> None:
    """Emit actionable hints for common setup errors."""
    if isinstance(exc, ImportError):
        msg = str(exc)
        if "No module named 'prelude'" in msg:
            print(
                "Hint: 'prelude' not found. In dev mode, add metamath-prelude/src "
                "to PYTHONPATH or install metamath-prelude.",
                file=sys.stderr,
            )
        if "No module named 'logic'" in msg:
            print(
                "Hint: 'logic' not found. In dev mode, add metamath-logic/src "
                "to PYTHONPATH or install metamath-logic.",
                file=sys.stderr,
            )
    if isinstance(exc, RuntimeError) and "No active dependencies context" in str(exc):
        print(
            "Hint: this build.py was executed outside 'skfd'. "
            "Run via 'python -m skfd.cli verify <project-name>'.",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    p = argparse.ArgumentParser(prog="skfd", description="ProofScaffold CLI")
    p.add_argument("--root", type=Path, help="Project root", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- init-pkg ---
    p_init_pkg = sub.add_parser("init-pkg", help="Initialize a new logic package")
    p_init_pkg.add_argument("name", help="Name of the package")
    p_init_pkg.set_defaults(func=_cmd_init_pkg)

    # --- init-proof ---
    p_init_proof = sub.add_parser("init-proof", help="Initialize a standalone proof script")
    p_init_proof.add_argument("name", help="Filename for the script (e.g. my_proof.py)")
    p_init_proof.set_defaults(func=_cmd_init_proof)

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

    # align
    p_doc_align = doc_sub.add_parser("align", help="Check alignment with set.mm")
    p_doc_align.set_defaults(func=_cmd_doctor_align)

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
    p_verify = sub.add_parser(
        "verify",
        help="Build and verify a project (or run a standalone proof script)",
    )
    p_verify.add_argument(
        "package",
        metavar="TARGET",
        help="Project name from pyproject.toml ([project].name), or a .py proof script",
    )
    p_verify.add_argument(
        "--level",
        type=int,
        default=0,
        choices=[0, 1, 2],
        help="Conformance level (0=Loose, 1=Strict Interface, 2=FOL)",
    )
    p_verify.set_defaults(func=_cmd_verify)

    # --- serve (theorem browser) ---
    p_serve = sub.add_parser(
        "serve", help="Serve a local theorem dependency browser for a project"
    )
    p_serve.add_argument(
        "package",
        metavar="TARGET",
        help="Project name from pyproject.toml ([project].name)",
    )
    p_serve.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default: 127.0.0.1)",
    )
    p_serve.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port (default: 8000)",
    )
    p_serve.add_argument(
        "--level",
        type=int,
        default=0,
        choices=[0, 1, 2],
        help="Conformance level (0=Loose, 1=Strict Interface, 2=FOL)",
    )
    p_serve.set_defaults(func=_cmd_serve)

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

    root = args.root or Path.cwd()
    _configure_path(root)

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
