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

from skfd.authoring.emit import emit_axioms, emit_lemmas, emit_lowered_lemmas
from skfd.authoring.parsing import wff
from skfd.builder import MMBuilder
from skfd.config import load_config
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.verifier.aggregate import run_all, summarize

HilbertSystem = Any

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
    Get HilbertSystem instance.
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
        return mod.HilbertSystem.make(interner=SymbolInterner())
    except Exception as err:
        # If logic package is missing, fallback to a minimal dummy system or raise clear error
        # Actually, for minimal scripts, we can construct a minimal HilbertSystem locally if needed
        # But usually this means PYTHONPATH is wrong or user didn't install logic package.
        # However, to be nice to standalone usage without the full logic repo:
        raise RuntimeError(
            "Could not auto-create HilbertSystem (metamath-logic module not found). "
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
        return 0
        
    # Verify
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mm", delete=False, mode="w") as tmp:
        mm_path = Path(tmp.name)
        
    try:
        print(f"Emitting {len(proofs)} proofs to Metamath...", end=" ", flush=True)
        origin_table = OriginTable()
        builder = MMBuilder(
            interner=hs.interner,
            origin_table=origin_table,
            module_id=script_path.stem
        )
        
        # Heuristic: declare basic types if missing
        builder.c("wff") 
        
        emit_axioms(builder, hs)
        def _emit_rule_skeleton() -> None:
            if "mp" in builder._labels:
                return

            symtab = hs.interner.symbol_table()
            wi_wff = hs.compile(wff("ph -> ps"), ctx="rule[wi]")
            wn_wff = hs.compile(wff("-. ph"), ctx="rule[wn]")
            wa_wff = hs.compile(wff("( ph /\\ ps )"), ctx="rule[wa]")
            phi_wff = hs.compile(wff("ph"), ctx="rule[mp.phi]")
            psi_wff = hs.compile(wff("ps"), ctx="rule[mp.psi]")
            imp_wff = hs.compile(wff("( ph -> ps )"), ctx="rule[mp.imp]")

            const_ids: set[int] = set()
            var_ids: set[int] = set()

            for w_ in [wi_wff, wn_wff, wa_wff, phi_wff, psi_wff, imp_wff]:
                for sid in w_.tokens:
                    s = symtab[sid]
                    if s.kind == "Const":
                        const_ids.add(s.id)
                    elif s.kind == "Var":
                        var_ids.add(s.id)

            token_map: dict[int, str] = {}
            const_names: list[str] = []
            for sid in sorted(const_ids):
                name = f"c{sid}"
                token_map[sid] = name
                const_names.append(name)

            for sid in sorted(var_ids):
                token_map[sid] = f"v{sid}"

            extra_consts = [name for name in const_names if name not in builder._constants]
            if extra_consts:
                builder.c(*extra_consts)

            def _render(w_) -> str:
                return " ".join(token_map[sid] for sid in w_.tokens)

            for label, w_ in {"wi": wi_wff, "wn": wn_wff, "wa": wa_wff}.items():
                builder.a(label, "wff", _render(w_))

            with builder.block():
                builder.e("mp.1", "wff", _render(phi_wff))
                builder.e("mp.2", "wff", _render(imp_wff))
                builder.a("mp", "wff", _render(psi_wff))

        _emit_rule_skeleton()

        referenced: set[str] = set()
        for p in proofs:
            for st in getattr(p, "steps", ()):
                if getattr(st, "op", None) == "ref":
                    ref = getattr(st, "ref", None)
                    if isinstance(ref, str) and ref:
                        referenced.add(ref)

        missing_refs = {ref for ref in referenced if ref not in hs.compile_axioms()}
        missing_refs -= {"wi", "wn", "wa", "mp"}

        if missing_refs:
            try:
                dep_proofs = []
                mod = importlib.import_module("logic.propositional.hilbert.theorems")
                cat = getattr(mod, "SETMM_TO_HILBERT_LEMMAS", {})
                for ref_label in sorted(missing_refs):
                    ctor = cat.get(ref_label)
                    if ctor is not None:
                        dep_proofs.append(ctor(hs))
                if dep_proofs:
                    emit_lemmas(builder, hs, dep_proofs)
            except Exception:
                pass

        emit_lowered_lemmas(builder, hs, proofs)
        mm_path.write_text(builder.render(), encoding="utf-8")
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
