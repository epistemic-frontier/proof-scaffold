# ProofScaffold Linker — v2 Review Notes

**Architectural Risk Register & Evolution Roadmap**

## 0. Scope & Intent

This document collects **all known limitations, deferred design points, and semantic edge cases** identified during the Rev.2 design and MVP prototyping phase.

These items are **explicitly out of scope for the MVP (v1)**, but are mandated for the future **v2 linker iteration**.

Beyond listing deferred items, this document records their **practical consequences and usage boundaries**. This ensures that MVP users (and developers) do not misinterpret *deliberate design boundaries* as *implementation defects*.

> **Purpose**: To provide architectural continuity and expectation management, strictly separating the "Propositional Logic MVP" from the "First-Order Logic v2".

---

## 1. Deferred Semantic Constraints (`$d`)

### 1.1 Disjoint Variable Constraints

* **Status**: Deferred (Not implemented in MVP).
* **Risk**: High (Semantic Correctness).
* **Practical Impact**: **Severe** (Limits MVP to Propositional Logic).

#### Issue

Metamath proof validity depends on active `$d` (disjoint) constraints during substitution. The current MVP IR models symbol reachability (`$c/$v/$f/$e`) but **completely ignores** `$d`.

Consequently, a topologically correct, scope-balanced stream produced by the MVP Linker may still be **rejected by the verifier** due to illegal substitutions in First-Order Logic contexts.

#### Practical Consequence

Because `$d` constraints are essential for avoiding variable capture:

* The MVP Linker is **effectively limited to Propositional Logic**.
* Proofs involving **Quantifiers** (), **Set Theory**, or any context requiring variable distinctness are **unsupported**.

#### Usage Guidance (MVP Phase)

* **DO TEST**:
* Modus Ponens (`ax-mp`) chains.
* Propositional calculus (`|- ( ph -> ps )`).
* Simple axiom chaining.


* **DO NOT TEST**:
* Quantifier introduction/elimination.
* Complex substitutions requiring `$d`.



#### Required v2 Work

(See Appendix for detailed Evolution Strategy)

* Extend Exported Context to include required `$d` sets.
* Enforce **Disjoint Variable Reachability** at emission points.

---

## 2. `$v` Hoisting & Variable Isolation

### 2.1 Global `$v` Hoisting Side Effects

* **Status**: Mitigated via Name Mangling.
* **Risk**: Medium → High (Scales with project size).

#### Issue

In MVP, all `$v` declarations are hoisted to the global header to ensure reachability. While syntactically valid, this removes lexical isolation.

#### Practical Consequence

* **Namespace Pollution**: Common variable names (`x`, `y`, `ph`) become globally visible.
* **`$d` Explosion**: In v2, this lack of isolation could lead to an exponential number of required `$d` pairs if not managed by scopes.

#### Required v2 Work

* Explicitly distinguish **Public `$v**` (interface) vs **Private `$v**` (implementation) in IR.
* Enforce deterministic naming isolation for private variables (e.g., `pkg__func__var_x`).
* Implement selective `$v` hoisting based on export contracts.

---

## 3. Export Contract Precision

### 3.1 Interface vs. Implementation Dependencies

* **Status**: Not modeled.
* **Risk**: High (Link-time verifier failures).

#### Issue

Metamath proofs have two distinct dependency layers:

1. **Assertion Interface**: Requirements visible to the caller (Mandatory Hypotheses, Variables).
2. **Proof Implementation**: Requirements internal to the proof (Lemmas, internal Hypotheses).

The MVP IR treats these as a single flattened list.

#### Practical Consequence

A theorem may appear linkable, yet fail verification because its proof body references a lemma whose context is **no longer active** at the emission site. This results in "ghost dependencies" that are hard to debug.

#### Required v2 Work

* Split Fragment dependencies into **Interface Requirements** and **Proof Closure Requirements**.
* Compute the transitive closure of dependencies for both layers explicitly.

---

## 4. Token-Level Relocation

### 4.1 Generator-Linker Coupling

* **Status**: Deferred.
* **Risk**: Medium (Engineering Debt).
* **Practical Impact**: Generator logic is coupled to Linker naming strategy.

#### Issue

The MVP Linker relocates definitions but does not rewrite internal proof tokens. Python generators are expected to emit **already-mangled** symbol names.

#### Practical Consequence

Generators cannot simply write `ref("ax-mp")`; they must predict the final name, e.g., `ref("logic__ax-mp")`. This makes generator code brittle.

#### Usage Guidance (MVP Phase)

To mitigate coupling without full token rewriting, use a helper API in the Python layer:

```python
# GOOD: Abstraction layer
ctx.resolve("ax-mp") 

# BAD: Hardcoded coupling
return "logic__ax-mp"

```

#### Required v2 Work

* Represent proof tokens as resolved **Symbol References** (not strings) in the IR.
* Perform systematic token rewriting during the Linearization phase.

---

## 5. Scope & Context Modeling

### 5.1 Fine-Grained Scope Tracking

* **Status**: Minimal (Fragment-level only).
* **Risk**: Medium.

#### Issue

The MVP enforces that fragments are *balanced*, but it has no internal model of nested `${ ... $}` structures. It treats the body of a proof as an opaque blob.

#### Required v2 Work

* Introduce explicit **Scope Frames** in the Linear Proof IR.
* Track active hypotheses and context snapshots per frame to enable advanced features like incremental verification.

---

## 6. Debugging & Source Maps

### 6.1 Beyond Byte Offsets

* **Status**: Coarse mapping.
* **Risk**: Medium (Developer Experience).

#### Issue

Verifier errors often correspond to **Logical Context Mismatches** (e.g., "Missing hypothesis X"), not just syntax errors at a specific line. Byte offsets are insufficient for debugging logic errors.

#### Required v2 Work

* Enrich Source Maps with **Semantic Metadata**: Fragment IDs, Symbol Instantiation Context, and Active Hypothesis Sets.

---

## 7. Performance & Streaming

* **Status**: **Explicitly Deferred**.
* **Risk**: Low (Non-functional).

Features such as **Zero-copy verification**, **Shared Memory Streams**, and **Proof Caching** are postponed until the semantic linker model is fully stable.

---

## 8. Summary & Contract

### MVP (v1) Guarantees

* ✅ Deterministic Linkage
* ✅ Symbol Relocation (Name Collision Safety)
* ✅ Global `$c/$v/$f` Legality
* ✅ Scope-Balanced Emission

### Known MVP Boundaries (The "Chasm")

* ⚠️ **Propositional Logic Only** (No `$d` support).
* ⚠️ **Coupled Naming** (Generators must use helpers).
* ⚠️ **Opaque Proof Bodies** (No internal rewriting).

### v2 Objectives

* 🚀 **First-Order Logic Support** (Automated `$d` management).
* 🚀 **Precise Export Contracts**.
* 🚀 **Token-Level Integrity**.

---

## 9. Closing Note

This document is **not a backlog**. It is a **conscious record of deferred power**.

Every limitation listed here is a result of **explicit architectural choice**, not oversight. This clarity is what allows the MVP to remain small, correct, and finishable.

---

## Appendix: Evolution Strategy — From Propositional to First-Order Logic

To bridge the gap from Propositional Logic to First-Order Logic (FOL) without a core rewrite, we define an **additive three-stage progression** for handling `$d` constraints:

### Stage 1: Explicit Contract (MVP)

* **Mechanism**: "Dumb Pass-through."
* **Behavior**: The Python generator explicitly declares required `$d` sets manually. The Linker emits them faithfully but performs no validation.
* **Goal**: Enable FOL *possibility* immediately, with manual bookkeeping.

### Stage 2: Verification-Guided Propagation (The Linter)

* **Mechanism**: "Requirement Discovery."
* **Behavior**: Tooling parses verifier error logs (e.g., "Disjoint violation x, y") and maps them back to Source Maps, prompting the user to add missing constraints via the "Linter" interface.

### Stage 3: Automated Constraint Inference (The Solver)

* **Mechanism**: "Constraint Bubbling."
* **Behavior**: The Linker integrates a **Union-Find data structure**. It analyzes substitutions, calculates the `$d` constraints required by child lemmas, and automatically "bubbles" them up to the parent theorem's interface.

> **Core Principle**: *Explicit beats Implicit.* Even in Stage 3, manual user constraints will always override automated inference.