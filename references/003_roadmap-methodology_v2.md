# ProofScaffold Roadmap & Methodology (Document-First Plan)

**Status:** working document  
**Scope:** build/link toolchain for modular Metamath artifacts (Python as builder, Metamath as verifier)  
**Derived from:** Design Notes Rev. 2 and Linker Model v3  

---

## 1. Goals and Non-Goals

### 1.1 Goals (North Star)

1. **A repeatable toolchain** that turns a dependency DAG of proof components into a **single deterministic Metamath stream** that a verifier accepts.
2. **Linkage discipline** comparable to a systems linker:
   - dependency closure is explicit and checked,
   - namespaces are relocated deterministically,
   - scope and binding points are made explicit in a linear artifact.
3. **Developer-grade debugging**:
   - verifier failures must map back to *origin module → proof unit → statement → proof step* (SourceMap),
   - the toolchain should tell developers *where* and ideally *why* generation went wrong.
4. **A trust boundary that scales**:
   - Python generation and the linker are *untrusted*,
   - the verifier is the semantic authority.

### 1.2 Non-Goals

The project is **not**:
- an automated theorem prover (no proof search, no backtracking);
- an interactive proof assistant UX (Lean/Coq-like experience);
- a system that translates Metamath back to natural language.

---

## 2. System Principles

This project is governed by four non-negotiable principles:

1. **Explicitness**  
   Dependencies, scopes, substitutions, and transformations must be represented explicitly in IR.

2. **Determinism**  
   Same input IR must produce the same output stream (including names and ordering).

3. **Untrusted Generation**  
   Python code and the linker are *builders*, not trusted logical authorities.

4. **Incremental Verifiability**  
   Every new capability must be introduced with a minimal, stable sanity check.

---

## 3. Architecture Overview

### 3.1 The Three Layers

1. **Document Layer (human-facing)**  
   Markdown/LaTeX: intent, strategy, explanation. Not formally checked.

2. **Python Layer (compiler + linker)**  
   Produces structured IR, computes dependency closure, performs relocation, emits Metamath streams, and builds SourceMaps.

3. **Metamath Layer (binary artifact)**  
   A linear, machine-checkable stream. The verifier executes it.

### 3.2 The “Linker” Analogy (Toolchain Mental Model)

The proof system behaves like a compiler toolchain:

```
Python proof packages
  -> IR (HIR optional, LIR required)
  -> Linker (closure, scopes, relocation, emission)
  -> Metamath stream ("object code")
  -> Verifier ("CPU") executes and accepts/rejects
  -> Diagnostics -> SourceMap -> developer feedback
```

Correctness comes from:
- **structural integrity** (linker discipline), and
- **semantic execution** (verifier acceptance).

### 3.3 Trust Model

**TCB (Trusted Computing Base):**
- the Metamath verifier backend,
- the Metamath specification (syntax + semantics).

**Untrusted:**
- all Python generators,
- the linker itself,
- any optimization passes.

If the builder emits garbage, the verifier must reject it. Tooling exists to make the rejection actionable.

---

## 4. Core Concepts and Artifacts

### 4.1 IR: HIR and LIR

- **HIR (optional):** structured proof operations (e.g., `Apply(assertion, subst, step_id)`) with substitution metadata.
  - Enables `$d` propagation and strict MVP checks.
  - Improves provenance and diagnostics.

- **LIR (required):** Metamath-shaped statements whose tokens are *symbol references*, not raw strings.
  - Supports token-level relocation and deterministic emission.

### 4.2 Symbol System

- `SymbolId`: internal stable id, never emitted.
- `SymbolDef`: `{origin, local_name, kind(Const|Var|Label), scope_class}`.
- `SymbolRef`: reference to `SymbolId`.

**Rule:** proof tokens and math strings must be represented as `SymbolRef[]` (raw strings only in an explicit compatibility mode).

### 4.3 ProofUnit (the linkable boundary)

A **ProofUnit** is the smallest unit of linking discipline. It contains:
- `decls_local`: local `$f/$e` hypotheses and local `$d` needed at binding points;
- `exports`: exported assertions (`$a/$p`);
- `proof_body`: proof tokens (LIR) and optionally HIR proof ops.

**Policy constraint:** cross-unit dependencies are allowed only via **exported** `$a/$p` labels (never by peeking at internal `$f/$e`).

### 4.4 Contracts

Two contract layers exist and must not be conflated:

1. **Interface Contract (export contract)** for each exported assertion `A`:
   - `mandatory_hyps(A)` (ordered list of mandatory `$f` then `$e`)
   - `mandatory_vars(A)` (deterministically ordered)
   - `dv_contract(A)` (disjoint pairs over mandatory vars)
   - `public_symbols(A)` (externally linkable: exported `$a/$p` only)

2. **Proof Closure Contract (implementation closure)** for theorem `T`:
   - `uses_assertions(T)` (referenced `$a/$p` labels appearing in proof tokens / HIR)

This split eliminates “ghost dependencies” and makes linkability checkable.

### 4.5 ScopeFrames (explicit scoping)

The linear output IR must make scope explicit via frames:

- `ScopeEnter` `${`
- `ScopeExit` `$}`

A frame controls the activity of `$f`, `$e`, and `$d` declarations and defines the binding points for exports.

### 4.6 SourceMap (debugging surface)

A SourceMap is required for sustainable development.

Minimum fields:
- `stream_span -> (origin, unit_id, stmt_id, label?, proof_step_idx?)`

Recommended enrichment:
- active context snapshot digest (active `$f/$e/$d`),
- referenced assertion per proof step,
- optional substitution digest (if HIR exists).

---

## 5. Roadmap (Milestones and Acceptance Criteria)

The roadmap is dependency-ordered. Each milestone is defined by **deliverables** and **acceptance tests**.

### Phase 0 — Bootstrap and Baseline Loop

**M0.1 Minimal pipeline sanity**
- Deliverable: a stable `check_sanity` that always runs in CI.
- Acceptance: clean environment → build → emit minimal stream → verifier accepts.

**M0.2 Repository conventions**
- Deliverable: clear module layout (IR, linker passes, emission, diagnostics, tests).
- Acceptance: new contributors can run sanity + one small example with one command.

---

### Phase 1 — Linker v0 (Multi-Module Linkage + Deterministic Emission)

**M1.1 LIR foundation**
- Deliverable: typed LIR statement model; tokens are `SymbolRef[]`.
- Acceptance: single ProofUnit emits a valid stream and verifies.

**M1.2a Traceability infrastructure (Internal)**
- Deliverable: require an `origin` (module + file:line) on every `SymbolDef` / `Statement` / `ProofUnit` (and HIR `Apply`, if present); every linker pass must preserve it and wrap errors with an “origin chain”.
- Acceptance tests:
  - any linker error can report the *generator callsite* (origin module + file:line), not only a Python traceback inside the linker;
  - a deliberately triggered symbol collision reports both conflicting callsites.

**M1.2 Global symbol resolution + early lint**
- Deliverable: symbol table `(origin, local_name, kind) -> SymbolId`; resolution pass; forbidden pattern checks.
- Acceptance tests:
  - referencing a non-exported label fails before emission;
  - cross-unit `$f/$e` usage in proof tokens fails with a precise error location;
  - raw-string tokens (outside explicit COMPAT mode) fail fast with an origin-linked diagnostic.

**M1.3 Dependency closure + topo sort**
- Deliverable:
  - compute `uses_assertions(T)` from resolved proof tokens (preferred path);
  - in explicit COMPAT builds, allow a coarse `dependencies_hint=[...]` on ProofUnits as a bootstrap fallback;
  - topological ordering of ProofUnits; cycle detection; (optional) compare hint vs computed closure when both exist.
- Acceptance:
  - two-module example links in correct order;
  - a cycle is detected and rejected;
  - in COMPAT mode, missing/incorrect `dependencies_hint` fails early with an origin-linked diagnostic.

**M1.4 Scope planning (conservative ScopeFrames)**
- Deliverable: emit each ProofUnit in its own `${ ... $}` with unit-local decls preceding exports.
- Acceptance:
  - no scope leakage between units;
  - verifier accepts the linked multi-unit output.

**M1.5 Token-level relocation**
- Deliverable:
  - deterministic `emitted_name(SymbolId)` mapping,
  - rewrite of labels, math strings, and proof tokens.
- Acceptance:
  - two units can define the same local label name without collision,
  - repeated builds produce identical output (byte-identical or token-identical).

**M1.6 Two-phase emission (`$c/$v` header + body)**
- Deliverable:
  - hoist all `$c` and `$v` to a global header,
  - body contains only ScopeFrames + `$d/$f/$e/$a/$p`.
- Acceptance: the verifier accepts; emitted stream is deterministic; headers are stable.

**Exit Criteria for Linker v0**
- Multi-package linking works.
- Deterministic output is enforced in CI.
- Debugging can localize failures to units/statements and report generator callsites (origin chain), even if still coarse.

---

### Phase 2 — Diagnostics-First (SourceMap and Developer Feedback Loop)

**M2.1 SourceMap MVP**
- Deliverable:
  - mapping from output spans to origin/unit/stmt and (where possible) proof step index;
  - build it *from day one* on top of the IR `origin` metadata introduced in M1.2a (no retrofitting after emission).
- Acceptance: deliberately broken proof yields a report pointing to the generating unit and step.

**M2.2 Debug slice tool**
- Deliverable: a CLI that prints a minimal “slice” around a failing proof step:
  - surrounding ScopeFrame,
  - active context digest,
  - nearby tokens.
- Acceptance: a verifier error is reproducible in a small emitted excerpt or minimal reproducer stream.

**Exit Criteria**
- No verifier error is “just a byte offset”.
- Developers fix Python generators/contracts, not emitted Metamath by hand.

---

### Phase 3 — Contract Discipline (Interface vs Closure)

**M3.1 Contract extraction**
- Deliverable: compute `mandatory_hyps`, `mandatory_vars`, and `uses_assertions`.
- Acceptance:
  - interface/closure mismatch is detected,
  - closure completeness is enforced (no “implicit import”).

**M3.2 Conformance levels**
- Deliverable: formally define and enforce:
  - Level 0: LIR-only,
  - Level 1: MVP_STRICT-capable (requires substitution metadata),
  - Level 2: FOL-ready (free-vars metadata for `$d` propagation).
- Acceptance: build fails early if a requested conformance level is not met.

---

### Phase 4 — `$d` Readiness (Disjoint Variables)

This phase is explicitly staged to avoid blocking bootstrap progress.

**M4.1 `$d` Mode A (pass-through / explicit)**
- Deliverable: generators can supply `dv_contract(A)` and/or explicit `$d` decls; linker guarantees correct binding placement.
- Acceptance: a test that fails without `$d` passes when explicit contracts are provided.

**M4.2 MVP_STRICT checks (optional gate)**
- Deliverable: if enabled, enforce “variable-free substitution” via HIR substitution metadata.
- Acceptance: a known counterexample fails with a step-level diagnostic.

**M4.3 `$d` Mode B (linter-driven workflow)**
- Deliverable: map verifier disjointness errors back through SourceMap to suggest where to amend `dv_contract` or local `$d`.
- Acceptance: missing `$d` produces actionable guidance without manual stream archaeology.

**M4.4 `$d` Mode C (HIR-assisted propagation)**
- Deliverable: constraint propagation (soundness-first, non-minimal allowed):
  - for each `Apply(L, σ)`, propagate pairs `(x,y) in dv_contract(L)` to `Vars(σ(x)) × Vars(σ(y))`.
  - separate **interface pairs** (restricted to `mandatory_vars(T)`) from **local pairs** (scoped to internal proof safety).
- Acceptance: a small HIR-driven example verifies without manually writing all resulting `$d` pairs.

**Exit Criteria**
- `$d` is treated as part of the interface contract and is active at assertion definition sites.
- `$d` inference never becomes proof search; it remains constraint propagation over recorded substitutions.

---

### Phase 5 — Performance and Scaling (Deferred Until Semantics Stabilize)

**M5.1 IR representation microbench**
- Deliverable: benchmark per-token Python objects vs packed integer buffers for `SymbolRef`.
- Acceptance: choose and document a baseline representation strategy.

**M5.2 Compute-over-I/O**
- Deliverable: in-memory emission; avoid writing `.mm` files as a primary path.
- Acceptance: large builds run without I/O dominating runtime.

**M5.3 Zero-copy verification interface (optional)**
- Deliverable: a verifier interface that consumes an in-memory buffer (shared memory / buffer protocol).
- Acceptance: measurable reduction in memory copies and wall-clock time for large artifacts.

---

### Phase 6 — Ecosystem Integration and Packaging

**M6.1 Proof packages as Python packages**
- Deliverable: conventions for packaging proof libraries, declaring dependencies via imports, versioning via standard Python tooling.
- Acceptance: a library can be published and consumed like a normal Python dependency.

**M6.2 Reproducible builds**
- Deliverable: lockfile guidance, deterministic naming policies, and an artifact signature/digest.
- Acceptance: identical inputs yield identical artifact digests across machines.

---

## 6. Methodology (How We Build)

### 6.1 Document-First Workflow

Every significant change starts as a doc:
- **Spec** changes (Linker Model, IR rules, invariants)
- **ADR/RFC** for decisions (naming scheme, scope strategy, contract computation, `$d` modes)

A change is considered “ready for implementation” only when:
- the invariant impact is documented,
- acceptance tests are defined,
- migration/compatibility concerns are addressed.

### 6.2 Pass-Based Middle-End Development

Implement the linker as a sequence of passes (stages). Each pass must declare:

- **Inputs** and **outputs**
- **Preconditions**
- **Postconditions (invariants)**

Example invariants:
- no raw-string tokens (outside compatibility mode),
- scope balance is preserved,
- relocation rewrites all token occurrences,
- `$c/$v` are hoisted to the header,
- cross-unit hypothesis leakage is impossible by construction.

### 6.3 Testing Strategy

Three test classes are mandatory:

1. **Sanity tests (non-negotiable)**
   - minimal build → emit → verify
   - fast, stable, always in CI

2. **Golden tests**
   - fixed IR input → fixed emitted output (determinism)
   - includes name relocation snapshots

3. **Adversarial tests**
   - collisions, cycles, forbidden references, missing `$d`, scope imbalance
   - must fail in the earliest possible stage with a precise diagnostic

Optional:
- microbench tests (representation, emission speed),
- fuzzing on IR (defensive robustness).

### 6.4 Determinism as a First-Class Constraint

Determinism failures are treated as build failures.
Practices:
- sort all sets before emission,
- avoid hash-iteration dependence,
- define stable ordering for symbols, units, and statements,
- include a CI job that checks byte-identical output for a canonical build.

### 6.5 Diagnostics Loop (Developer Experience)

The correct loop is:

1) generator/linker emits  
2) verifier rejects (if wrong)  
3) SourceMap maps error back  
4) developer fixes Python generator/contracts  
5) repeat

We should optimize for “time-to-actionable-error”, not for “time-to-first-big-library”.

### 6.6 Compatibility Policy

Compatibility mode (allowing raw-string tokens) is permitted only as a bootstrap tool and must have:

- an explicit flag (e.g. `--compat` or `ALLOW_STRING_TOKENS=1`),
- a deprecation plan (compat usage must be tracked and reduced),
- tests that ensure it does not silently become the default.

**CI shock therapy (default-off):**
- After **M1.2 Global symbol resolution + early lint** lands, CI runs with `ALLOW_STRING_TOKENS=0` by default.
- Any remaining compat usage must be explicitly allowlisted (legacy/bridge only) and must carry a visible marker in code/tests.
- A build that introduces raw-string tokens outside an allowlisted compat target fails fast with an origin-linked diagnostic.

---

## 7. Project Hygiene (Recommended Defaults)

- Prefer small ProofUnits with clear exports.
- Treat interface contracts as public API (version them accordingly).
- Avoid private variable proliferation; deterministically rename private vars to prevent collisions and uncontrolled `$d` growth.
- Keep performance work behind semantic gates; do not optimize before invariants are stable.

---

## 8. Definition of Done (DoD)

A feature is “done” when:

1. It is specified (doc-first) with invariants and acceptance tests.
2. It is implemented as a pass with explicit pre/post conditions.
3. It has:
   - at least one sanity test,
   - at least one adversarial test (if applicable),
   - determinism checks (if emission is affected).
4. Diagnostics are actionable:
   - failures map back to origin/unit/stmt/step.

---

## 9. Appendices

### Appendix A — Stage Mapping (v3)

For implementation tracking, the linker pipeline stages are:

- Stage 0: IR construction (Python -> HIR/LIR)
- Stage 1: symbol resolution + early lint
- Stage 2: contract extraction
- Stage 3: `$d` processing (modes A/B/C)
- Stage 4: dependency resolution (closure DAG)
- Stage 5: scope planning (ScopeFrames)
- Stage 6: relocation (token-level)
- Stage 7: two-phase emission
- Stage 8: SourceMap + diagnostics

