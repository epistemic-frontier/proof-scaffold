# Specification: ProofScaffold Package (007-package)

## 1. Introduction

This specification defines the **ProofScaffold Package**, the fundamental unit of distribution and reuse in the MetaMath ecosystem.

A ProofScaffold Package is a standard **Python Package** that follows specific conventions to declare dependencies and construct Metamath artifacts.

Package role matters for linker semantics. Most packages are ordinary library or
application packages. The standard `metamath-prelude` package is the distinguished
foundation unit and follows the global foundation-scope contract described in
[010-foundation-scope.md](file:///Users/mingli/MetaMath/proof-scaffold/references/010-foundation-scope.md).

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

### 2.2 Package Roles

ProofScaffold recognizes three conceptual roles:

* **Foundation**: the unique global foundation frame in a build closure. The
  standard package is `metamath-prelude`.
* **Library**: a reusable ordinary package such as `metamath-logic`.
* **Application**: a project package consuming libraries to prove local results.

Ordinary packages may import vocabulary and exported assertions from declared
dependencies. They must not rely on another ordinary package's local `$f` or
`$e` labels. Foundation-owned `$f` labels are the controlled exception, because
they are part of the global foundation frame.

## 3. The Build Script (`build.py`)

The `build.py` file is executed by the ProofScaffold Driver during the build phase. It MUST expose a single entrypoint:

```python
from skfd.api_v2 import BuildContextV2

def build(ctx: BuildContextV2) -> None:
    ...
```

No script-mode globals are injected. The toolchain passes all build-time capabilities explicitly via `ctx`.

### 3.1 Why `build.py` is Necessary?

Unlike simple code libraries, Metamath databases are **order-sensitive** and require **explicit construction**. The `build.py` script serves as the **Orchestrator**:

1.  **Import Selection**: Explicitly choosing which symbols to import from dependencies (avoiding namespace pollution).
2.  **Order Control**: Defining the exact order of axioms and theorems (crucial for verification).
3.  **Glue Logic**: Converting high-level Python objects (ASTs) into low-level Metamath tokens.

While it cannot be eliminated, it can be kept concise using the `skfd` library.

### 3.2 Context Access (`BuildContextV2`)

The Driver constructs a `BuildContextV2` and calls `build(ctx)`.

Key fields:

* `ctx.mm`: an [MMBuilderV2](file:///Users/mingli/MetaMath/proof-scaffold/src/skfd/builder_v2/builder.py) instance (SymbolId-only emission).
* `ctx.deps`: a [DepsView](file:///Users/mingli/MetaMath/proof-scaffold/src/skfd/api_v2.py) for accessing dependency exports.
* `ctx.names`: a `NameResolver` shared by the build and toolchain for Unicode authoring → ASCII canonicalization.
* `ctx.unit`: stable metadata (`dist_name`, `module_name`, `build_path`) for origin tracking and diagnostics.

### 3.3 Example 1: Minimal Build (Zero Config)

For standard packages where the Python module structure already reflects the desired logical structure, `build.py` can simply delegate to a local emitter:

```python
# src/my_logic/build.py
from skfd.api_v2 import BuildContextV2
from . import axioms, theorems

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    axioms.emit(mm, ctx=ctx)
    theorems.emit(mm, ctx=ctx)
```

### 3.4 Example 2: Explicit Control

For packages requiring precise control over emission order or complex glue logic:

```python
# src/my_logic/build.py
from skfd.api_v2 import BuildContextV2

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    prelude = ctx.deps.prelude  # or ctx.deps["metamath-prelude"]

    wff = prelude["wff"]  # SymbolId
    mm.comment("My logic library")

    ax1 = mm.a(mm.sym.label("ax-1"), tc=wff, expr=[mm.sym.var("φ")])
    th1 = mm.p(mm.sym.label("th-1"), tc=wff, expr=[mm.sym.var("φ")], proof=[ax1])

    mm.export(ax1, th1)
```

## 4. How It Works (The Lifecycle)

1.  **Discovery (Static)**:
    *   The Linker scans `pyproject.toml` of all packages in the workspace.
    *   It builds a dependency graph solely based on package names.
    *   *Note: Python code is NOT executed in this phase.*

2.  **Planning**:
    *   The Linker performs a topological sort of the packages.

3.  **Execution (Dynamic)**:
    *   The Driver iterates through the sorted packages.
    *   For each package:
        1.  It creates a new `MMBuilderV2` (sharing a workspace-wide `SymbolInterner`).
        2.  It creates a `DepsView` of already-built dependency exports.
        3.  It calls `build(ctx: BuildContextV2)`.
        4.  It finalizes the unit (`mm.finish()`), collects exports, and stores the unit IR for linking.

## 6. Namespace and Relocation

* **Unit identity**: each build unit has a stable `origin_module_id` (typically the Python module name containing `build.py`).
* **Relocation**: Link-time relocation ensures the final emitted `.mm` is globally coherent, while preserving provenance via sourcemaps.

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
from . import core, basic_props
from .subgroups import lagrange

def build(ctx):
    mm = ctx.mm
    core.emit(mm, ctx=ctx)
    basic_props.emit(mm, ctx=ctx)
    lagrange.emit(mm, ctx=ctx)
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
