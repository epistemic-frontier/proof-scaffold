# ProofScaffold Linker Model
## Formal IR and Data Flow Specification (Rev. 2)

This document specifies the **linker-oriented execution model** of ProofScaffold.

It refines the initial draft by incorporating **Metamath-specific semantic constraints**
that are not present in conventional compiler toolchains.

The goal of this specification is to ensure that the linker does not merely produce
topologically correct output, but **semantically valid Metamath streams**.

This is a **middle-end specification**:
it defines invariants, data flow, and interfaces, not implementation details.

---

## 1. Overview

ProofScaffold treats formal proofs as **linkable artifacts**.

At the Python level, proof components form a **dependency DAG**.
At the Metamath level, verification requires a **strictly linear stream**
with well-defined scope and context semantics.

The linker is responsible for transforming the former into the latter
while preserving all constraints imposed by the Metamath specification.

```

Python Modules
↓
[Proof IR Graph]
↓  (dependency resolution, context management, relocation)
[Linearized Proof IR]
↓  (two-phase emission)
Metamath Stream
↓
Verifier Backend

```

---

## 2. Design Principles

The linker model is governed by four principles:

1. **Explicitness**  
   All dependencies, symbols, scopes, and transformations must be explicit in the IR.

2. **Determinism**  
   Given the same inputs, the linker must produce the same linear stream.

3. **Untrusted Generation**  
   The linker may generate invalid output; the verifier must reject it.

4. **Incremental Verifiability**  
   Each stage must admit sanity checks and localized debugging.

---

## 3. Proof IR: Core Entities

### 3.1 Symbols

A **Symbol** represents a Metamath-level entity.

Minimal attributes:

- `name`: local (human-facing) identifier
- `origin`: source module/package
- `kind`: `$c`, `$v`, `$f`, `$e`, `$a`, `$p`
- `scope_class`: global-only or nest-safe

Symbols are **not globally unique by name alone**.

---

### 3.2 Symbol Table

The **Symbol Table** is a global linker structure:

```

(Symbol Origin, Local Name) → Global Symbol ID

```

Responsibilities:

- Prevent name collisions across modules
- Provide a stable internal identifier
- Support relocation during linearization
- Serve as the backbone for source maps

The Symbol Table is internal to the linker and invisible to the verifier.

---

### 3.3 Proof Fragment

A **Proof Fragment** is the smallest unit of linkage.

Conceptually, it contains:

- Declarations (`$c`, `$v`, `$f`, `$e`)
- Assertions (`$a`, `$p`)
- Local symbol references
- Dependency metadata
- Export metadata (see below)

Fragments are **not** assumed to be linearly ordered.

---

### 3.4 Exported Context vs Private Context

Each fragment distinguishes between:

- **Exported Context (Public Interface)**  
  Declarations and hypotheses that must be reachable by downstream fragments
  (e.g. `$v`, `$f` required by exported theorems).

- **Private Context**  
  Auxiliary symbols and hypotheses intended only for internal proofs.

This distinction is mandatory to prevent **context leakage**
and to make hypothesis reachability explicit.

---

### 3.5 IR Invariants (Metamath-Specific Constraints)

To ensure that a topologically correct link yields a **semantically valid**
Metamath stream, the IR enforces strict invariants:

1. **Scope Balance (Scope Atomicity)**  
   Every Proof Fragment must be *scope-balanced*.
   It cannot leave an open `${` or `$}` dangling across fragment boundaries.
   Fragment linkage must never depend on a global “open-scope stack”.

2. **Scope Class Declaration**  
   Each fragment declares whether it is:
   - **Global-only** (must be emitted at top-level), or
   - **Nest-safe** (may be emitted inside `${ ... $}`).

3. **Constant and Variable Hoisting**  
   All `$c` declarations, and all `$v` declarations,
   are treated as **global header atoms**.
   They must be emitted in the global header of the final stream,
   never inside a local scope,
   regardless of where they appear in Python modules.

4. **Hypothesis Reachability (Context Non-Leakage)**  
   If Fragment B depends on Fragment A,
   then any `$f` or `$e` required by A’s exported assertions
   must be **reachable (active)** in the scope where B is emitted.

These invariants form the **middle-end contract** of the linker.

---

## 4. Linker Stages

### 4.1 Front-End (IR Construction)

Input:
- Python modules
- Generator functions
- Optional manifest metadata

Output:
- Proof IR fragments
- Initial symbol registrations

This stage answers:

> *What proof components exist?*

---

### 4.2 Dependency Resolution

Input:
- Proof IR fragments
- Explicit dependency metadata

Output:
- Topologically sorted fragment order

Failure modes:
- Missing dependency
- Circular dependency

---

### 4.3 Relocation (Namespace Flattening)

Metamath requires a **flat global namespace**.
Python modules are scoped.

The linker performs relocation:

- Local symbol names are rewritten to globally unique identifiers
- All internal references are updated accordingly

#### Mangling Strategy (Readability vs Uniqueness)

Recommended strategy:

1. Prefer readable, deterministic names:  
   `mp` in module `logic` → `mp__logic`
2. On collision, append a deterministic hash suffix:  
   `mp__logic__a1b2`
3. If label length limits apply, truncate and keep the hash suffix

Source Maps complement mangling, but must not be the sole debugging mechanism.

---

### 4.4 Linearization

After relocation, the DAG is flattened into a **linear sequence**.

Constraints:

- All symbols must be defined before use
- Scope balance must be preserved
- Hypothesis reachability must match fragment export contracts

The result is a **Linear Proof IR**.

---

### 4.5 Emission

#### 4.5.1 Two-Phase Emission: Global Header + Body

Emission is split into two explicit phases:

1. **Global Header**
   - Hoisted `$c` declarations
   - Hoisted `$v` declarations
   - Optional linker metadata anchors

2. **Body**
   - Scope-balanced fragments
   - Relocated labels and rewritten references
   - Assertions and proofs

This structure enforces `$c/$v` legality and stabilizes namespace semantics.

---

## 5. Source Maps (Debugging Model)

Large generated streams are not human-debuggable.

The linker must generate **Source Maps** mapping:

```

Linear Stream Offset → (Source Module, Line, Generator Context)

```

Source Maps enable:

- Localizing verifier errors
- Debugging Python generators
- CI error reporting

Optionally, the linker may emit a separate `symbol_map`
for human inspection.

---

## 6. Verifier Interface Boundary

The verifier is treated as a black box.

The linker guarantees only:

- Syntactic validity of the emitted stream
- Structural correctness (per IR invariants)

The verifier is responsible for:

- Parsing
- Scope handling
- Stack discipline
- Substitution
- Proof checking

Multiple verifier backends may be supported:
CLI, library, or streaming interfaces.

---

## 7. Correctness Model

Correctness is **not** established by the linker.

Instead:

- The linker enforces **structural correctness**
- The verifier enforces **semantic correctness**

Any violation must result in verifier rejection.

This separation is intentional and fundamental.

---

## 8. Minimal Viable Linker (MVP)

A minimal linker implementation must support:

- Fragment-level dependency resolution
- Symbol Table with relocation
- Constant and variable hoisting
- Linear emission
- Single verifier backend

Advanced features (caching, zero-copy, streaming) are layered on top.

---

## 9. Relation to Tutorial and Sanity Checks

The tutorial and sanity checks provide **ground truth**
for the linker model.

Each tutorial step corresponds to a constrained instance
of this pipeline.

The linker model generalizes those steps
without altering their semantics.

---

## 10. Scope of This Specification

This document defines *what* the linker must do, not *how*.

Implementation strategies may vary,
but deviations from these invariants must be justified explicitly.
