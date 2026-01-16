# Project 009: Generic Logic Driver

## 1. Goal
Implement a generic "Compiler Driver" (`skfd.driver`) that builds Python-based Proof Packages.
**Constraint**: The Driver must NOT implicitly depend on `prelude`. All dependencies must be explicit.

## 2. Package Contract

A **Proof Package** is a python module that exposes a `build()` hook.

### 2.1. The `build` Hook

```python
# src/my_logic/build.py
from skfd.builder import MMBuilder

def build(mm: MMBuilder, **deps: ModuleInterface) -> None:
    """
    Args:
        mm: Pre-configured builder (interner + module_id bound).
        deps: Dictionary of dependency modules (injected by Driver).
    """
    pass
```

### 2.2. Dependency Declaration
How does the Driver know what to inject into `deps`?
We need a metadata mechanism. Options:
1.  **`pyproject.toml`** (Standard, best for future packaging).
2.  **`manifest.toml`** (Custom).
3.  **`build.py` attribute** (Simple, no extra file).

**Decision**: For Phase 1, we use a simple **`manifest()`** function or variable in `build.py`.

```python
# src/logic/build.py
def manifest() -> dict:
    return {
        "deps": ["prelude"]
    }
```

## 3. Architecture

### 3.1. Components
*   **`PackageDiscoverer`**: Scans directories for `build.py`.
*   **`DependencyGraph`**:
    *   Nodes: Packages.
    *   Edges: declared dependencies.
    *   Action: Topological Sort.
*   **`DriverRunner`**:
    *   Creates global `SymbolInterner`.
    *   Iterates sorted packages.
    *   For each package:
        *   Init `MMBuilder` (with `OriginTable` context).
        *   Resolve dependencies (fetch `ModuleInterface` from previous builds).
        *   Call `build(mm, **resolved_deps)`.
        *   Collect `ProofUnitIR`.

## 4. Verification Strategy: Transient Monolith

Since we do NOT use Metamath's inclusion mechanism (`$[ ... $]`) to avoid scope pollution and complexity, the Driver uses a **Transient Monolith** strategy for verification.

### 4.1. Verification Step
When running `skfd verify logic`:
1.  **Resolve Dependencies**: Logic -> [Prelude].
2.  **Collect LIR**:
    *   Load `prelude`'s LIR (from memory or cached pickle).
    *   Load `logic`'s LIR (freshly built).
3.  **Concatenate**: Create a single stream: `Prelude LIR + Logic LIR`.
4.  **Emit**: Generate one standalone file `target/logic_full.mm`.
5.  **Verify**: Run `metamath-exe target/logic_full.mm`.
6.  **Discard** (or keep as artifact): The file is independent and self-contained.

### 4.2. Advantages
*   **Isolation**: No cross-file `$d` or `$v` pollution. `logic_full.mm` is a sealed unit.
*   **Simplicity**: No need for the Linker to compute "Differential Emission". It just dumps everything required.
*   **Robustness**: If `prelude` changes, `logic` verification naturally picks it up (no stale `.mm` references).

## 5. Implementation Steps
1.  Define `skfd.driver` package.
2.  Add `build.py` to `src/prelude` and `src/logic`.
3.  Implement `PackageDiscoverer` and `DependencyGraph`.
4.  Implement `LIRBundle` (container for LIR statements to pass between builds).
5.  Implement `DriverRunner`:
    *   Build A -> `LIRBundle A`
    *   Build B(A) -> `LIRBundle A` + `LIRBundle B`
6.  CLI: `skfd verify <package>`.
