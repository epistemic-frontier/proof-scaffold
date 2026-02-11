# skfd/driver/script_runner.py
from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from skfd.authoring.emit import emit_axioms, emit_lowered_lemmas
from skfd.authoring.parsing import wff
from skfd.builder_v2 import MMBuilderV2
from skfd.config import load_config
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver
from skfd.verifier.aggregate import run_all, summarize

System = Any

def _discover_proof_functions(module: ModuleType) -> list[tuple[str, Callable[..., Any]]]:
    """Find all functions starting with 'prove_' in the module."""
    proofs = []
    for name, obj in inspect.getmembers(module):
        if name.startswith("prove_") and inspect.isfunction(obj):
            proofs.append((name, cast(Callable[..., Any], obj)))
    # Sort by line number to run in definition order
    proofs.sort(key=lambda x: x[1].__code__.co_firstlineno)
    return proofs

def _get_or_create_system(module: ModuleType) -> Any:
    """
    Get System instance.
    Strategy:
    1. Look for 'system' or 'sys' variable in module.
    2. Look for 'build()' or 'get_system()' function.
    3. Fallback: Default construction for logic.propositional.hilbert.
    """
    # 1. Variable
    if hasattr(module, "system"):
        return module.system
    if hasattr(module, "sys") and not isinstance(module.sys, ModuleType): # sys module check
        return module.sys
        
    # 2. Function
    if hasattr(module, "build") and callable(module.build):
        return module.build()
    if hasattr(module, "get_system") and callable(module.get_system):
        return module.get_system()
        
    # 3. Fallback
    try:
        mod = importlib.import_module("logic.propositional.hilbert")
        return mod.System.make(interner=SymbolInterner(), names=NameResolver())
    except Exception as err:
        # If logic package is missing, fallback to a minimal dummy system or raise clear error
        # Actually, for minimal scripts, we can construct a minimal System locally if needed
        # But usually this means PYTHONPATH is wrong or user didn't install logic package.
        # However, to be nice to standalone usage without the full logic repo:
        raise RuntimeError(
            "Could not auto-create System (metamath-logic module not found). "
            "Please ensure PYTHONPATH includes the logic package or define 'sys' in your script."
        ) from err

def verify_script(script_path: Path, project_root: Path | None = None) -> int:
    """
    Load a script, run proof functions, and verify results.
    """
    spec = importlib.util.spec_from_file_location("user_script", script_path)
    if spec is None or spec.loader is None:
        print(f"Error: Could not load script {script_path}", file=sys.stderr)
        return 1
        
    module = importlib.util.module_from_spec(spec)
    sys.modules["user_script"] = module
    
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"Error executing script {script_path}: {e}", file=sys.stderr)
        return 1
        
    # Discover proofs
    proof_funcs = _discover_proof_functions(module)
    if not proof_funcs:
        print(f"No 'prove_*' functions found in {script_path}")
        return 0
        
    print(f"Found {len(proof_funcs)} proof(s): {', '.join(n for n, _ in proof_funcs)}")
    
    # Setup System
    try:
        hs = _get_or_create_system(module)
    except Exception as e:
        print(f"Error initializing system: {e}", file=sys.stderr)
        return 1
        
    # Run Proofs
    proofs = []
    for name, func in proof_funcs:
        print(f"Running {name}...", end=" ", flush=True)
        try:
            # Inject sys if the function expects arguments
            sig = inspect.signature(func)
            if len(sig.parameters) > 0:
                p = func(hs)
            else:
                p = func()
            
            if p:
                proofs.append(p)
                print(f"OK ({p.name})")
            else:
                print("OK (No proof returned)")
        except Exception as e:
            print("FAIL")
            print(f"Error in {name}: {e}", file=sys.stderr)
            return 1
            
    if not proofs:
        print("No proof objects returned to verify.")
        return 1
        
    # Verify
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mm", delete=False, mode="w") as tmp:
        mm_path = Path(tmp.name)
        
    try:
        print(f"Emitting {len(proofs)} proofs to Metamath...", end=" ", flush=True)
        origin_table = OriginTable()
        names = NameResolver()
        mm = MMBuilderV2(
            interner=hs.interner,
            origin_table=origin_table,
            names=names,
            unit_id=script_path.stem,
            origin_module_id=script_path.stem,
        )

        wff_tc = mm.sym.const("wff")

        emit_axioms(mm, hs)
        def _emit_rule_skeleton() -> None:
            axioms = hs.compile_axioms()
            if "mp" in axioms:
                return

            compile_fn = getattr(hs, "compile", None)
            if compile_fn is None:
                compile_fn = getattr(hs, "_compile", None)
            if compile_fn is None:
                raise RuntimeError("System is missing compile()")

            wi_wff = compile_fn(wff("ph -> ps"), ctx="rule[wi]")
            wn_wff = compile_fn(wff("-. ph"), ctx="rule[wn]")
            wa_wff = compile_fn(wff("( ph /\\ ps )"), ctx="rule[wa]")
            phi_wff = compile_fn(wff("ph"), ctx="rule[mp.phi]")
            psi_wff = compile_fn(wff("ps"), ctx="rule[mp.psi]")
            imp_wff = compile_fn(wff("( ph -> ps )"), ctx="rule[mp.imp]")

            if "wi" not in axioms:
                mm.a(mm.sym.label("wi"), tc=wff_tc, expr=wi_wff.tokens)
            if "wn" not in axioms:
                mm.a(mm.sym.label("wn"), tc=wff_tc, expr=wn_wff.tokens)
            if "wa" not in axioms:
                mm.a(mm.sym.label("wa"), tc=wff_tc, expr=wa_wff.tokens)

            with mm.block():
                mm.e(mm.sym.label("mp.1"), tc=wff_tc, expr=phi_wff.tokens)
                mm.e(mm.sym.label("mp.2"), tc=wff_tc, expr=imp_wff.tokens)
                mm.a(mm.sym.label("mp"), tc=wff_tc, expr=psi_wff.tokens)

        _emit_rule_skeleton()

        compiled_axioms = hs.compile_axioms()
        reserved = {"wi", "wn", "wa", "mp"}

        def _refs(p: Any) -> set[str]:
            refs: set[str] = set()
            for st in getattr(p, "steps", ()):
                if getattr(st, "op", None) != "ref":
                    continue
                ref = getattr(st, "ref", None)
                if isinstance(ref, str) and ref:
                    refs.add(ref)
            return refs

        try:
            mod = importlib.import_module("logic.propositional.hilbert.theorems")
            cat = getattr(mod, "SETMM_TO_HILBERT_LEMMAS", {})
        except Exception:
            cat = {}

        queue: list[Any] = list(proofs)
        lemma_by_name: dict[str, Any] = {}
        while queue:
            p = queue.pop(0)
            lemma_name = getattr(p, "name", None)
            if not isinstance(lemma_name, str) or not lemma_name:
                continue
            if lemma_name in lemma_by_name:
                continue
            lemma_by_name[lemma_name] = p
            for ref in _refs(p):
                if ref in compiled_axioms or ref in reserved:
                    continue
                if ref in lemma_by_name:
                    continue
                ctor = cat.get(ref)
                if ctor is not None:
                    queue.append(ctor(hs))

        unresolved: set[str] = set()
        for p in lemma_by_name.values():
            for ref in _refs(p):
                if ref in compiled_axioms or ref in reserved or ref in lemma_by_name:
                    continue
                unresolved.add(ref)
        if unresolved:
            raise RuntimeError(f"unresolved lemma references: {sorted(unresolved)}")

        emit_lowered_lemmas(mm, hs, list(lemma_by_name.values()), label_ids=None)
        unit = mm.finish()
        res = LinkerV1.link(
            units=[unit],
            origin_table=origin_table,
            interner=hs.interner,
            conformance_level=0,
        )
        mm_path.write_text(res.mm_text, encoding="utf-8")
        print("OK")
        
        # Run Verifiers
        cfg = load_config(project_root)
        active_cmds = cfg.get_active_commands()
        if not active_cmds:
            print("Warning: No active verifiers configured.")
            
        results = run_all(mm_path, active_cmds)
        print("\n" + "="*20 + " VERIFICATION SUMMARY " + "="*20)
        print(summarize(results))
        
        failed = any(not r.passed for r in results)
        if failed:
            for r in results:
                if not r.passed:
                    print(f"\n❌ {r.name} FAILED:\n{r.output.strip()}")
            return 1
            
        return 0
        
    except Exception as e:
        print(f"\nVerification process failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup usually handled by OS / tempfile, but we explicit here if needed
        # For debugging, we leave it or print it
        # print(f"Artifact: {mm_path}")
        pass
