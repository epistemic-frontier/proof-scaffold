from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path
from typing import Any

from skfd.authoring.dsl import compile_wff
from skfd.authoring.formula import Formula, Wff, render

SETMM_PATH = Path("set.mm/set.mm")


def _ensure_repo_paths() -> None:
    root = Path.cwd()
    for rel in (
        "metamath-logic/src",
        "metamath-prelude/src",
        "proof-scaffold/src",
        "metamath-set/src",
    ):
        p = (root / rel).resolve()
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))

def get_setmm_stmt(label: str) -> str | None:
    """Find the statement of a theorem/axiom in set.mm.
    Supports both $p (theorem) and $a (axiom) entries.
    Extracts content between '|-' and end marker ('$=' for $p, '$.' for $a).
    """
    if not SETMM_PATH.exists():
        print(f"set.mm not found at {SETMM_PATH}")
        return None

    # Grep for the label definition
    # Pattern: "^label $p" or " label $p"
    cmd_p = ["grep", "-n", f" {label} \\$p", str(SETMM_PATH)]
    res_p = subprocess.run(cmd_p, capture_output=True, text=True)

    line = None
    end_marker = "$="
    if res_p.returncode == 0 and res_p.stdout.strip():
        line = res_p.stdout.strip().splitlines()[0]
        end_marker = "$="
    else:
        cmd_a = ["grep", "-n", f" {label} \\$a", str(SETMM_PATH)]
        res_a = subprocess.run(cmd_a, capture_output=True, text=True)
        if res_a.returncode != 0 or not res_a.stdout.strip():
            return None
        line = res_a.stdout.strip().splitlines()[0]
        end_marker = "$."
        
    # Format: line_num: label $p |- ( ... ) $=   or   line_num: label $a |- ( ... ) $.
    parts = line.split(":", 1)
    if len(parts) < 2:
        return None
        
    content = parts[1].strip()
    
    # Extract content between '|-' and end marker
    if "|-" not in content or end_marker not in content:
        # Handle multi-line statements
        # If end marker is not in the first line, read subsequent lines
        try:
            with open(SETMM_PATH, encoding="latin-1") as f:
                # grep gave us line number (1-based)
                line_num = int(parts[0])
                f.seek(0)
                # Skip to the line
                for _ in range(line_num - 1):
                    f.readline()
                
                # Read lines until we find the end marker
                full_stmt = ""
                found_end = False
                
                # Read the current line from file (replacing the grep output which has line numbers)
                current_line = f.readline()
                while current_line:
                    full_stmt += " " + current_line.strip()
                    if end_marker in current_line:
                        found_end = True
                        break
                    current_line = f.readline()
                
                if found_end:
                    content = full_stmt
                    # Re-parse content
                    if "|-" in content:
                         start = content.find("|-") + 2
                         end = content.find(end_marker)
                         stmt_raw = content[start:end].strip()
                         stmt_clean = " ".join(stmt_raw.split())
                         return stmt_clean
        except Exception as e:
            print(f"Error reading multi-line statement: {e}")
            return None

        return None
        
    start = content.find("|-") + 2
    end = content.find(end_marker)
    stmt_raw = content[start:end].strip()
    
    # Normalize spaces
    stmt_clean = " ".join(stmt_raw.split())
    return stmt_clean

def compile_zfc_expr(pred: Any, expr: Any, ctx: str) -> Any:
    # 1. Get base environment
    env, registry = pred.author_env()
    
    # 2. Intern new symbols
    interner = pred.interner
    # Use global module ID for stability
    mod_id = "__zfc_defs__" 
    
    def get_sym(name: str) -> int:
        return int(
            interner.intern(
                origin_module_id=mod_id,
                local_name=name,
                kind="Const",
                origin_ref=None,
            )
        )

    subq = get_sym("C_")
    uni = get_sym("U.")
    un = get_sym("u.")
    in_ = get_sym("i^i")
    pw = get_sym("~P")
    sn_l = get_sym("{")
    sn_r = get_sym("}")
    pipe = get_sym("|")
    comma = get_sym(",")
    dif = get_sym("\\")
    
    # 3. Add builders
    # We need to map authoring Constructor names (from _structures.py) to builders
    
    # Ab: { x | ph }
    env.ctor_builders["Ab"] = lambda b, xs: Formula("class", (sn_l, *xs[0].tokens, pipe, *xs[1].tokens, sn_r))
    
    # Subq: A C_ B
    env.ctor_builders["C_"] = lambda b, xs: Wff("wff", (*xs[0].tokens, subq, *xs[1].tokens))
    
    # Pw: ~P A
    env.ctor_builders["~P"] = lambda b, xs: Formula("class", (pw, *xs[0].tokens))
    
    # Uni: U. A
    env.ctor_builders["U."] = lambda b, xs: Formula("class", (uni, *xs[0].tokens))
    
    # Un: ( A u. B )
    lp = pred.builtins.lp
    rp = pred.builtins.rp
    env.ctor_builders["u."] = lambda b, xs: Formula("class", (lp, *xs[0].tokens, un, *xs[1].tokens, rp))
    
    # In: ( A i^i B )
    env.ctor_builders["i^i"] = lambda b, xs: Formula("class", (lp, *xs[0].tokens, in_, *xs[1].tokens, rp))
    
    # Sn: { A }
    env.ctor_builders["Sn"] = lambda b, xs: Formula("class", (sn_l, *xs[0].tokens, sn_r))
    
    # Pr: { A , B }
    env.ctor_builders["Pr"] = lambda b, xs: Formula("class", (sn_l, *xs[0].tokens, comma, *xs[1].tokens, sn_r))
    
    # Dif: ( A \ B )
    env.ctor_builders["\\"] = lambda b, xs: Formula("class", (lp, *xs[0].tokens, dif, *xs[1].tokens, rp))
    
    # 4. Compile
    return compile_wff(expr, env=env, registry=registry)

def check_alignment() -> None:
    print("Checking alignment between set.mm and Hilbert system...")
    _ensure_repo_paths()

    pred_mod = importlib.import_module("logic.predicate.hilbert")
    prop_mod = importlib.import_module("logic.propositional.hilbert")
    prop_theorems = importlib.import_module("logic.propositional.hilbert.theorems")
    set_theory_mod = importlib.import_module("set_theory")
    set_axioms_mod = importlib.import_module("set_theory.axioms")
    set_defs_mod = importlib.import_module("set_theory.definitions")
    set_thms_mod = importlib.import_module("set_theory.theorems")

    SETMM_TO_PREDICATE_AXIOMS = pred_mod.SETMM_TO_PREDICATE_AXIOMS
    PredicateSystem = pred_mod.PredicateSystem
    make = prop_mod.make
    SETMM_TO_HILBERT_LEMMAS = prop_theorems.SETMM_TO_HILBERT_LEMMAS

    SETMM_TO_ZFC_AXIOMS = set_theory_mod.SETMM_TO_ZFC_AXIOMS
    SETMM_TO_ZFC_DEFINITIONS = set_theory_mod.SETMM_TO_ZFC_DEFINITIONS
    SETMM_TO_ZFC_THEOREMS = set_theory_mod.SETMM_TO_ZFC_THEOREMS

    make_zfc_axioms = set_axioms_mod.make_axioms
    make_zfc_definitions = set_defs_mod.make_definitions
    make_zfc_theorems = set_thms_mod.make_theorems
    
    from skfd.core.symbols import SymbolInterner
    interner = SymbolInterner()
    sys = make(interner=interner)
    pred = PredicateSystem.make(interner=interner)
    
    # symtab = interner.symbol_table() # Moved inside loop
    
    success_count = 0
    fail_count = 0
    
    for label, lemma_ctor in SETMM_TO_HILBERT_LEMMAS.items():
        print(f"Checking {label}...")
        
        # 1. Get set.mm statement
        setmm_stmt = get_setmm_stmt(label)
        if not setmm_stmt:
            print(f"  [WARN] Could not find or parse '{label}' in set.mm")
            fail_count += 1
            continue
            
        # 2. Get local lemma statement
        try:
            proof = lemma_ctor(sys)
            # Refresh symtab to include newly interned variables
            symtab = interner.symbol_table()
            local_stmt = render(proof.statement.tokens, symtab=symtab)
            # Render usually produces "( phi -> psi )". set.mm also uses that format.
            # We might need to strip outer parens if set.mm includes them or not?
            # set.mm: |- ( ph -> ph )  -> extracted: ( ph -> ph )
            # render: ( ph -> ph )
            
            # Normalize spaces just in case
            local_stmt_clean = " ".join(local_stmt.split())
            
        except Exception as e:
            print(f"  [FAIL] Error constructing local lemma: {e}")
            fail_count += 1
            continue
            
        # 3. Compare
        if setmm_stmt == local_stmt_clean:
            print(f"  [OK] Match: {setmm_stmt}")
            success_count += 1
        else:
            print("  [FAIL] Mismatch!")
            print(f"    set.mm: {setmm_stmt}")
            print(f"    local : {local_stmt_clean}")
            fail_count += 1

    # Predicate axioms alignment (AX5/AX6/... placeholders)
    print("Checking predicate axioms alignment...")
    axioms = pred.compile_axioms()
    for label, local_name in SETMM_TO_PREDICATE_AXIOMS.items():
        print(f"Checking {label} -> {local_name}...")
        setmm_stmt = get_setmm_stmt(label)
        if not setmm_stmt:
            print(f"  [WARN] Could not find or parse '{label}' in set.mm")
            fail_count += 1
            continue
        try:
            wff = axioms[local_name]
            symtab = interner.symbol_table()
            local_stmt = render(wff.tokens, symtab=symtab)
            local_stmt_clean = " ".join(local_stmt.split())
        except Exception as e:
            print(f"  [FAIL] Error compiling local axiom {local_name}: {e}")
            fail_count += 1
            continue
        if setmm_stmt == local_stmt_clean:
            print(f"  [OK] Match: {setmm_stmt}")
            success_count += 1
        else:
            print("  [FAIL] Mismatch!")
            print(f"    set.mm: {setmm_stmt}")
            print(f"    local : {local_stmt_clean}")
            fail_count += 1

    # ZFC axioms alignment
    print("Checking ZFC axioms alignment...")
    zfc_axioms_expr = make_zfc_axioms()
    # Compile ZFC axioms using the PredicateSystem (it has the necessary builtins)
    zfc_axioms = {k: pred.compile(v, ctx=f"compile_zfc[{k}]") for k, v in zfc_axioms_expr.items()}
    
    for label, local_name in SETMM_TO_ZFC_AXIOMS.items():
        print(f"Checking {label} -> {local_name}...")
        setmm_stmt = get_setmm_stmt(label)
        if not setmm_stmt:
            print(f"  [WARN] Could not find or parse '{label}' in set.mm")
            fail_count += 1
            continue
        try:
            wff = zfc_axioms[local_name]
            symtab = interner.symbol_table()
            local_stmt = render(wff.tokens, symtab=symtab)
            local_stmt_clean = " ".join(local_stmt.split())
        except Exception as e:
            print(f"  [FAIL] Error compiling local ZFC axiom {local_name}: {e}")
            fail_count += 1
            continue
        if setmm_stmt == local_stmt_clean:
            print(f"  [OK] Match: {setmm_stmt}")
            success_count += 1
        else:
            print("  [FAIL] Mismatch!")
            print(f"    set.mm: {setmm_stmt}")
            print(f"    local : {local_stmt_clean}")
            fail_count += 1

    # ZFC definitions alignment
    print("Checking ZFC definitions alignment...")
    zfc_defs_expr = make_zfc_definitions()
    zfc_defs = {k: compile_zfc_expr(pred, v, ctx=f"compile_zfc_expr[{k}]") for k, v in zfc_defs_expr.items()}

    for label, local_name in SETMM_TO_ZFC_DEFINITIONS.items():
        print(f"Checking {label} -> {local_name}...")
        setmm_stmt = get_setmm_stmt(label)
        if not setmm_stmt:
            print(f"  [WARN] Could not find or parse '{label}' in set.mm")
            fail_count += 1
            continue
        try:
            wff = zfc_defs[local_name]
            symtab = interner.symbol_table()
            local_stmt = render(wff.tokens, symtab=symtab)
            local_stmt_clean = " ".join(local_stmt.split())
        except Exception as e:
            print(f"  [FAIL] Error compiling local ZFC definition {local_name}: {e}")
            fail_count += 1
            continue
        if setmm_stmt == local_stmt_clean:
            print(f"  [OK] Match: {setmm_stmt}")
            success_count += 1
        else:
            print("  [FAIL] Mismatch!")
            print(f"    set.mm: {setmm_stmt}")
            print(f"    local : {local_stmt_clean}")
            fail_count += 1

    # ZFC theorems alignment
    print("Checking ZFC theorems alignment...")
    zfc_thms_expr = make_zfc_theorems()
    zfc_thms = {k: compile_zfc_expr(pred, v, ctx=f"compile_zfc_expr[{k}]") for k, v in zfc_thms_expr.items()}

    for label, local_name in SETMM_TO_ZFC_THEOREMS.items():
        print(f"Checking {label} -> {local_name}...")
        setmm_stmt = get_setmm_stmt(label)
        if not setmm_stmt:
            print(f"  [WARN] Could not find or parse '{label}' in set.mm")
            fail_count += 1
            continue
        try:
            wff = zfc_thms[local_name]
            symtab = interner.symbol_table()
            local_stmt = render(wff.tokens, symtab=symtab)
            local_stmt_clean = " ".join(local_stmt.split())
        except Exception as e:
            print(f"  [FAIL] Error compiling local ZFC theorem {local_name}: {e}")
            fail_count += 1
            continue
        if setmm_stmt == local_stmt_clean:
            print(f"  [OK] Match: {setmm_stmt}")
            success_count += 1
        else:
            print("  [FAIL] Mismatch!")
            print(f"    set.mm: {setmm_stmt}")
            print(f"    local : {local_stmt_clean}")
            fail_count += 1

    print("-" * 40)
    print(f"Alignment check complete. OK: {success_count}, FAIL: {fail_count}")

if __name__ == "__main__":
    check_alignment()
