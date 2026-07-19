# Project 024: Elevating Language to a First-Class Theory Interface

## Status

In progress, 2026-07-16.

Normative basis:
[Reference 011: Language as a First-Class Element](../references/011-language-as-first-class.en.md).

Related existing designs:

- [Reference 005: Authoring-First Architecture](../references/005-authoring.md)
- [Reference 010: Foundation Scope](../references/010-foundation-scope.md)
- [Project 008: Prelude Framework Refactor](./008-prelude_refactor.md)
- [Project 020: Foundation Scope Refactor](./020-foundation-scope-refactor.md)
- [Project 021: Authoring IR](./021-authoring-ir-for-human-and-llm-authors.md)
- [Project 022: Authoring API v0.1](./022-authoring-api-v0.1.md)

This document is an engineering diagnosis and incremental improvement plan for the current
`proof-scaffold`, `metamath-prelude`, and `metamath-logic` implementations. It does not freeze the
final Python API.

## 0.1 Revised Implementation Contract

The initial draft correctly identified the missing language abstraction, but compressed semantic
language, notation, Metamath backend conversion, and syntax assertion binding into an overly broad
`LanguageSpec`. This section supersedes the conflicting groupings and implementation order in
Sections 4, 5, and 9.

The target skeleton is:

```text
LanguageSpec
  sorts + variable kinds + constructors + binders
        |
        +---- NotationSpec
        |       parse + render + aliases + precedence
        |
        +---- MetamathLanguageBinding
                typecodes + token templates + syntax assertions

CalculusSpec
  judgment kinds + primitive inference rules

LogicSpec
  language + calculus + logical axioms

TheorySpec
  base logic + language extension + definitions + non-logical axioms + theorems
```

Here, `Term` contains only stable variable/constructor identifiers, an argument tree, and a sort.
Unicode spelling, source spans, `SymbolId`, Python object identity, and provenance do not
participate in its equality. `|-` is the Metamath realization of the `Provable(Wff)` judgment;
`wi/wn/wa/w3a` belong to the language binding; `ax-mp/ax-gen` belong to the calculus; and
`ax-1/ax-2/ax-3` belong to the logical axioms.

### Source, Interface, and Runtime

The three stages must not be collapsed:

```text
LanguageSpec
  finite declaration source edited by library authors

LanguageInterface
  immutable, digestible consumer interface after conflict checking and inheritance expansion

BoundLanguage / LanguageEnvironment
  runtime object binding notation, backend, SymbolId, resolver, and build context
```

`System` is a runtime binding. It cannot represent the theory itself or determine the theory's
semantic identity. The first phase may allow new declarations and legacy global registries to
coexist, but the new declarations must not be generated from the global registries. The next phase
must derive the legacy compatibility adapter from declarations, and import side effects must
ultimately be removed.

### Layered Digests

```text
semantic_digest = sorts + variable kinds + constructors + binder behavior
notation_digest = patterns + aliases + canonical rendering
backend_digest  = typecodes + owned tokens + templates + formation assertions
calculus_digest = judgments + primitive rule signatures
```

All digests use explicitly versioned canonical JSON. They must not use `repr`, Python hashes,
mapping iteration, callbacks, or `SymbolId`.

### Revised Phase Order

**Phase 0.5 — Strengthen Term identifiers and identity.** Create nominal identifiers `SortId`,
`ConstructorId`, and `VariableRef`, together with a structurally equal immutable `Term`. Retain the
old `Expr` only in a compatibility role, not as a public ABI.

**Phase 1 — Minimal language canary.** Implement independent `LanguageSpec`, `NotationSpec`, and
`MetamathLanguageBinding` objects with layered digests; Prelude declares `Not/Imp`; prop extends it
with `And2/And3`. Binary and ternary conjunction have different `ConstructorId` values and formation
assertions but may share a backend token. In the first round, `And3` uses unambiguous call notation
rather than reproducing the old parser's arity collapse.

**Phase 2 — Declarations become the source of truth.** Derive legacy registries/builders/parser
tables from the new declarations; do not maintain a second `LANGUAGE` generated from the old global
registry indefinitely.

**Phase 3 — Judgment / Calculus.** Implement `Provable(Wff)` first, then design schema-aware MP and
generalization. Do not prematurely freeze the primitive rule API with arbitrary callbacks before
substitution and constraints are stable.

**Phase 4 — Binder / DV canary.** Use `All`, `ax-gen`, and one mandatory-DV assertion to validate
real sorts, free variables, capture, alpha-renaming, DV substitution, and relocation.

**Phase 5 — Proof API and combinators.** Only then freeze `AssertionSignature`, `ProofDraft`,
`ApplyAssertion`, and `ElaboratedProof`. Project 023 families/combinators must expand into ordinary
concrete assertion applications.

### Completion Boundary of the Current First Slice

This round implements:

- parallel Term v2 and stable nominal identifiers in ProofScaffold;
- a conflict-checked immutable `LanguageInterface`;
- a finite prefix/infix/call `NotationSpec`;
- a symbolic `MetamathLanguageBinding` with no `SymbolId` values;
- a minimal judgment-only `CalculusSpec`, without prematurely implementing MP/Gen;
- Prelude `Not/Imp` and prop `And2/And3` canaries;
- independent semantic/notation/backend/calculus digests;
- unchanged legacy build, proof constructors, BuilderV2, and verifier behavior.

This round explicitly does not migrate FOL, binders, substitution, DV, primitive rules, or the
existing 2,675 proof constructors. To avoid freezing an incomplete contract that has only print
shape and binder-argument checks but no free-variable or capture-avoidance semantics, the Phase 1
`ConstructorDecl` does not yet expose binding fields. Those fields must enter the interface in
Phase 4 together with complete free-variable, substitution, capture-rejection, and alpha-renaming
behavior.

Phase 2A completed the first source-of-truth inversion for Prelude `Not/Imp`: legacy token interning,
token-level constructors, shape matchers, authoring-layer symbol specs, formation rule signatures,
and `wn/wi` emission are all derived from resolved language/notation/backend declarations; the
compatibility layer still preserves the old Python API. The SHA-256 of
`metamath-prelude_full.mm` is exactly identical before and after this migration.

Phase 2B advanced the same mechanism to prop `And2/And3`: the legacy builder registry uses the full
`Constructor(name, arity)` as its exact key, allowing binary and ternary constructors with the same
name to coexist, while string lookup remains only as a compatibility fallback. The authoring-layer
parser also uses the public name/arity lookup and no longer reads or writes the registry's private
mapping. On the Logic side, the conjunction/disjunction `_by_name` pop/restore mechanism and
argument-count dispatch have been removed; the authoring-layer specs, token templates, formation
labels, legacy backend conversion, and `wa/w3a` emission for `And2/And3` are now derived from prop
language/notation/backend declarations. Before and after the migration, the SHA-256 of
`metamath-logic_full.mm` is
`0e857f13fe8c82d406f3b730f8dcc2aade8a94a031f38152a295f0be00ba75b8`, and all three verifiers
pass. This remains a compatibility migration: the global registry and legacy `Expr` have not yet
been removed, and the full Phase 2 is not complete.

Phase 2C further removed prop's duplicate authoring-layer declarations of Prelude `Imp/Not`: the
old import paths are now compatibility re-exports of the Prelude constructors. Prelude token
backend conversion now accepts downstream builtins through a read-only structural protocol, so
prop and FOL can reuse the same constructor builder without inheriting a concrete runtime class.
The Logic build output retains the SHA-256 above.

Phase 3A extended `CalculusSpec` from a judgment vocabulary into a finite, immutable, digestible set
of `PrimitiveRuleDecl` values. Each primitive rule explicitly declares schema variables, judgment
premises, and a conclusion; the resolver validates variable kinds, constructor trees, sorts, and
judgment kinds, and normalizes schema-variable order when it has no positional semantics. Prop's
modus ponens is now formally represented as
`Provable(φ), Provable(Imp(φ, ψ)) -> Provable(ψ)`, while the public `RULES["ax-mp"]` is only a
compatibility view from the set.mm label to that semantic declaration and no longer presents the
string `"mp"` as rule metadata. `ax-gen` is intentionally deferred to Phase 4: no incomplete
generalization declaration will be created before the setvar sort, `All` binder, substitution, and
DV contracts enter the semantic language. This phase does not change proof execution or emission,
and the SHA-256 of the Logic build output remains unchanged.

Phase 4A added a digestible `BinderDecl` and derives free-variable analysis, alpha-renaming, and
capture-avoiding substitution uniformly from the binder contract. Nested shadowing masks only the
inner binder's scoped arguments; arguments not bound by the inner binder remain subject to the outer
scope. Binder notation supports precedence-aware parsing/rendering, and language extensions are
forbidden from adding or changing binder semantics for inherited constructors. The FOL semantic
language now explicitly extends prop and declares an independent `SETVAR` sort,
`All : SETVAR × WFF -> WFF`, and its binder contract; `wal` exists only in the Metamath formation
binding, while `ax-gen` is represented as the primitive inference rule
`Provable(φ) -> Provable(All(x, φ))`.

Phase 4B completed the mandatory-DV canary with `ax-5`. Both endpoints of `DistinctPair` directly
reference the assertion's typed `VariableRef` values; the resolver verifies that endpoints belong
to the same schema-variable set, normalizes each pair independent of direction, and includes the
constraint in the assertion digest. Thus `ax-5` expresses the WFF schema variable `φ`, the SETVAR
schema variable `x`, and the mandatory pair `(φ, x)` together; the constraint is not incorrectly
attached to `ax-gen`. The current legacy `ACTIVE_DV_PAIRS` remains the authoritative emission input,
while semantic `ax-5` is a migration canary that does not independently rewrite the corpus or public
`prove_*` APIs. The next step should connect this typed assertion contract to Phase 5's unified
`AssertionSignature/apply_assertion` and then gradually eliminate the label-keyed side table rather
than maintaining two sources of truth indefinitely.

Phase 5A established the minimal semantic assertion-application kernel. `AssertionSignature`
uniformly carries the stable assertion identifier, kind, ordered schema variables, ordered judgment
premises, conclusion, and mandatory DV for axioms and primitive rules. The binding from primitive
`RuleId` to backend assertion identifier must be explicit; no implicit type conversion is performed.
Immutable `ProofDraft` stores hypotheses and fully reified steps using occurrence-based `StepId`
values, checks contiguous IDs, uniqueness, and the absence of forward or foreign premises at
construction, and normalizes the complete active-DV environment. `apply_assertion` accepts only one
specific signature and ordered prior steps. It performs local structural unification, treats partial
substitution/target values as constraints, requires every mandatory variable to be determined
uniquely, and computes the result through an independent one-pass schema instantiation. It neither
invokes capture-avoiding object substitution nor trusts a caller-provided result. Consistent with
Metamath, DV checking uses the Cartesian product of all syntactically occurring variables in the two
endpoint substitutions, including occurrences under binders, and requires the consumer's active-DV
relation to cover every pair. Failure raises a structured `AssertionApplicationError`, leaving the
original draft unchanged.

This slice used real `ax-mp` and `ax-5` metadata to verify ordered-premise inference,
binder-variable instantiation, missing/overlapping DV rejection, and reified substitution/evidence.
It does not yet claim to complete the full Phase 5: theory/assertion-profile lookup, goals/holes,
finalization, replay context, semantic digest, legacy backend conversion, and family/combinator
expansion remain explicitly deferred to later slices.

Phase 5A.5 inserted scoped Source IR between the kernel and finalization without rewriting the `$d`
system. A `SourceBlock` statement may be a `DistinctStatement`, an `AssertionSource`, or a nested
block; one distinct group expands exactly into the undirected pairs within that group, without
transitive closure. The pure elaborator copies active DV from the parent relation, accumulates `$d`
in source order, snapshots the complete relation at each assertion declaration, and restricts the
relation to the assertion's schema variables to form the public mandatory DV. A nested block inherits
its parent but does not leak back into the parent when it exits. The `with` simplified interface of
`SourceBuilder.block()` constructs only immutable Source IR; it does not invoke BuilderV2, the
linker, or emission, and it does not modify global registries. Equivalent pair groupings have
different `source_digest` values and the same `semantic_digest`; both digests include the full
assertion content rather than depending only on nominal identifiers. The FOL `ax-5` canary now enters
a block first as a source assertion without DV, and elaboration of `d(φ, x)` recovers mandatory
contracts exactly equal to `AX5_SIGNATURE`. Legacy `_dv_contracts.py` remains the authoritative input
for the current emission path.

Phase 5B connected scoped assertion snapshots to fixed theorem drafts and finalization. A draft
started from a snapshot fixes the theorem signature, ordered hypotheses, and complete active DV;
construction requires the public mandatory DV to equal exactly the restriction of the active
relation to schema variables. Finalization accepts only theorems, forbids self-reference, requires
the root to equal the declared conclusion exactly, and rejects every dead step not backward-reachable
from the root. `AssertionReplayContext` preserves the full normalized active DV unchanged rather
than retaining only public mandatory pairs. The dependency closure of `ElaboratedProof` is sorted by
stable assertion ID as a set; its semantic digest is a read-only derived value containing the
calculus digest, complete signature, position-based proof DAG, substitution, constraint evidence,
and replay relation, while excluding display labels, nominal `ProofId`, and concrete `StepId`
spelling. Thus changing source display labels or proof-local occurrence namespaces for the same
proof does not change the mathematical digest, while changing the calculus contract necessarily
does. Theory/assertion-profile lookup, assumption closure, legacy backend conversion, and a public
snapshot codec remain deferred to later slices.

Phase 5C established the minimal assertion-catalog boundary required by a fixed theory/assertion
profile. The catalog references assertions by stable `AssertionSemanticId`; full signatures
participate in its deterministic digest, while canonical labels serve only as a compatibility view.
Duplicate IDs, duplicate labels, and dangling references in an assertion profile all reject on
error, and resolution results use immutable mappings. `apply_assertion_by_id` may resolve a signature
from the catalog only when authorized by an explicit assertion profile, after which it reuses the
Phase 5A kernel. Backend-neutral `SemanticReplayPlan` does not introduce a second set of proof
semantics: step by step, it reruns `apply_assertion` using the catalog signature, proof substitution,
premise occurrence, and target; only afterward does it attach the catalog compatibility label,
position-based premises, and dependency closure classified by assertion kind. The prop `mp2b` canary
completed a semantic proof, finalization, and replay-plan generation using two applications of
`ax-mp` resolved by ID, and its structure matches the two steps of the legacy proof. The current
slice does not convert replay plans into legacy `Proof` values and does not change BuilderV2/corpus
emission; full theory ontology, cross-catalog dependencies, and family/combinator migration remain
for later slices.

Phase 5D added a narrow legacy bridge from `SemanticReplayPlan` to the existing `Proof`/`Step` types.
Terms form token sequences only through `ResolvedMetamathLanguageBinding`; runtime code must
explicitly provide mappings from `TokenRef -> Const SymbolId`, `VariableRef -> Var SymbolId`, and
semantic sort -> legacy sort. Variable mappings must exist, have the correct kind, and be injective,
preventing backend conversion from silently specializing formulas. Assertion backend bindings also
explicitly distinguish semantic assertion IDs, set.mm labels, and legacy operations: `ax-mp` maps to
legacy `apply(mp)`, ordinary assertions map to `ref(label)`, and catalog display/compatibility labels
no longer determine backend conversion. The bridge accepts only canonical replay plans with no
forward or dead steps and with the root at the final occurrence; hypothesis-root proofs that the
current legacy emitter cannot faithfully represent reject on error. The hypotheses, local labels,
two MP applications, result Wff, and every other field in the `mp2b` canary are exactly equal to the
value returned by the existing `prove_mp2b()`.

Phase 5D.5 further validated the DV bridge with `ax-5`. In addition to the public mandatory pair, the
canary's replay context contains a proof-only active pair; backend conversion maps and normalizes
`SymbolId` pairs from the complete `AssertionReplayContext.active_distinct`, and both pairs enter
legacy `Proof.active_dv_pairs`. Thus the proof implementation does not incorrectly degrade into
reading only assertion mandatory DV. The existing emitter's `$d` path for
`Proof.active_dv_pairs` is unchanged; formal corpus emission and public `prove_*` APIs have not yet
switched to the semantic source.

Phase 5E added a minimal `ProofAuthor` simplified interface over the immutable kernel. It stores only
the current `ProofDraft`; `use()` still enters the profile-constrained catalog by stable assertion ID
and invokes the same `apply_assertion` kernel, while `qed()` still invokes the same finalizer. This
simplified interface accepts no steps created by another author and introduces no implicit
substitution, result formula, or second proof state. `mp2b` now has an independent semantic signature
and the following author code:

```python
h_phi, h_phi_psi, h_psi_chi = proof.hypotheses
psi = proof.use(MP_ASSERTION, h_phi, h_phi_psi)
chi = proof.use(MP_ASSERTION, psi, h_psi_chi)
return proof.qed(chi)
```

This proof forms an immutable `ElaboratedProof` at import time; only at runtime are `ph/ps/ch` and
set.mm tokens bound and converted to the existing `Proof` ABI. Prop's public theorem registry now
uses the semantic constructor for `mp2b`, so the formal corpus build has traversed the new path; it
is field-for-field equal to the transpiler-generated `logic.prop.core.prove_mp2b`, which remains
directly importable. The generated `core.py` was intentionally not hand-edited: regeneration will
not lose the semantic implementation or registry override. Switching the direct `prove_mp2b` name
in the topic module itself requires first defining a stable generated-proof override protocol for
the transpiler rather than adding a one-off generator special case.

---

## 1. Problem Statement

The current public logic API has formed a relatively clear structure around three classes of
metadata:

```text
AXIOMS
RULES
THEOREMS
```

But it does not expose the `LANGUAGE` on which these objects jointly depend as a first-class public
element. Language facts remain scattered across:

- builtin token identifiers, token constructors, and shape parsing in
  `metamath-prelude/src/prelude/formula.py`;
- authoring variables, `Imp`, and `Not` in `metamath-prelude/src/prelude/structures.py`;
- syntax assertion wrappers in `metamath-prelude/src/prelude/hilbert_rules.py`;
- actual constants, variables, `$f`, `wn`, and `wi` emission in
  `metamath-prelude/src/prelude/build.py`;
- vocabulary, backend conversion, and shape matching in
  `metamath-logic/src/logic/prop/_builtins.py` and `fol/_builtins.py`;
- constructors, aliases, precedence, and global DSL registry mutation in `prop/_structures.py` and
  `fol/_structures.py`;
- assembly of builtins, authoring environment, rules, and resolver in `_system.py`;
- the `Expr -> Wff` compilation and rule-application bridge in `_internal.py`.

The result is not merely inconsistent naming; one dimension is missing from the theory interface.
The system can enumerate axioms, inference rules, and theorems, but it cannot answer in the same way,
"What language are these objects written in?"

---

## 2. Concrete Symptoms of the Current Confusion

### 2.1 Prelude and the Propositional Language Declare the Same Things Twice

Prelude already declares `phi`, `psi`, `Imp`, and `Not`, but `logic.prop._structures` declares the
same variables and constructors again; `logic.prop._builtins` also provides another backend
conversion for the `imp` and `wn` tokens.

This makes the actual relation look like duplication:

```text
prelude language     prop language
      Imp       ≈       Imp
      Not       ≈       Not
```

The correct relation should instead be explicit extension:

```text
PROP_LANGUAGE = PRELUDE_LANGUAGE.extend(And, Or, Iff, ...)
```

Without stable constructor identifiers and a language-composition contract, the two declarations
can drift independently in arity, aliases, precedence, token namespace, or backend conversion.

### 2.2 `_syntactic.py` Mixes Formation Rules with Inference Rules

`logic.prop._syntactic` places `Wi`, `Wn`, `Wa`, and `Mp` in the same registry:

- `Wi/Wn/Wa` check input sorts and form new formulas, so they are language-formation capabilities;
- `Mp` consumes two proved hypotheses and produces a conclusion, so it is a primitive inference
  rule of the logic.

The Metamath backend can represent both as assertion applications, but the authoring API must
distinguish "form a formula" from "obtain a proof." The current module name and registry conceal
these two responsibilities.

### 2.3 `_builtins.py` Is a Vocabulary, Compiler, and Parser at Once

The current `_builtins.py` has at least four responsibilities:

1. intern canonical token identifiers;
2. directly assemble `Wff` token sequences;
3. parse implication, negation, and other token shapes;
4. provide backend-conversion implementations for authoring constructors in `_structures.py`.

All of these belong to the language subsystem, but they are not the same kind of data. Because
there is no explicit `LanguageSpec`, constructor signatures, display notation, token layouts, and
shape matching can remain consistent only by convention.

### 2.4 Constructor Registration Depends on Global Mutable State

`logic.prop._structures` uses `DEFAULT_REQUIRE` and `DEFAULT_BUILDERS` and temporarily mutates the
registry's private mapping for binary/ternary conjunction and disjunction. This implementation can
support the current corpus, but it cannot clearly answer:

- exactly which language a given `System` uses;
- whether two language configurations can exist in isolation within the same process;
- whether import order changes the constructor registry;
- whether multiple arities sharing one token form one constructor family or multiple stable
  constructors.

Once language becomes an explicit object, the registry should be built from language declarations
and held explicitly by `System`; module import must not be a semantic operation.

### 2.5 The First-Order Language Has an Incomplete Sort and Binder Contract

`logic.fol._structures` currently uses the `WFF` sort for formula variables, quantified variables,
class-related constructions, and relation arguments. For example, the current signature of `All`
appears as `(WFF, WFF) -> WFF`. This is convenient for compatibility with existing backend
conversion, but it conceals mathematical distinctions:

- what kind of variable a quantifier binds;
- whether arguments to `Eq` and `Elem` are setvar, class, or term values;
- the sorts of the source, target, and formula arguments of substitution;
- how free-variable and capture-avoidance behavior follows from constructor declarations.

Declaring only the print shape of `All` is not enough to define a first-order language. Binders,
scope, free variables, and substitution must enter the language contract and align with DV
obligations.

### 2.6 Historical Layout Obscures the Boundary Between `fol` and Set-Theory Language

The current `logic.fol` provides constructions such as `Elem/∈` and `Cv` that are closely tied to
the prefix layout of `set.mm`. This may be a practical choice for compatible builds, but `∈` is not
an intrinsic symbol of first-order logic in general. Without `LANGUAGE` and its extension relation,
users cannot distinguish:

- pure first-order-logic vocabulary;
- language configurations with equality;
- vocabulary that is already set-theoretic;
- vocabulary needed only for `set.mm` emission order.

### 2.7 Public `RULES` Exposes the Classification Problem Caused by the Missing Language

Both `logic.prop.RULES` and `logic.fol.RULES` are `Mapping[str, str]` values containing only
`{"ax-mp": "mp"}`. This shape cannot express premises, conclusions, sorts, binder/DV side
conditions, or the calculus to which a rule belongs; meanwhile, FOL's primitive generalization
`ax-gen` is absent from the public registry.

This project should not expand a language refactor into a complete rewrite of the `Rule` API, but
after establishing a binder-aware language it must review `RULES`: formation rules should move into
the `LANGUAGE` contract, while primitive inference rules such as `mp` and `gen` should receive
metadata sufficient to express their judgment signatures and side conditions.

### 2.8 Build Outputs Know the Language, but the Public Interface Does Not

`prelude.build` and `logic._build` can ultimately emit correct `.mm` files, showing that the build
path actually possesses the necessary constants, variables, syntax assertions, and token layouts.
But these facts converge only inside procedural build code, private builtins, and registries. They do
not form a `LanguageInterface` that parsers, formatters, proof authors, agents, and downstream
packages can read together.

That is the substance of the "missing language" problem: the system has syntax, but syntax has not
become a unique, explicit, reusable theory fact.

---

## 3. The Foundational Role of Prelude

### 3.1 Two Kinds of Foundation Must Remain Separate

The current stack has two different senses of foundation:

| Layer | Responsibility | Typical objects |
| --- | --- | --- |
| ProofScaffold | General metatools for constructing arbitrary languages | `Sort`, `Var`, `Constructor`, `Expr`, registry, parser/backend-conversion algorithms |
| metamath-prelude | Minimal concrete language and Foundation Frame shared by standard packages | `wff`, `|-`, `(`, `)`, `-.`, `->`, schema variables, `wn`, `wi` |

Prelude therefore plays a foundational role in language construction, but it should not reabsorb
the general framework already provided by `skfd.authoring`. The direction taken by Project 008—move
general authoring machinery out of Prelude and into ProofScaffold—remains correct. This project adds
the missing requirement that concrete languages must also become first-class objects.

### 3.2 What Prelude Should Expose

Prelude should expose a minimal, immutable, digestible `LANGUAGE` or `LanguageInterface` that
downstream consumers can extend explicitly:

```text
PRELUDE_LANGUAGE
  sorts: wff, provable judgment marker as appropriate
  variables: standard schema-variable families
  constructors: Not, Imp
  token layouts: -., ( _ -> _ )
  syntax assertions: wn, wi
```

Here, `wn` and `wi` are backend proof associations for language formation and should not enter the
logical `AXIOMS`. Prelude remains the only foundation unit in the standard build closure, and its
ambient `$f` and symbol-namespace rules remain governed by Reference 010; `LanguageSpec` cannot
bypass linker exports or foundation scope.

### 3.3 What Prelude Should Not Expose

Prelude should not become:

- a repository for all logical connectives;
- a repository for Hilbert logical axioms and ordinary theorems;
- an implicit source of first-order binders or set-theoretic relations;
- a second implementation of general parsers, unifiers, and proof builders;
- a mechanism that automatically injects a global language registry through Python imports.

Its minimality both reduces downstream ABI risk and permits clear future definitions of distinct
foundation/language configurations, without pretending that every logic naturally shares one
object language.

---

## 4. Historical Goal Summary

> This section preserves the diagnosis from the initial draft; object groupings are governed by the
> revised contract in Section 0.1.

### 4.1 Public Theory Interface

Every logic or domain theory should provide:

```text
LANGUAGE
CALCULUS
AXIOMS
RULES
THEOREMS
```

Where:

- `LANGUAGE` contains only sorts, variable kinds, constructors, and binders;
- `CALCULUS` contains judgment kinds and primitive inference rules;
- `AXIOMS` are primitive provable schemas in the language;
- `RULES` is a simple read-only view of the primitive rules in `CALCULUS`;
- `THEOREMS` are proved, named assertions.

Direct Python APIs such as `prove_*`, `Imp`, and `All` remain. Aggregated metadata serves build,
catalogue, agent query, documentation, and interface-digest uses; it does not replace straightforward
direct imports.

### 4.2 Explicit Language Extension

The target relation is:

```text
PRELUDE_LANGUAGE
    |
    +-- PROP_LANGUAGE
            |
            +-- FOL_LANGUAGE
                    |
                    +-- SET_LANGUAGE
```

"Extension" must preserve stable identifiers and backend-conversion rules for inherited
constructors. A package may publish multiple explicit language configurations, such as pure FOL,
FOL with equality, and a set.mm-compatible logic prefix. Additional vocabulary must not silently
enter every language configuration because of import order.

### 4.3 One Source of Truth for Language

One constructor semantic declaration should uniquely determine:

- the typed authoring constructor;
- the abstract `Term` application;
- binder/free-variable traversal.

Parser aliases, formatting, and precedence belong to `NotationSpec`; token backend conversion and
syntax assertions belong to `MetamathLanguageBinding`. They are associated through stable
`ConstructorId` values and must not copy semantic signatures. Legacy views may be used only for
inventory and must not be named as a stable `LANGUAGE`.

### 4.4 Narrowing the Responsibility of System

The target `System` should compose rather than invent theory facts:

```text
System
  language environment  <- LANGUAGE
  axiom applications    <- AXIOMS
  inference applications<- RULES
  name/token binding     <- build context + backend adapter
```

`System` may hold in-process `SymbolId`, `NameResolver`, and rule implementations, but these runtime
objects should be bound from stable interfaces. `_internal` should provide only a controlled bridge
and no longer be a hidden source of language definitions.

---

## 5. Historical Phase List

> The long-term migration goals in this section remain valid; the actual execution order is
> superseded by Phases 0.5–5 in Section 0.1.

### Phase 0: Establish a Classification Inventory and Compatibility Baseline

Deliverables:

- create a machine-checkable inventory of all current sorts, variables, constructors, syntax
  assertions, logical axioms, and primitive inference rules for Prelude, prop, and fol;
- record the current 2,675 declared proofs, results from all three verifiers, catalogue, and public
  import smoke tests;
- annotate each current construction with its target owner: prelude, prop, fol, an equality language
  configuration, or set-domain.

Acceptance:

- every currently emitted syntax label has one unique classification;
- `wn/wi/wa/...` and `ax-1/ax-mp/ax-gen` are no longer conflated in design records;
- this phase does not change `.mm` output or public imports.

### Phase 1: Complete a Minimal `LanguageSpec` Interface View in ProofScaffold

Deliverables:

- implement the stable IDs, sort signatures, constructor signatures, and `LanguageInterface`
  proposed by Projects 021/022;
- support explicit `extends`/composition and conflict diagnostics;
- generate a read-only language-interface view from existing DSL declarations;
- exclude `SymbolId`, file layout, and import order from the language-interface digest.

Non-goals:

- implement every mixfix/binder/LaTeX feature at once;
- replace BuilderV2, the linker, or the verifier;
- create a second set of proof semantics.

Acceptance:

- two independent language environments can be built in the same process without relying on global
  import order;
- constructor-signature conflicts produce deterministic errors;
- existing `Expr -> Wff` backend conversion continues to work through a compatibility adapter.

### Phase 2: Prelude Becomes the First Language Source of Truth

Deliverables:

- Prelude exposes `LANGUAGE`;
- `Builtins`, `structures`, `hilbert_rules`, and `build` derive from the same declaration or bind
  through stable IDs;
- Prelude's `__init__` exposes the language interface rather than a mutable backend registry;
- `wn` and `wi` are explicitly classified as syntax assertions.

Acceptance:

- Prelude emitted symbols, `$f`, `wn`, and `wi` remain compatible with current output;
- Foundation Scope invariants for one foundation, ambient `$f`, and zero `$d` are preserved;
- downstream consumers can read the Prelude language without importing its private formula internals.

### Phase 3: prop Explicitly Extends Prelude

Deliverables:

- `logic.prop.LANGUAGE` explicitly extends Prelude;
- remove the independent duplicate sources of truth for `Imp/Not` while retaining compatibility
  re-exports;
- separate formation capabilities such as `Wi/Wn/Wa` from `Mp`'s inference registry;
- replace temporary mutation of private registry mappings with an explicit constructor family;
- progressively separate `_builtins` into vocabulary binding, backend conversion, and a shape
  adapter rather than keeping an overly broad module.

Acceptance:

- current authoring-layer calls to `Imp`, `Not`, `And`, and similar constructors continue to work
  through compatibility re-exports and gain formal non-private import paths;
- `logic.prop` exposes `LANGUAGE/AXIOMS/RULES/THEOREMS`;
- the generated corpus, catalogue, mypy, pytest, and all three verifiers pass;
- module import order does not change the language-interface digest.

### Phase 4: fol Gains Real Sorts and a Binder Contract

Deliverables:

- `logic.fol.LANGUAGE` explicitly extends prop;
- establish the sort model for setvar/term/class/wff actually required by the current corpus;
- declare binder, scope, free-variable, and capture behavior for `All`, `Exists`, and substitution;
- make DV contracts and semantic variables use the same variable identifiers and substitution map;
- distinguish pure FOL, equality, and set.mm-compatible vocabulary language configurations.

Acceptance:

- binder-aware tests cover free occurrences, shadowing, capture rejection, and alpha-renaming;
- invalid cross-sort construction is rejected at the authoring boundary rather than by the token
  verifier;
- the existing corpus can be converted to a backend representation through an explicit compatibility
  configuration without requiring every generated proof to change at once.

### Phase 5: Review Primitive `RULES`

Deliverables:

- `RULES` metadata expresses premises, conclusions, judgment sorts, and necessary side conditions;
- prop explicitly includes modus ponens;
- fol explicitly decides and represents `ax-gen`;
- syntax assertions appear only through backend-conversion metadata in `LANGUAGE`;
- derived rules remain provable theorem/APIs rather than expanding the trusted primitive set.

Acceptance:

- `logic.fol.RULES` agrees with actual `.mm` primitive-rule usage;
- the builder can generate correct applications from rule metadata and implementation bindings;
- changes in rule classification do not change mathematical conclusions already verified.

### Phase 6: Migrate Domain Boundaries and Remove Compatibility Layers

Deliverables:

- assign `Elem/∈`, `Cv`, and similar constructions explicitly to set-domain language or an explicit
  compatibility configuration;
- downstream set/number-theory packages declare language extensions and theory configurations;
- after at least one release cycle, remove duplicate declarations, global registry hacks, and
  obsolete aliases;
- generate language catalogue and interface-digest build outputs.

Acceptance:

- a pure FOL consumer does not implicitly receive set-theory vocabulary;
- a set-domain consumer receives the same stable constructor identifiers through explicit extension;
- no second independently mutable declaration of `Imp/Not` or constructor backend conversion remains.

---

## 6. Migration Principles

### 6.1 Generate a View First, Then Converge

The first step should generate a read-only `LANGUAGE` interface view from existing running code,
rather than first rewriting the parser, AST, and builder. This view can expose duplication,
conflicts, and omissions immediately. Once equivalence has been verified, the source of truth can
converge item by item onto the declarative model.

### 6.2 Preserve Proof Behavior Before Adjusting Mathematical Boundaries

Structural refactoring and content migration must be committed separately:

1. introduce language objects while output and verifier behavior remain unchanged;
2. verify;
3. then move domain vocabulary such as `Elem` or correct `RULES`;
4. verify again and record interface changes.

### 6.3 Public Direct APIs Do Not Disappear Because Metadata Exists

`LANGUAGE` is an aggregation and reflection interface; it should not force users to write:

```python
LANGUAGE.constructors["prop.imp"].apply(...)
```

Users should still be able to import and write directly:

```python
from logic.prop.language import Imp
from logic.prop.core import prove_syl
```

The module spelling here is only an example of the target form and is not frozen by this document.
The key requirement is that constructors have formal, non-private entry points rather than requiring
users to import `_structures` or invoke them indirectly through a registry.

Metadata serves building, discovery, checking, and tooling; direct functions keep mathematical
programming simple and understandable.

### 6.4 Generated Partitioning Does Not Replace Language Boundaries

Proof partitioning determines implementation modules and retrieval regions; it does not determine
sorts, constructor identifiers, or theory extensions. Moving a theorem file must not change
`LANGUAGE`; moving a language constructor requires language ABI review.

---

## 7. Risks and Controls

| Risk | Control |
| --- | --- |
| A new `LanguageSpec` becomes another copy of duplicated metadata | Initially generate only a read-only interface view; at each phase remove or derive the old registry, forbidding long-term dual writes |
| Designing an overly broad API too early | Implement only fields required by the prop canary and one binder/DV canary |
| Unintentional Foundation ABI change | Compare emitted Prelude LIR, interface digest, and verification output |
| Correcting sorts rewrites 2,675 proofs at once | Provide an explicit backend-conversion compatibility configuration and migrate authoring-layer terms in batches |
| Global-registry import side effects are difficult to remove | The new API injects a language environment explicitly; old defaults remain only as a deprecated compatibility layer |
| The `RULES` refactor expands project scope | Defer Phase 5 until language and binder data are stable, then implement it separately |
| Historical set.mm order conflicts with mathematical package boundaries | Distinguish semantic ownership from emission compatibility configurations |

---

## 8. Overall Acceptance Criteria

When this project is complete, it must satisfy all of the following:

1. Prelude, prop, fol, and at least one concrete domain package can each expose a digestible
   `LANGUAGE`;
2. every public theory can explicitly identify its language, logical axioms, primitive rules, and
   theorems;
3. Prelude is the standard minimal concrete language foundation and ProofScaffold provides general
   language tools, without duplicated responsibilities;
4. prop reuses Prelude's `Imp/Not` through extension rather than copying their semantic declarations;
5. fol's binder, free-variable, substitution, and DV contracts are machine-checkable;
6. syntax assertions, logical axioms, and inference rules have explicit API classifications;
7. parsers, typed constructors, formatters, and backend conversion no longer maintain independently
   drifting language facts;
8. existing direct `prove_*` and constructor APIs remain usable during migration;
9. BuilderV2, the linker, and the Metamath verifier remain authoritative for backend conversion,
   linking, and final correctness;
10. the current complete corpus continues to pass Proof coverage, `mmverify`, `metamath`, and `knife`
    verification.

---

## 9. First Implementation Slice

The minimal, high-information slice selected for this round is:

1. create a structurally equal Term v2 without changing legacy `Expr` behavior;
2. make `LanguageSpec` contain semantic declarations only;
3. keep `NotationSpec` and `MetamathLanguageBinding` independent, each with its own digest;
4. have `PRELUDE_LANGUAGE` provide `Not/Imp`;
5. have `PROP_LANGUAGE` extend it explicitly and provide `And2/And3`;
6. let `And2/And3` share the `/\\` backend token while retaining different constructor identifiers,
   arities, and formation assertions;
7. establish a judgment-only `CalculusSpec` and `Provable(Wff)` canary;
8. keep every existing build and proof API unchanged;
9. verify digest determinism, notation round trips, exact-symbol backend conversion, and absence of
   verifier regressions.

This slice tests the most important architectural judgment—whether language can truly become a
stable interface between packages—without first solving every FOL binder, rule-metadata, and domain
migration issue.
