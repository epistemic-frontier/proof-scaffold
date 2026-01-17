# Specification: ProofScaffold Package (007-package)

## 1. Introduction

This specification defines the **ProofScaffold Package**, the fundamental unit of distribution and reuse in the MetaMath ecosystem.

A ProofScaffold Package is a standard **Python Package** that follows specific conventions to declare dependencies and construct Metamath artifacts.

## 2. Package Structure

A compliant package MUST follow the standard `src`-layout:

```text
my-logic-lib/
├── pyproject.toml       # Metadata & Dependencies
├── README.md
├── src/
│   └── my_logic/
│       ├── __init__.py
│       ├── build.py     # <--- THE BUILD SCRIPT
│       └── ...
└── ...
```

### 2.1 `pyproject.toml`

The `pyproject.toml` MUST declare a dependency on `proof-scaffold`. It acts as the **source of truth** for dependency resolution.

```toml
[project]
name = "my-logic-lib"
version = "0.1.0"
dependencies = [
    "proof-scaffold>=0.1.0",
    "metamath-prelude>=0.1.0", 
]
```

## 3. The Build Script (`build.py`)

The `build.py` file is executed by the ProofScaffold Linker during the build phase. It works in **Script Mode**: top-level code is executed immediately to construct the proof artifacts.

### 3.1 Why `build.py` is Necessary?

Unlike simple code libraries, Metamath databases are **order-sensitive** and require **explicit construction**. The `build.py` script serves as the **Orchestrator**:

1.  **Import Selection**: Explicitly choosing which symbols to import from dependencies (avoiding namespace pollution).
2.  **Order Control**: Defining the exact order of axioms and theorems (crucial for verification).
3.  **Glue Logic**: Converting high-level Python objects (ASTs) into low-level Metamath tokens.

While it cannot be eliminated, it can be kept concise using the `skfd` library.

### 3.2 Context Access (`skfd.context`)

The Linker injects the build context into the `skfd` module before executing the script.

*   `skfd.mm`: The global `MMBuilder` instance for the current package.
*   `skfd.deps`: A proxy object to access exports from upstream dependencies.

### 3.3 Example 1: Minimal Build (Zero Config)

For standard packages where the Python module structure already reflects the desired logical structure, `build.py` can be a single line:

```python
# src/my_logic/build.py
from skfd import auto_build

# Automatically scans globals() for Theorems/Axioms/Defs
# and emits them in definition order.
auto_build.emit_package(globals())
```

### 3.4 Example 2: Explicit Control

For packages requiring precise control over emission order or complex glue logic:

```python
# src/my_logic/build.py
from skfd import mm, deps
from . import axioms, theorems

# 1. Import Dependencies
mm.import_symbols(
    wff=deps.metamath_prelude.wff,
    imp=deps.metamath_prelude.wimp
)

# 2. Emit Axioms (Order Matters!)
axioms.emit(mm)

# 3. Emit Theorems
theorems.emit(mm)

# 4. Export Public API
mm.export("ax-1", "th-1")
```

## 4. How It Works (The Lifecycle)

1.  **Discovery (Static)**:
    *   The Linker scans `pyproject.toml` of all packages in the workspace.
    *   It builds a dependency graph solely based on package names.
    *   *Note: Python code is NOT executed in this phase.*

2.  **Planning**:
    *   The Linker performs a topological sort of the packages.

3.  **Execution (Dynamic)**:
    *   The Linker iterates through the sorted packages.
    *   For each package:
        1.  It creates a new `MMBuilder`.
        2.  It populates `skfd.deps` with the results of already-built dependencies.
        3.  It executes `src/<pkg>/build.py` using `importlib` or `exec`.
        4.  It collects the artifacts from the builder and registers them as the package's output.

## 5. Advanced: Function Mode (Legacy/Explicit)

For complex scenarios requiring explicit control or unit testing, the legacy **Function Mode** is still supported. If `build.py` defines a `build(mm, **deps)` function, the Linker will call it instead of relying on side-effects.

```python
# src/my_logic/build.py
def build(mm, metamath_prelude):
    # Explicit dependency injection
    ...
```

## 6. Namespace and Relocation

*   **Implicit Names**: When using Script Mode, the Linker assumes the `build.py` file defines the root namespace of the package.
*   **Relocation**: All locally defined symbols (e.g., `vx`) are automatically rewritten to globally unique names (e.g., `my_logic.vx`) in the final output.

## 7. Internal Organization Patterns

ProofScaffold imposes **no restrictions** on how you organize your Python source files. As long as `build.py` can import and emit them, any layout is valid.

### 7.1 Pattern A: Domain-Driven (Recommended)

Group foundational definitions (constructors, axioms) in a core module, and split proofs into logical topics or directories.

```text
src/group_theory/
├── build.py
├── core.py         # Constructors (G, *) and Axioms (group laws)
├── basic_props.py  # Basic lemmas (uniqueness of identity, etc.)
└── subgroups/      # Advanced topics in a subdirectory
    ├── __init__.py
    └── lagrange.py
```

**build.py**:
```python
from skfd import mm
from . import core, basic_props
from .subgroups import lagrange

core.emit(mm)
basic_props.emit(mm)
lagrange.emit(mm)
```

### 7.2 Pattern B: Layered (Strict Separation)

Separate syntax, axioms, and theorems into distinct files.

```text
src/logic/
├── build.py
├── syntax.py       # Constructors only
├── axioms.py       # Axioms only
└── theorems.py     # Theorems only
```

### 7.3 Pattern C: Monolithic (Single File)

For simple theories or prototypes, keep everything in one file.

```text
src/toy_logic/
├── build.py
└── logic.py        # Contains everything
```
