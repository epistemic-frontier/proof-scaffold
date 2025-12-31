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

**End of specification.**
