# Specification: Dependency Management (006-dependency)

## 1. Introduction

This specification addresses the **Granularity Gap** in the ProofScaffold ecosystem:

*   **Python Packages** (007-package) operate at a coarse grain (libraries, distribution units).
*   **Proof Construction** operates at a fine grain (theorems, definitions, individual symbols).

While Python's import system handles the coarse grain, we need a specialized mechanism to resolve fine-grained logical dependencies during the authoring-to-linking translation.

## 2. The Granularity Model

We define three levels of dependency granularity:

1.  **Package Level (Coarse)**:
    *   Unit: Python Package (e.g., `metamath-logic`).
    *   Resolution: `pip` + `pyproject.toml`.
    *   Role: Availability. Ensures code and artifacts are on disk.

2.  **Module Level (Medium)**:
    *   Unit: ProofUnit (e.g., `logic.propositional`).
    *   Resolution: `build.py` / `skfd` Linker.
    *   Role: Linking. Ensures symbols are loaded into the global SymbolTable.

3.  **Symbol Level (Fine)**:
    *   Unit: `Theorem`, `Axiom`, `Const`, `Var`.
    *   Resolution: **The Collector** (Authoring Layer).
    *   Role: Usage. Ensures a specific theorem is available for `apply()` in a proof step.

This document focuses on Level 3 and its interaction with Level 2.

## 3. The Symbol Reference Protocol

To support fine-grained dependencies without loading implementation code, we introduce **Symbol References**.

### 3.1 The `Ref` Object

A `Ref` is a lightweight handle that points to a symbol defined elsewhere. It does not carry the proof or definition, only the identity.

```python
@dataclass(frozen=True)
class Ref:
    package: str       # e.g., "metamath-logic"
    module: str        # e.g., "logic.propositional"
    name: str          # e.g., "L1_id"
    kind: SymbolKind   # "Theorem" | "Axiom" | "Const"
```

### 3.2 Authoring-Time Usage

Authors import these References as if they were the objects themselves.

```python
# In skfd/authoring/refs.py or generated code
from skfd.core.refs import Ref

# This is just a pointer, effectively zero-cost import
L1_id = Ref("metamath-logic", "logic.prop", "L1_id", "Theorem")
```

When constructing a proof, the `LemmaBuilder` accepts these Refs:

```python
def prove_my_lemma(sys):
    # sys.apply knows how to handle Ref objects
    step1 = sys.apply(L1_id, subst={...})
```

## 4. The Collector Mechanism

The bridge between Authoring (Level 3) and Linking (Level 2) is **The Collector**.

### 4.1 Phase 1: Local Collection

When `emit_lemmas(mm, lemmas)` is called, the Collector scans the proof steps of all provided lemmas.

```python
collector = DependencyCollector()
for lemma in lemmas:
    collector.scan(lemma)
    
# Result: Set[Ref]
# { Ref("metamath-logic", "logic.prop", "L1_id"), ... }
```

### 4.2 Phase 2: Resolution & Auto-Import

The Collector then reconciles these references against the `MMBuilder` context.

```python
for ref in collector.needed_refs:
    # 1. Check if already defined locally
    if mm.has_symbol(ref.name):
        continue
        
    # 2. Check if already imported
    if mm.is_imported(ref.name):
        continue
        
    # 3. Auto-Import from Dependency
    # This requires that the 'package' dependency is already built (Level 1/2)
    # skfd.deps is the proxy to upstream exports
    upstream_pkg = skfd.deps.get(ref.package)
    if not upstream_pkg:
        raise DependencyError(f"Package '{ref.package}' is missing from pyproject.toml")
        
    # 4. Bind the symbol
    target_id = upstream_pkg.exports[ref.name]
    mm.import_symbol(ref.name, target_id)
```

## 5. Explicit vs. Implicit Policies

We support two policies for dependency management in `build.py`:

### 5.1 Explicit Policy (Strict)

The `build.py` must explicitly import every symbol used. The Collector verifies this but does not perform auto-import.

*   **Pros**: precise control, no surprises.
*   **Cons**: verbose `build.py`.

### 5.2 Implicit Policy (Auto)

The Collector automatically imports any missing symbol if it can be found in the declared package dependencies.

*   **Pros**: authoring flow is seamless.
*   **Cons**: `build.py` hides the actual API surface used.

**Recommendation**: Use **Implicit Policy** for standard library / prelude dependencies (high frequency), and **Explicit Policy** for large external libraries (to be aware of coupling).

## 6. Interaction with Package Specification (007)

*   **007-package** defines how packages are installed and how `build.py` is triggered.
*   **006-dependency** defines how `emit()` uses the context provided by 007 to resolve fine-grained symbol usage.

The `skfd` framework is responsible for implementing the Collector and ensuring it respects the boundaries defined in 007.
