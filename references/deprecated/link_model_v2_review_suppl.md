# ProofScaffold Linker — v2 Review Notes (Final)

**Architectural Risk Register & Evolution Roadmap**

## 0. Scope & Intent

This document collects **all known limitations, deferred design points, and semantic edge cases** identified during the Rev.2 design phase.

It serves as a **binding contract** for the MVP. Deviating from the boundaries defined below is not an "experimental feature"—it is an architectural violation that will lead to correct-looking but semantically broken proofs.

---

## 1. MVP Validity Criterion (The Hard Boundary)

**Status**: **Strict Enforcement**.

To prevent ambiguity about "how much" logic the MVP supports, we define the following hard criterion:

> **MVP Validity Criterion**
> A proof is within MVP scope **IF AND ONLY IF** every substitution performed during verification is **variable-free**.
> *(i.e., no `$v` is ever substituted by an expression containing variables).*

**Practical Consequence**:
Any attempt to perform quantifier instantiation () constitutes a **v2 violation** and is undefined behavior in the MVP.

---

## 2. Deferred Semantic Constraints (`$d`)

### 2.1 The Non-Repairability of `$d`

**Status**: Not implemented in MVP.
**Risk**: Critical (Silent semantic failure).

#### Issue

The MVP Linker does not track disjoint variable (`$d`) constraints.

#### Critical Warning

> **$d violations are non-local and non-repairable at link-time.**
> Once a proof body is emitted without correct `$d` contracts, no amount of post-hoc scope rearrangement or linear shuffling can fix it.
> *Do not attempt to "patch" missing `$d` constraints manually in the output stream.*

#### Required v2 Work

(See Appendix) Implement Automated Constraint Inference.

---

## 3. Forbidden Patterns (Defensive Engineering)

**Status**: **Prohibited**.

The following patterns are explicitly forbidden in both MVP and v2 Python generators, as they break the Linker's ability to reason about dependency closures:

1. **Cross-Fragment Label Peeking**: Directly referencing another fragment's internal `$f` or `$e` labels (e.g., `ref("other_mod.internal_hyp")`). You must only link against exported Theorems (`$a/$p`).
2. **Implicit Context Reliance**: A proof body depending on hypotheses that are not included in its explicit export contract.
3. **Zombie Assumptions**: A generator assuming that upstream hypotheses remain active beyond the specific Theorem Unit boundary.

---

## 4. `$v` Hoisting & Namespace Pollution

**Status**: Mitigated via Name Mangling.
**Risk**: Medium.

#### Issue

MVP hoists all `$v` to the global header.

#### Practical Consequence

Common names (`ph`, `x`) are globally shared. Without strict name mangling in the generator (e.g., `ctx.resolve("x")`), unintended variable capture may occur.

---

## 5. Token-Level Relocation

**Status**: Deferred.
**Risk**: Medium (Engineering Debt).

#### Issue

The Linker does not rewrite internal proof tokens. Generators must emit **already-mangled** symbol names via helper APIs.

---

## Appendix: Evolution Strategy — From Propositional to First-Order Logic

To bridge the gap to FOL, we define an additive progression for `$d` constraints.

### Stage 1: Explicit Contract (MVP)

* **Mechanism**: "Dumb Pass-through."
* **Behavior**: Manual bookkeeping. FOL is possible *only* if the user manually validates the MVP Validity Criterion is not violated (or manually adds `$d`).

### Stage 2: Verification-Guided Propagation (The Linter)

* **Mechanism**: "Requirement Discovery."
* **Behavior**: Tooling parses verifier errors to prompt users for missing constraints.

### Stage 3: Automated Constraint Inference (The Solver)

* **Mechanism**: "Constraint Bubbling."
* **Behavior**: The Linker uses a Union-Find structure to bubble requirements up.

#### Non-Optimality Guarantee

> **Automated `$d` inference is permitted to be sound but not minimal.**
> The solver may generate excessive `$d` constraints to ensure safety. Missing constraints are a bug; redundant constraints are acceptable overhead.
