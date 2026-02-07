"""
Experiment: Symbol References and Dependency Collection.

This script demonstrates the "Level 3" dependency management (Symbol Level)
discussed in 006-dependency.md.

It simulates:
1. Defining a Reference Object (Ref).
2. Authoring a proof using Refs (no direct MMBuilder access).
3. Collecting dependencies automatically.
4. Resolving them against a mock upstream package.
"""

from __future__ import annotations

from dataclasses import dataclass

from skfd.builder import MMBuilder
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.linker.api import LinkerV1

# --- 1. The Reference System (Mocking skfd.core.refs) ---

@dataclass(frozen=True)
class Ref:
    """A pointer to a symbol defined in another package."""
    pkg: str
    name: str

    def __repr__(self) -> str:
        return f"@{self.pkg}.{self.name}"

# --- 2. The Upstream Package (Mocking skfd.deps) ---

class UpstreamPackage:
    def __init__(self, exports: dict[str, int]):
        self.exports = exports

# --- 3. The Authoring Layer (Mocking skfd.authoring) ---

@dataclass
class ProofStep:
    label: str
    rule: str | Ref  # Can be a local string or a remote Ref
    hyps: list[str]

@dataclass
class Theorem:
    name: str
    stmt: str
    steps: list[ProofStep]

# --- 4. The Collector (The Core Logic) ---

class Collector:
    def __init__(self) -> None:
        self.needed_refs: set[Ref] = set()

    def scan(self, thm: Theorem) -> None:
        """Scan a theorem for external references."""
        for step in thm.steps:
            if isinstance(step.rule, Ref):
                self.needed_refs.add(step.rule)

# --- 5. The Build Process (Mocking build.py + skfd orchestration) ---

def run_demo() -> None:
    print("=== Step 1: Build Upstream Package (pkg_a) ===")
    ot = OriginTable()
    interner = SymbolInterner()
    
    mm_a = MMBuilder(interner=interner, origin_table=ot, module_id="pkg_a")
    mm_a.c("wff", "|-", "ph")
    mm_a.v("x")
    # Define ax-1: |- x
    mm_a.a("ax-1", "|-", "x") 
    
    # Export ax-1
    ax1_id = mm_a._intern_label("ax-1")
    pkg_a_exports = {"ax-1": ax1_id}
    
    unit_a = mm_a.to_proof_unit("pkg_a:unit0")
    print(f"Upstream built. Exports: {pkg_a_exports}")

    print("\n=== Step 2: Define References (refs.py) ===")
    # This is what the user would import
    AX_1_REF = Ref("pkg_a", "ax-1")
    print(f"Defined reference: {AX_1_REF}")

    print("\n=== Step 3: Authoring (pkg_b) ===")
    # User writes a proof using the Ref, oblivious to SymbolIds
    # Theorem: |- x (proven by ax-1)
    my_thm = Theorem(
        name="th-1",
        stmt="x",
        steps=[
            ProofStep("s1", rule=AX_1_REF, hyps=[])
        ]
    )
    print(f"Authored theorem '{my_thm.name}' using rule {my_thm.steps[0].rule}")

    print("\n=== Step 4: Collection & Resolution ===")
    # 1. Collect
    collector = Collector()
    collector.scan(my_thm)
    print(f"Collector found refs: {collector.needed_refs}")

    # 2. Build Downstream (pkg_b)
    mm_b = MMBuilder(interner=interner, origin_table=ot, module_id="pkg_b")
    
    # 3. Resolve & Auto-Import
    # Mocking the dependency injection
    deps = {"pkg_a": UpstreamPackage(pkg_a_exports)}
    
    local_map = {} # Ref -> Local SymbolId
    
    for ref in collector.needed_refs:
        print(f"Resolving {ref}...")
        if ref.pkg not in deps:
            raise ValueError(f"Missing dependency: {ref.pkg}")
        
        upstream = deps[ref.pkg]
        if ref.name not in upstream.exports:
            raise ValueError(f"Symbol {ref.name} not exported by {ref.pkg}")
            
        target_id = upstream.exports[ref.name]
        
        # Auto-Import into mm_b
        # We use the same name for simplicity, but could rename
        mm_b.import_symbols(**{ref.name: target_id})
        local_map[ref] = ref.name # Map Ref to the local string name used in import
        print(f"  -> Imported '{ref.name}' as ID {target_id}")

    # 4. Emit Theorem
    print(f"Emitting {my_thm.name}...")
    # Need to declare local usage first (normally handled by emit_axioms)
    # Since we share the interner, the constants/vars are "known" globally but need local declaration
    # For this demo, we cheat and re-declare or assume shared context.
    # In real skfd, we'd import wff/ph too.
    # Let's just do minimal declarations to make it valid
    mm_b.c("wff", "|-", "ph") 
    mm_b.v("x") 

    # Translate proof steps
    proof_labels = []
    for step in my_thm.steps:
        if isinstance(step.rule, Ref):
            # Use the imported name
            proof_labels.append(local_map[step.rule])
        else:
            proof_labels.append(step.rule)
            
    mm_b.p(my_thm.name, "|-", my_thm.stmt, proof=proof_labels)
    
    unit_b = mm_b.to_proof_unit("pkg_b:unit0")

    print("\n=== Step 5: Linking ===")
    res = LinkerV1.link(units=[unit_a, unit_b], origin_table=ot, interner=interner)
    print(res.mm_text)

if __name__ == "__main__":
    run_demo()
