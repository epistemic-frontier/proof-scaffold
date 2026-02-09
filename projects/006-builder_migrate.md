# Migration Plan: Porting legacy v0 Builder to Global Symbol Architecture

## 1. Goal
Port the `MMBuilder` and `CompositeEmitter` (Text + LIR) from `v0-archive` to `src/proof_scaffold/builder`, adapting it to work with the new **Global Symbol Table** (`SymbolInterner`) architecture instead of `v0`'s unit-local symbol tables.

## 2. Gap Analysis

| Feature | `v0-archive` Implementation | Current `src` Architecture |
| :--- | :--- | :--- |
| **Symbol Resolution** | Unit-local `symtab` (list of strings). Tokens are `int` indices into this list. | Global `SymbolInterner`. Tokens are `SymbolId` (int) keys into a global dictionary. |
| **Token Identity** | Tokens `A` in Unit 1 and `A` in Unit 2 are distinct indices (0, 1...) unless merged later. | Tokens `A` in Unit 1 and `A` in Unit 2 are distinct `SymbolId`s if they have different `origin_module_id`, OR same if shared? (Need to verify interner policy). |
| **Emitter** | `LIREmitter` builds `v0.ir` objects using local indices. | Need `LIREmitter` to build `linker.lir` objects using global `SymbolId`. |
| **Scoping** | `ScopeStack` tracks visibility locally. | Linker has scoping passes, but Builder needs to track it for "verify-as-you-go" or just constructing valid IR. |

## 3. Key Design Decisions

### 3.0. Compliance with Link Model V4 (`references/002_link-model_v4.md`)
The migration must strictly adhere to the **Stage 0** contract defined in V4:
- **Inputs**: Python generators / DSL.
- **Outputs**:
    - OriginTable seeds.
    - Local symbol registrations (provisional).
    - `ProofUnitIR` with `LIR` (tokens as `SymbolId`).

**Crucial**: V4 §5 mandates "Stage 0 MUST attach `origin_ref` to every Statement". Our ported Builder is effectively the **Stage 0 implementation**.

### 3.1. Adapting to Global Interning
The key challenge is that the `v0` builder assumes it "owns" the universe of symbols for the unit it is building. In the new system, it is just one contributor to a global `SymbolInterner`.

**Proposed Change**:
- `MMBuilder` must be initialized with:
    - `SymbolInterner` (global)
    - `unit_id` / `module_id` (context for creating symbols)
- When `builder.c("foo")` is called:
    - Old: Append "foo" to local `_symtab`, return index.
    - New: Call `interner.intern(..., local_name="foo", kind="Const")`, return `SymbolId`.

### 3.2. Preservation of TextEmitter
The `TextEmitter` is fully string-based and agnostic to the internal representation. It can be ported **almost as-is**, providing a valuable debugging/verification output (the `.mm` file content) matching the IR.

### 3.3. Namespace & Naming Conflicts
The user mentioned: "Theoretically promoting from local to global, aside from naming conflicts, has no other obstacles."

- **Conflict Handling**:
    - The `SymbolInterner` uses `(origin_module, local_name, kind)` as the key.
    - As long as the Builder faithfully passes the current `module_id`, there is no conflict between modules.
    - Within a module, `builder`'s existing logic (`_check_label_fresh`) protects against duplicates.

## 4. Implementation Steps

### Step 1: Scaffold Types
- Create `src/proof_scaffold/builder/`.
- Port `ScopeStack` (logic is reusable).
- Port `MMError` / `MMDSLError`.

### Step 2: Port Emitters
- **TextEmitter**: Copy from `v0-archive`.
- **LIREmitter**: Rewrite to produce `src.linker.lir` objects.
    - Needs access to `SymbolInterner` to resolve strings -> `SymbolId` (or the Builder does resolution and passes `SymbolId`s).
    - **Decision**: Builder should probably resolve to `SymbolId` first (using Interner), then pass `SymbolId` + `str` (for comments/text) to Emitters.
    - *Correction*: `TextEmitter` needs strings. `LIREmitter` needs IDs. Builder sits in middle.

### Step 3: Implement `MMBuilder`
- Inject `SymbolInterner` and `module_id` in `__init__`.
- Update methods (`c`, `v`, `f`, `e`, `a`, `p`) to intern symbols immediately.
- Update `to_proof_unit` to return `src.linker.unit.ProofUnitIR`.

### 3.5. Dependency Management (The "Import" Problem)
The user correctly identified that moving to a Global Symbol Table exposes dependency management issues.

- **The Problem**: If Unit B uses theorem `ax-1` from Unit A, the Builder for B must produce the correct `SymbolId` for `ax-1` in the LIR.
- **Constraint**: `SymbolInterner` keys are `(origin_module, name, kind)`.
- **Scenario**:
    - **Case 1: Sequential Build (A then B)**:
        - Unit A runs, interns `ax-1` (Module="A").
        - Unit B runs. Builder calls `interner.get(key=("A", "ax-1", ...))`. It exists. Success.
    - **Case 2: Unknown Origin**:
        - Unit B just references "ax-1". Builder doesn't know it belongs to "A".
        - Builder might try to intern it as ("B", "ax-1"), which is WRONG (Shadowing/Redefinition).

- **Solution**:
    - **Explicit Imports**: The Builder API needs a way to say "search for 'ax-1' in dependencies".
    - **Python-level Object Sharing**: Since examples are Python scripts, we can explicitly pass `SymbolId`s or `SymbolDef` objects from Unit A to Unit B.
    - **DSL Extension**: `builder.import_symbols(from_unit: ProofUnitIR)`? Or `builder.use("ax-1", from_module="A")`?

**Decision**: For `v1` examples, we will leverage the **Python environment**, aligning with `references/001_arch-design.md` Section 7.1 "Ecosystem Leverage":
> "Imports: Python `import` statements define the logical dependency graph."

- Examples like `minimal_link.py` should instantiate Unit A, get its exports (SymbolIds), and pass them to Unit B's builder.
- *Refinement*: We might strictly require `builder.p(..., proof=[unit_a_thm])` where `unit_a_thm` is the python object referencing the symbol, rather than a bare string "ax-1". This is safer.
- **Goal**: Replac manual LIR construction in `examples/*.py` with `MMBuilder`.
- **Reasoning**: This validates the builder API and ensures it covers all features used in our test corpus.
- **Action**: Refactor `examples/minimal_ok.py` etc. to use `MMBuilder`.
  - Current examples construct `ProofUnitIR` manually.
  - New examples will look like: 
    ```python
    mm = MMBuilder(interner, origin_table, "minimal_ok")
    mm.c("min", "im").v("A", "B")...
    return mm.to_proof_unit()
    ```

## 5. Open Questions
- **Origin Tracking**: `v0` used `OriginProvider`. Current `linker` has `OriginRef`. We need to adapt the builder to create `OriginRef`s.
- **Dependencies**: `v0` builder had `requires()`. Current system seems to deduce dependencies. We should check if explicit dependency declaration in Builder is still needed.
