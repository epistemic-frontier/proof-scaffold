# An Authoring-First Architecture for Logical Systems

## 1. Motivation

When developing a logical system, the most difficult phase is not verification or automation, but **condensation**:
the stage where exploratory ideas are crystallized into a stable language, a small set of axioms, and a disciplined notion of consequence.

Most proof assistants (e.g. Lean, Coq) are optimized for *large-scale formalization* of already-mature theories.
They intentionally hide structure behind powerful type systems, automation, and inference.
This is highly effective once the system boundary is fixed, but imposes significant cognitive overhead during the condensation phase.

The goal of this design is different:

> **To support the author while a logical system is being shaped, clarified, and stabilized.**

This note documents an architecture that prioritizes *authoring clarity*, *explicit structure*, and *controlled growth*, while remaining compatible with later verification and compilation.

---

## 2. Core Design Principle

The central principle is:

> **Authoring precedes verification.**

In particular:

* The author should work with **formal variables** (φ, ψ, χ),
* **explicit constructors** with known arity,
* **axiom schemas** as written mathematics,
* and **step-by-step derivations** of consequences.

Low-level concerns (tokens, symbol tables, relocation, verification) are strictly downstream.

---

## 3. Layered Model: Language → Axioms → Consequences

The architecture mirrors how mathematicians actually build theories.

### 3.1 Language (Structures)

The first layer declares the **language skeleton**:

* Formal variables
* Primitive constructors (connectives, relations, operations)
* Arity and sort constraints

This layer makes **no logical commitments**.

Example (author-facing):

```python
from skfd.authoring.dsl import Var, symbol
from skfd.authoring.typing import WFF

phi = Var("φ")
psi = Var("ψ")
@symbol("->", 2, (WFF, WFF), WFF, op="rshift", precedence=20, assoc="right", aliases=["→"])
@symbol("→", 2, (WFF, WFF), WFF, op="rshift", precedence=20, assoc="right", aliases=["->"])
def Imp(b, args):
    return b.imp(args[0], args[1])
@symbol("-.", 1, (WFF,), WFF, op="invert", precedence=30, aliases=["¬"])
@symbol("¬", 1, (WFF,), WFF, op="invert", precedence=30, aliases=["-."])
def Not(b, args):
    return b.neg(args[0])

This is recorded as structure, not semantics.

### 3.2 Axioms

Axioms are **constraints on the language**, expressed as schemas.

Crucially:

* Axioms are **templates**, not inference rules.
* They are written using the authoring language.
* They are instantiated explicitly.

Example:

```python
A1 = Imp(phi, Imp(psi, phi))
```

This mirrors textbook mathematics and avoids hidden inference.

### 3.3 Consequences (Definitions, Lemmas, Theorems)

Logical consequences are layered:

* **Definitions**: conservative extensions (macros), expandable
* **Lemmas**: internal derivations
* **Theorems**: externally committed results

This separation allows gradual stabilization without prematurely freezing the theory.

---

## 4. Authoring Contract vs. Implementation Contract

A strict boundary is enforced.

### 4.1 Authoring Contract

The authoring layer:

* never sees tokens
* never sees symbol interners
* never performs verification
* never uses automation

It only builds **Expr trees**.

### 4.2 Compilation Bridge

A controlled bridge lowers authoring expressions into token-level formulas. In code, this is expressed as:

```python
from skfd.authoring.dsl import CompileEnv, compile_wff

w = compile_wff(expr, env=env)   # returns a token-level Wff (SymbolId sequence)
```

At this point, and only here:

* symbols are interned
* builtins are bound
* token sequences are produced

This keeps the authoring experience clean while preserving formal rigor.

Practical authoring ergonomics:

- For quick authoring, use the string parser [parsing.wff](file:///Users/mingli/MetaMath/proof-scaffold/src/skfd/authoring/parsing.py#L142-L145) to build an `Expr`:

```python
from skfd.authoring.parsing import wff

expr = wff("(φ → ψ) → (¬ψ → ¬φ)")
```

- For deterministic downstream output, the lowering step should use the same global `SymbolInterner` as the build context (`ctx.mm.interner`), and (in the BuilderV2 world) the same `NameResolver` policy as `ctx.names` so Unicode stays authoring-only.

---

## 5. Syntactic Layer and Inference Skeleton

The logical system exposes a **syntactic layer**:

* token-level constructors (wi, wn, wa)
* a minimal inference skeleton (mp)
* explicit arity/sort signatures

This layer is intentionally minimal and stable.
It does not grow with the theory.

All higher reasoning happens in lemmas and theorems.

---

## 5.1 Integration with BuilderV2 (Build-Time Emission)

Authoring produces token-level `Wff` values (a sequence of `SymbolId`). BuilderV2 consumes `SymbolId` directly, so emission is a thin, explicit bridge:

```python
from skfd.api_v2 import BuildContextV2
from skfd.authoring.emit import emit_axioms, emit_lemmas
from logic.propositional.hilbert import System
from logic.propositional.hilbert.lemmas import Proof

def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    prelude = ctx.deps.prelude

    wff_tc = prelude["wff"]
    sys = System.make(interner=mm.interner, names=ctx.names)

    emit_axioms(mm, sys, typecode=wff_tc)
    proofs: list[Proof] = []
    emit_lemmas(mm, sys, proofs, typecode=wff_tc)

    mm.export(wff_tc)
```

Key properties that keep authoring “clean” and toolchain behavior deterministic:

- Authoring and emission never use string token DSL for proof payloads; they pass `SymbolId` sequences end-to-end.
- `$f` boilerplate is handled by [MMBuilderV2.auto](file:///Users/mingli/MetaMath/proof-scaffold/src/skfd/builder_v2/builder.py#L112-L170) by default (`auto_f=True`), not by proof authors.

---

## 6. Comparison with Lean-style Authoring

Lean and similar systems optimize for *automation and compression*:

* complexity is paid by the system
* inference is implicit
* errors arise from failed unification or type inference

This architecture optimizes for *clarity and control*:

* complexity is paid by the author
* inference steps are explicit
* errors occur at precise, local points

These approaches are complementary, not competing.

This system is designed as a **front-end for theory condensation**, not as a replacement for proof assistants.

---

## 7. Resulting Directory Structure (Hilbert Example)

```
hilbert/
  _structures.py     # language skeleton
  _syntactic.py      # token-level syntax + mp
  axioms.py          # axiom schemas
  definitions.py     # conservative extensions
  lemmas.py          # derived consequences
  theorems.py        # committed results
```

Each file has a single, non-overlapping responsibility.

---

## 8. Benefits

* Authoring feels like writing mathematics, not driving a framework
* System boundaries are explicit and enforceable
* Language growth is controlled and reversible
* Verification and compilation remain downstream concerns
* The architecture scales naturally to new logics

---

## 9. Conclusion

This design treats logical systems not as monolithic artifacts, but as **objects that evolve through authoring**.

By respecting the condensation phase, we gain:

* clearer theories
* more stable foundations
* and a path from human reasoning to machine verification that remains intelligible.

---

## 10. Authoring Experience (Hilbert Lemmas)

Early experiments with a Hilbert-style propositional system provide some concrete feedback on this architecture.

- Hilbert as “assembly language”  
  - Writing the identity law lemma `L1_id : φ → φ` directly against A1/A2 and `mp` confirmed that the authoring contract works as intended:  
    - authoring stays in terms of `Var`, `Imp`, etc.,  
    - compilation is a single `compile(...)` call,  
    - and verification remains downstream in Metamath.  
  - The proof is mechanically close to textbook Hilbert derivations, which makes the correspondence between mathematics and code easy to see.

- Classic propositional lemmas expose friction  
  - For more substantial lemmas (De Morgan, contrapositive, double negation, excluded middle, Peirce), proofs become noticeably verbose when written purely in terms of A1/A2/A3 + `mp`.  
  - Many steps are instantiations of the same higher-level pattern (for example, combining `A → (B → C)` and `A → B` to obtain `A → C` via A2), but today these patterns are expanded by hand.  
  - Managing intermediate labels and `Hypothesis` objects is precise but laborious; small edits can require rechecking multiple downstream references.

- Toolchain vs. authoring effort  
  - Once a lemma is correctly expressed in the authoring layer, lowering to Metamath via `Proof` and `emit_lemmas` is smooth.  
  - Recent fixes around stack underflow and token mapping show that most remaining friction is in proof authoring, not in emission or verification.  
  - This is a good sign: the backend is stable enough that iteration cost is dominated by how we write proofs, not by how we compile them.

- Design implications for the authoring layer  
  - These experiments reinforce the idea that **Hilbert should be treated as a backend target**, not as the primary authoring language.  
  - A more ergonomic, assumption-aware proof DSL on top of the current authoring layer would let authors write natural-deduction style arguments, which could then be compiled down to Hilbert proofs using the Deduction Theorem as a specification.  
  - In this view, the existing authoring constructs (`Expr`, `CompileEnv`, `Proof`) are the right place to attach such a compiler, keeping the Hilbert layer thin and mechanical while preserving a mathematically natural authoring experience.
