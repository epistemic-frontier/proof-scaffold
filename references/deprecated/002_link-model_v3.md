# ProofScaffold Linker Model v3

## Semantic Contracts, Token Relocation, and Disjoint-Variable Support (Rev. 3)

**Status**: Draft specification text (middle-end).
**Supersedes**: Linker Model Rev. 2. 
**Incorporates**: v2 risk register and non-negotiable semantic boundaries (especially `$d` non-repairability, and the MVP validity criterion). 
**Project framing**: ProofScaffold is a build/link toolchain; Python is the builder, Metamath is the verifier and the ultimate semantic authority. 

---

## 0. Purpose and Scope

ProofScaffold Linker Model v3 defines the **formal IR**, **contracts**, and **data-flow pipeline** required to transform a dependency DAG of proof components (built in Python) into a **single, semantically valid Metamath stream** that a verifier can check.

This is a **middle-end specification**: it defines invariants, interfaces, and transformation stages, but does not mandate implementation details (storage layout, caching, streaming APIs, etc.). 

### 0.1 What v3 adds vs v2 (motivations)

v3 addresses the key architectural risks documented in the v2 review notes:

1. **First-order correctness readiness**: explicit modeling and propagation of **disjoint-variable constraints (`$d`)**; `$d` is treated as **non-local and non-repairable post hoc**. 
2. **Precise export contracts**: strict separation of **interface requirements** vs **proof-closure requirements** (“ghost dependency” elimination). 
3. **Token-level relocation**: proof tokens and math strings are represented as **symbol references**, enabling systematic rewriting during linking (no generator–linker naming coupling). 
4. **Explicit scope frames**: linear IR makes scope and active context explicit, enabling better debugging and future incremental verification. 

---

## 1. Design Principles (v3 Contract)

The v3 linker model is governed by the same four foundational principles as Rev.2:

1. **Explicitness**: dependencies, symbols, scopes, substitutions, and transformations are explicit in IR.
2. **Determinism**: same input IR produces the same output stream (including names).
3. **Untrusted generation**: Python and the linker are not trusted; the verifier must reject invalid output.
4. **Incremental verifiability**: each stage admits sanity checks and localized debugging. 

---

## 2. High-Level Pipeline

v3 introduces a two-tier IR to support both (a) Metamath emission and (b) optional structural information for `$d` inference and strict MVP checks.

```
Python Modules / Packages
  ↓
[HIR Graph]  (optional; structured proof ops + substitution metadata)
  ↓ lowering
[LIR Graph]  (required; Metamath-like statements + proof tokens as symbol refs)
  ↓ (dependency resolution + scope planning + relocation)
[Linear LIR + ScopeFrames]
  ↓ emission
Metamath Stream  → Verifier Backend
  ↓
Verifier Diagnostics  → SourceMap  → Linter / Developer Feedback
```

Notes:

* The verifier remains a black box; correctness is ultimately established by verifier execution. 
* If HIR is absent, v3 still links and emits, but `$d` inference and “MVP strict substitution checking” degrade to linter-driven workflows. 

---

## 3. Core Entities

### 3.1 Symbol Model

#### 3.1.1 SymbolId

An internal, stable identifier used throughout IR; never emitted directly to Metamath.

#### 3.1.2 SymbolDef

A symbol definition record:

* `origin`: module/package identity (e.g., Python import path)
* `local_name`: human-facing name within origin
* `kind`: one of `{Const, Var, Label}`

  * `Const` corresponds to `$c`
  * `Var` corresponds to `$v`
  * `Label` corresponds to `{ $f, $e, $a, $p }`
* `scope_class`: one of `{global_only, nest_safe}`

  * retained from v2 for emission constraints; v3 additionally uses explicit scope frames.

#### 3.1.3 SymbolRef

A reference to a `SymbolId`.

**v3 rule**: IR must not represent proof tokens or math-string tokens as raw strings (unless in an explicit compatibility mode). All emitted tokens originate from `SymbolRef → emitted_name` relocation.

---

### 3.2 Statement Model (LIR)

LIR statements are Metamath-shaped, but their token payloads are symbol references.

#### 3.2.1 Unlabeled statements

* `ConstDecl`: `$c c1 c2 ... $.`
* `VarDecl`: `$v v1 v2 ... $.`
* `DisjointDecl`: `$d v1 v2 ... $.` (scope-sensitive)
* `ScopeEnter`: `${`
* `ScopeExit`: `$}`

#### 3.2.2 Labeled statements

* `FloatingHyp`: `label $f <type> <var> $.`
* `EssentialHyp`: `label $e <math_string> $.`
* `Axiom`: `label $a <math_string> $.`
* `Theorem`: `label $p <math_string> $= <proof_tokens> $.`

Where:

* `<type>`, `<var>`, `<math_string>`, `<proof_tokens>` are **lists of `SymbolRef`**.

---

### 3.3 ProofUnit (Linkable / Verifiable Unit)

A **ProofUnit** is the smallest unit of linkage discipline in v3. It replaces the “Proof Fragment” as the primary contract boundary (v2 fragments may be considered a legacy packaging convenience).

A `ProofUnit` contains:

* `unit_id`: stable internal id
* `decls_local`:

  * local hypotheses (`$f/$e`) required to define or prove exports
  * local disjoint declarations (`$d`) required at definition sites
  * optional internal helper labels (private assertions), if permitted by policy
* `exports`: the list of exported assertions (typically 1 theorem/axiom, but may be multiple)
* `proof_body`:

  * **required**: LIR proof tokens (`SymbolRef` list)
  * **optional**: HIR proof ops (structured form; see §3.4)

**Policy constraint (defensive engineering)**: a unit may depend on other units only via their **exported assertions** (`$a/$p`), never by peeking at internal `$f/$e` labels. 

---

### 3.4 HIR (Optional Structured Proof Representation)

HIR is optional but enables advanced semantics:

* `$d` constraint inference (solver mode)
* “MVP strict” validity checking (variable-free substitution)
* higher quality source mapping (proof-step provenance)

Minimal HIR structure:

* `Apply(assertion: SymbolRef, subst: SubstMap, step_id)`
* `SubstMap`: mapping from variables to expressions, where expressions may carry a `free_vars` set/digest.

HIR is **not** a proof assistant language; it is a structured trace of what the generator intended.

---

## 4. Contracts

v3 makes contracts explicit and splits them into two layers.

### 4.1 Interface Contract (Export Contract)

For each exported assertion `A` (axiom or theorem), the interface contract includes:

* `mandatory_hyps(A)`:

  * ordered list of mandatory `$f` (first) and `$e` (then)
* `mandatory_vars(A)`:

  * the set (and deterministic ordering) of variables mandated by Metamath’s mandatory-variable rules
* `dv_contract(A)`:

  * the required disjoint-variable pairs on `mandatory_vars(A)` that must be active at `A`’s definition site
* `public_symbols(A)`:

  * externally linkable symbols are limited to exported `$a/$p` labels (never `$f/$e`)

### 4.2 Proof Closure Contract (Implementation Closure)

For each theorem `T`:

* `uses_assertions(T)`:

  * the set of referenced `$a/$p` labels appearing in its proof token list (or HIR)
* optional: `uses_subst(T)`:

  * structured substitution digests per `Apply`, if HIR exists

**Key guarantee**: “Interface linkability” and “proof verifiability” are distinct; a theorem’s proof closure must be explicitly resolvable and emitted in a context where all required labels are defined and usable.

This split is a direct response to “ghost dependencies.” 

---

## 5. Scope Model

### 5.1 ScopeFrames

v3 introduces explicit **ScopeFrames** in the linear IR. A `ScopeFrame` is a contiguous region of statements delimited by:

* `ScopeEnter`
* `ScopeExit`

The scope frame controls the activity of:

* `$f` and `$e` hypotheses (reachability / active context)
* `$d` declarations (disjoint constraints active at binding points)

### 5.2 Active Context Snapshot

For any position in Linear LIR, the linker can compute (at least conceptually):

* `active_f_labels`: the set of active `$f` labels
* `active_e_labels`: the set of active `$e` labels
* `active_d_pairs`: the set of active disjoint pairs (over variables)

This snapshot is used for:

* validating that proof steps do not rely on implicit context
* enriching source maps and diagnostics
* preparing future incremental verification

---

## 6. v3 Invariants (Middle-End Non-Negotiables)

### 6.1 Deterministic emission

* The linear order of units and the resulting output stream must be deterministic.

### 6.2 No cross-unit hypothesis leakage

* A proof may not rely on hypotheses outside its own unit unless explicitly reintroduced in its scope plan (see §7.4).
* Cross-unit referencing of internal `$f/$e` is forbidden. 

### 6.3 `$c/$v` legality via hoisting

* All `$c` and `$v` declarations are emitted in a global header phase.
* They are never emitted inside a nested scope in the final stream (even if declared locally in Python). 

### 6.4 Token-level integrity

* All token occurrences (labels, math strings, proof tokens) must pass through relocation:

  * no pre-mangled names required from generators
  * no stringly-typed proof bodies (except explicit compatibility mode) 

### 6.5 `$d` binding correctness (non-repairability)

* A theorem/axiom’s `dv_contract` must be active at the **definition site** of that assertion.
* Missing `$d` cannot be “patched later” by rearranging scopes after emission; therefore `$d` is part of the assertion’s interface contract. 

### 6.6 Scope balance

* Linear IR must be scope-balanced: no dangling `${` or `$}` across unit boundaries (unless units are explicitly defined as scope-aware in a future extension). 

---

## 7. Linker Stages (v3)

### Stage 0 — Front-end IR construction

Inputs:

* Python modules / generators
  Outputs:
* Symbol registrations (`SymbolDef`)
* ProofUnits
* LIR graph (required), HIR graph (optional)

### Stage 1 — Symbol resolution and early lint

* Build global symbol table: `(origin, local_name, kind) → SymbolId`
* Resolve all tokens into `SymbolRef`
* Enforce forbidden patterns:

  * cross-unit `$f/$e` references in proof tokens → error
  * references to non-exported labels → error
  * raw-string tokens (outside compatibility mode) → error

### Stage 2 — Contract extraction

* Compute `mandatory_hyps`, `mandatory_vars` for each exported assertion
* Extract `uses_assertions` for theorem proofs (closure graph)
* (Optional) extract substitution digests from HIR

### Stage 3 — `$d` processing (configurable)

v3 defines three modes (additive evolution strategy):

#### Mode A: Pass-through (explicit `$d`)

* Generator provides `dv_contract` and/or explicit `$d` decls.
* Linker emits them at correct binding points without inference.

#### Mode B: Linter-driven propagation

* Linker does not infer `$d`.
* It maps verifier disjointness errors back to IR source locations and prompts the developer to amend `dv_contract` or local `$d` declarations.

#### Mode C: Solver-driven inference (recommended)

Requires: HIR with `Apply + SubstMap`.

Inference rule (soundness-first, not necessarily minimal):

For each `Apply(L, σ)` inside theorem `T`:

* For each pair `(x, y)` in `dv_contract(L)`:

  * add all pairs in `Vars(σ(x)) × Vars(σ(y))` into `required_d_pairs(T)`

Then:

* `local_d_pairs(T)` may include pairs needed only for internal proof safety.
* `interface_d_pairs(T)` is the restriction of required pairs to `mandatory_vars(T)`.

Finally:

* emit `$d` declarations needed to ensure:

  1. `interface_d_pairs(T)` is active at `T`’s definition
  2. `local_d_pairs(T)` is active in the scopes where `T`’s proof is emitted

This rule is explicitly allowed to be non-minimal; redundant `$d` is acceptable overhead. 

### Stage 4 — Dependency resolution (closure DAG)

* Topologically sort ProofUnits using `uses_assertions` edges
* Detect and reject cycles

### Stage 5 — Scope planning (ScopeFrames)

Baseline emission strategy (conservative, simple, robust):

For each ProofUnit:

* open a fresh scope frame
* emit unit-local `$f/$e/$d`
* emit the exported assertion (`$a` or `$p`)
* close the scope frame

This ensures:

* no implicit context reliance
* clean binding points for `$d`
* strong debuggability

Future optimization (optional): merge compatible units into shared frames only when contract checks prove there is no context leakage.

### Stage 6 — Relocation (namespace flattening)

* Compute deterministic `emitted_name(SymbolId)` for all symbols
* Rewrite:

  * all labels (`$f/$e/$a/$p`)
  * all `$c/$v` tokens in math strings
  * all proof tokens referencing labels

Recommended mangling strategy (same philosophy as v2, now applied uniformly):

1. readable deterministic prefixing (`local @ origin → local__origin`)
2. collision: append deterministic hash suffix
3. if length limits apply: truncate + preserve suffix 

### Stage 7 — Two-phase emission

1. **Global header**:

   * all `$c`
   * all `$v`
2. **Body**:

   * linear stream of ScopeFrames and statements (including `$d/$f/$e/$a/$p`)

### Stage 8 — Source maps and diagnostics

Emit SourceMap that can map verifier errors to semantic locations.

Minimum mapping fields:

* `stream_span → (origin, unit_id, stmt_id, label?, proof_step_idx?)`

Recommended enrichment (to address “beyond byte offsets” debugging):

* active hypothesis snapshot digest (`active_f/e`)
* used assertion id for each proof step
* optional substitution digest (if HIR exists) 

---

## 8. Variable Model and `$v` Hoisting Discipline

Metamath variables are effectively global once declared. v3 keeps v2’s hoisting rule for correctness and stability, but reduces engineering harm via naming discipline:

* `public_v`: stable, human-readable variable names intended for broad reuse (e.g., `ph`, `ps`)
* `private_v`: unit-local variables that must be deterministically renamed (e.g., `v__<unit_id>__x`) to avoid accidental collisions and to control `$d` growth risks

The linker may optionally omit declaring unused private variables entirely, but **if declared**, they are hoisted to the global header.

---

## 9. MVP Strict Mode (Propositional-Scope Guardrail)

The v2 review defines a hard MVP boundary:

> A proof is within MVP scope iff every substitution performed during verification is variable-free. 

v3 operationalizes this boundary as an optional linker check:

When `MVP_STRICT = true`:

* Require HIR substitution metadata (or an explicit generator declaration of “no substitutions with variables”)
* For each substitution mapping `$v → expr`:

  * reject if `expr` contains any variables
* If the check fails:

  * either reject the build, or require switching to `$d` mode (FOL mode) with explicit or inferred disjoint constraints

---

## 10. Verifier Interface Boundary (Trust Model)

The verifier is authoritative for semantic correctness. The linker guarantees:

* syntactic well-formedness of emitted Metamath
* structural invariants (scope balance, ordering, token relocation, contract adherence)

The verifier remains responsible for:

* parsing
* stack discipline
* substitution semantics
* proof checking
* rejecting invalid proofs 

---

## 11. Non-goals and Deferred Topics (v3)

v3 explicitly does not standardize:

* proof compression formats
* caching and incremental re-check implementations (though ScopeFrames + SourceMap enable them)
* performance mechanisms (zero-copy, shared memory, streaming I/O), which remain deferred until semantics stabilize 

---

## 12. Compatibility Notes (Rev.2 → Rev.3)

* The v2 “Proof Fragment” concept can be mapped to v3 “ProofUnit” by treating each fragment as a unit with one export; however, v3’s contract split (interface vs closure) is mandatory.
* v2 relocation is extended from “definitions only” to **token-level relocation** (math strings and proof tokens).
* v2 scope-balance remains required, but v3 makes scopes explicit via ScopeFrames and context snapshots.

---

## 13. FAQ (Design Clarifications)

### Q1. Does `$d` inference turn the Linker into an automated theorem prover?

No. In ProofScaffold, the Linker is a **build/link** component, not a prover.

* The Linker may *propagate* already-declared semantic obligations (e.g., disjoint-variable contracts) through **recorded substitutions** (when HIR metadata exists), but it performs **no proof search**, **no backtracking**, and **no theorem discovery**.
* The output remains **untrusted**: any incorrect `$d` handling must be rejected by the Metamath verifier.

Practical note: for clarity, the `$d` “solver” phrasing should be read as **constraint propagation**, not theorem proving.

### Q2. `$d` is “non-repairable”. How do we develop proofs without getting stuck?

`$d` must be active at an assertion’s definition site; missing `$d` cannot be safely patched later by rearranging scopes.

To keep development incremental, the linker model supports staged workflows:

* **Pass-through mode**: generators provide explicit `$d` (and/or explicit `dv_contract`), and the linker only places them at binding points.
* **Linter-driven mode**: if `$d` is missing, the verifier error is mapped back (via SourceMap) to the generating unit/step so the developer can amend contracts or local `$d`.
* **HIR-assisted propagation mode**: when HIR substitutions are available, the linker can propagate known disjointness requirements through those substitutions.

### Q3. How do we keep the Linker “dumb” while avoiding `$d` bloat or over-constraining interfaces?

The intended balance is achieved by **separating interface obligations from local proof safety**:

* **Interface `$d`** should be limited to what is required on the theorem’s **mandatory variables** (Metamath’s interface surface).
* **Local `$d`** may be more conservative, but must be **scoped** (via ScopeFrames) so it does not leak into unrelated theorems.

Two engineering levers keep `$d` growth under control:

1. Make `Vars(expr)` (free-variable sets) as **precise** as practical in HIR substitution metadata.
2. Treat any `$d` “minimization” as an **optional optimization pass**, never as a semantic requirement.

### Q4. Will the IR be too memory-heavy if implemented as Python objects per token?

The IR types (SymbolId/SymbolRef/Statements) are a **semantic model**, not an implementation mandate.

For large libraries, the recommended representation is:

* SymbolRef as **integer IDs** (dense indices), not heap objects.
* Token lists as **contiguous arrays** (e.g., `array('I')`, `numpy`/`pyarrow`-like buffers, or custom packed buffers).
* “Struct-of-arrays” layouts for tables (symbol table, statement table), to reduce per-object overhead and improve locality.

This keeps Python as the orchestrator while allowing data to live in compact, GC-friendly memory.

### Q5. What does “zero-copy verification” mean here?

“Zero-copy” refers to avoiding:

* writing intermediate `.mm` files to disk, and/or
* copying large proof streams between components.

A typical strategy is:

* the linker emits a **single contiguous byte buffer** (or shared-memory segment) for the Metamath stream,
* the verifier backend consumes it via **buffer protocols / shared memory views**.

The goal is to keep the hot path as “compute over I/O”, while still preserving verifier authority.

### Q6. If names are mangled by relocation, how do we keep debugging humane?

Relocation is required because Metamath’s namespace is global, while Python modules are scoped.

To prevent “linker-error nightmares”, SourceMaps should support an **unmangled view**:

* Map verifier spans and labels back to: `(origin module, local_name, unit_id, stmt_id, proof_step_idx)`.
* Provide a “debug slice” view: show the surrounding scope frame and the active context snapshot (active `$f/$e/$d` digests) near the failing step.
* Optionally emit a **minimal reproducer stream** for the failing ProofUnit (still verifier-checkable, but small enough to inspect).

The guiding rule is: developers should fix **Python generators and contracts**, not hand-edit emitted Metamath.

### Q7. Is HIR optional or required?

HIR is optional for **bootstrap linkage**, but it becomes effectively required for “modern” capabilities:

* Without HIR, the system can still answer “**where** did this fail?” (unit/statement/step localization).
* With HIR, the system can often explain “**why** did this fail?” (substitution provenance, `$d` propagation, MVP strict checks).

A practical way to formalize this is via conformance levels:

* **Level 0 (Bootstrap)**: LIR-only; no strict substitution checks; `$d` handled via pass-through or linter-driven workflows.
* **Level 1 (MVP Strict)**: requires substitution metadata sufficient to enforce “variable-free substitution” within MVP scope.
* **Level 2 (FOL-ready)**: requires HIR with free-variable sets (or equivalent digests) to support robust `$d` propagation and richer diagnostics.

### Q8. What “toy models” should we build early to de-risk the design?

Three minimal experiments cover most structural risks:

1. **`$d` propagation stress test**: feed small HIR patterns with substitutions and measure growth of required `$d` pairs, especially at the interface boundary.
2. **Representation microbenchmark**: compare per-token Python objects vs packed integer buffers for millions of tokens.
3. **Diagnostics loop test**: intentionally introduce a verifier error and ensure it maps back to a single ProofUnit + proof-step context with an unmangled view.

These should be kept as “sanity checks”: small, stable, and always runnable.

---

# Appendix A — LIR / HIR Format Specification (v0.1)

## A.1 Purpose and Design Principles

This appendix specifies the **Low-level Intermediate Representation (LIR)** and the **High-level Intermediate Representation (HIR)** used by the ProofScaffold toolchain.

The core design principles are:

1. **LIR is mandatory, HIR is optional.**
2. **LIR is Metamath-shaped but symbol-normalized.**
3. **HIR is semantic structure, not a proof language.**
4. **All linking, relocation, and verification operate on IR, never on raw strings.**

The IR formats are designed to support:

* deterministic linking,
* token-level relocation,
* precise error diagnostics,
* and future semantic extensions (e.g. `$d` propagation, MVP_STRICT).

---

## A.2 Symbol Model (Shared by LIR and HIR)

All tokens appearing in LIR or HIR MUST be represented as `SymbolRef`.

```text
SymbolDef:
  id: SymbolId
  kind: CONST | VAR | TYPECODE | LABEL
  origin: (module_id, file, line)
  attributes: opaque map

SymbolRef:
  symbol_id: SymbolId
```

String literals MAY appear only as:

* debug hints,
* source annotations,
* or legacy compatibility fields.

They MUST NOT participate in linking or verification.

---

## A.3 LIR: Low-level Intermediate Representation

### A.3.1 Scope Structure

LIR explicitly represents Metamath scoping.

```text
ScopeEnter
ScopeExit
```

Scopes are **atomic**: declarations and assertions are not interleaved across scopes.

---

### A.3.2 Unlabeled Statements

```text
ConstDecl(symbol)
VarDecl(symbol)
DisjointDecl(symbols[])
```

All symbols are `SymbolRef`.

---

### A.3.3 Labeled Statements

```text
FloatingHyp:
  label
  typecode
  var

EssentialHyp:
  label
  typecode
  expr[]

Axiom / Theorem:
  label
  typecode
  expr[]
  proof_tokens[]   // SymbolRef[]
```

`proof_tokens` MUST already be tokenized into symbol references.
No string-level proof parsing occurs after this stage.

---

### A.3.4 Required Engineering Fields

Each LIR statement MUST carry:

```text
stmt_id        // stable within compilation unit
origin         // source provenance
span_hint      // optional source map anchor
```

These fields are mandatory to enable deterministic diagnostics and relocation.

---

## A.4 HIR: High-level Intermediate Representation

### A.4.1 Scope of HIR

HIR provides **structured semantic traces** over LIR proofs.

HIR:

* does NOT perform proof search,
* does NOT replace Metamath semantics,
* does NOT define a new logic.

HIR exists solely to make **implicit structure explicit**.

---

### A.4.2 Minimal HIR Kernel (v0.1)

The only required HIR operation is `Apply`.

```text
Apply:
  step_id
  assertion_ref      // SymbolRef
  substitution_map   // var_ref -> expr[]
```

Optionally, an `Apply` node MAY carry:

```text
free_vars: Set[SymbolRef]
or
expr_digest: Hash
```

Either is sufficient for:

* MVP_STRICT checks,
* `$d` constraint propagation,
* semantic diagnostics.

---

### A.4.3 Stability Guarantees

* LIR v0.1 is **frozen** except for additive fields.
* HIR v0.1 is **experimental**, but its core `Apply` form is expected to remain stable.

---

# Appendix B — Relationship Between LIR / HIR and the Generator

## B.1 Generator as IR Producer

The Generator is responsible for producing **well-formed IR**, not Metamath source.

Its responsibilities are:

1. Emit complete LIR units.
2. Allocate stable `SymbolId`s.
3. Preserve source provenance.
4. Optionally emit HIR traces.

The Generator MUST NOT:

* rely on global symbol names for correctness,
* emit raw string proofs as final artifacts.

---

## B.2 Generator → LIR Contract

The Generator guarantees that:

* All symbols used are declared in-scope.
* All proof tokens are resolved to `SymbolRef`.
* Scope boundaries are explicit.
* LIR units are internally consistent.

The Linker is NOT required to:

* infer missing scopes,
* guess symbol intent,
* recover from malformed LIR.

Malformed LIR is a generator error.

---

## B.3 Generator → HIR Contract

HIR emission is **optional**.

If emitted, the Generator guarantees:

* Each `Apply` references a valid LIR assertion.
* Substitutions respect declared variables.
* HIR steps are aligned with LIR proof order.

The Linker MAY:

* ignore HIR entirely,
* partially consume HIR (e.g. for diagnostics),
* or enforce stricter checks in MVP_STRICT mode.

---

## B.4 Compatibility and Degradation Strategy

Three operational modes are defined:

| Mode       | LIR      | HIR      |
| ---------- | -------- | -------- |
| MVP        | required | ignored  |
| MVP_STRICT | required | optional |
| FUTURE     | required | required |

The system MUST degrade gracefully:

* absence of HIR MUST NOT break linking,
* presence of HIR MUST NOT alter proof semantics.

---

## B.5 Architectural Consequence

This separation ensures that:

* Metamath remains the semantic ground truth.
* IR becomes the sole operational interface.
* Advanced features can evolve without destabilizing the MVP.

---

**End of specification.**
