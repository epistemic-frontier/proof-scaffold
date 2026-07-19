# Language as a First-Class Element

> Status: Normative design commentary, proposal draft.
>
> Scope: Responsibility boundaries among language, logic, theory, the Prelude, and proof infrastructure in the ProofScaffold standard package stack.
>
> The terms “MUST,” “MUST NOT,” “SHOULD,” “SHOULD NOT,”
> and “MAY” in this document have normative meaning.

---

## 0. Core Adjudication

A formal mathematical system MUST be understood as the following ordered composition of layers, rather than as a proof catalog containing only axioms and theorems:

```text
Language
  determines which expressions are meaningful

Judgment / Calculus
  determines which judgments can be made about expressions and how judgments primitively derive judgments

Logic
  combines a language, a calculus, and logical axioms

Concrete Mathematical Theory
  extends or reuses the underlying language and adds domain-specific non-logical symbols and axioms

Proofs and Theorems
  record and name conclusions obtained under the established language and inference relation
```

Therefore, language MUST be a first-class, nameable, composable, and checkable interface element. A theory that publishes `AXIOMS`, `RULES`, and `THEOREMS` without also publishing the language contract on which these objects depend has a semantically incomplete interface.

The standard public mental model SHOULD be:

```text
LANGUAGE   determines what can be said
CALCULUS   determines which judgments can be made and how new judgments are derived
AXIOMS     determines which judgments are accepted directly by the logic
THEORY     adds domain language, definitions, and non-logical axioms
THEOREMS   records conclusions that have been derived and named
```

`|-`, modus ponens, and generalization do not belong to the object-expression language. The first is a Metamath realization of a Judgment; the latter two are Primitive inference rules of a Calculus. Making language a first-class element MUST NOT be misunderstood to mean that the language object subsumes the entire logical system.

---

## 1. Normative Definition of “Language”

A Formal language is a finite and checkable contract for constructing abstract expressions. A `LanguageSpec` MUST describe at least:

1. **Sort**: for example, `wff`, object variable, class, or term;
2. **Variable kinds**: the Sort to which each kind of variable belongs and whether it can be bound by a Binder;
3. **Constructors and symbols**: each Constructor's stable identifier, input Sorts, output Sort, and arity;
4. **Abstract syntax**: the Constructors from which valid expressions are recursively generated;
5. **Binding behavior**: which argument positions introduce Binders and which arguments fall within each Binder's scope;
6. **Structural information required for free variables and substitution**: sufficient to derive capture avoidance and alpha-renaming structurally.

`LanguageSpec` MUST NOT contain Unicode/ASCII spelling, parser callbacks, Metamath token layout, `SymbolId`, or Formation assertion labels. These belong respectively to `NotationSpec` and a Backend binding.

A language declares variable **kinds**; it does not enumerate all actual variable names. Actual variable identifiers belong to their declaration contexts:

```text
DeclaredVariableId(owner=language_or_theory_id, local_key=...)
SchemaVariableId(owner=assertion_id, local_key=...)
LocalVariableId(owner=proof_id, local_key=...)
```

Preferred names such as `φ/ψ/χ` belong to Notation/style; the fixed `ph/ps/ch` token pool in the Prelude belongs to the Metamath foundation binding. Neither may enter the structural content identity of an abstract Term.

The language contract MUST distinguish the following three objects:

- A `Term` or `Expr` is an Abstract syntax tree and the semantic object manipulated by authors;
- ASCII, Unicode, LaTeX, and strings are input or display views of the same semantic object;
- A `Wff`/token sequence is a backend representation for Metamath.

Display Notation MUST NOT participate in mathematical content identity. `->`, `→`, and `⇒` MAY parse to the same Constructor, but the Constructor's stable identifier, arguments, and result Sort MUST participate in the Term's structural equality.

### 1.1 Four Contracts That MUST NOT Be Mixed

```text
LanguageSpec
  sorts + variable kinds + constructors + binders

NotationSpec
  parse/render + aliases + precedence + associativity

MetamathLanguageBinding
  typecodes + owned tokens + token templates + formation assertions

CalculusSpec
  judgment kinds + primitive inference rules
```

The same `LanguageSpec` MAY have multiple Notations and Backend bindings. Changing Unicode display MUST NOT change the Term or language semantic digest; changing Metamath token layout MAY change the backend digest without changing the abstract language; changing a Constructor's Sort signature, however, MUST change the language semantic digest and invalidate dependent interfaces.

Core declarations MUST use finite, algebraic data structures. Arbitrary Python callbacks MUST NOT enter an interface level claimed to be serializable, digestible, and reproducible across processes.

A language determines only whether expressions are well formed, not whether they are true or provable. For example, if `Imp` has signature `Wff × Wff → Wff`, then `Imp(φ, ψ)` is a valid formula; this fact is neither a logical axiom nor a proof of it.

---

## 2. Formation Rules Are Not Inference Rules

Metamath uses `$a` to encode both Formation assertions and logical axioms, so backend statement kinds cannot directly serve as author-level mathematical classifications. An implementation MUST distinguish:

### 2.1 Language Formation Rules

```text
φ : wff, ψ : wff
-----------------  wi
(φ → ψ) : wff
```

This specifies how the Metamath backend proves that a token sequence resulting from conversion to a backend representation is well formed. It belongs to `MetamathLanguageBinding`, not to the abstract `LanguageSpec`.

### 2.2 Logical Axioms

```text
⊢ (φ → (ψ → φ))    ax-1
```

This directly grants a provability Judgment in the established language and belongs to `AXIOMS`.

### 2.3 Inference Rules

```text
⊢ φ    ⊢ (φ → ψ)
----------------  ax-mp
       ⊢ ψ
```

This consumes proved Judgments and produces a new proved Judgment and belongs to `RULES`.

Therefore, a Formation assertion MAY be emitted as `$a` in `.mm`, but MUST NOT consequently be misclassified as logical `AXIOMS` in the author API. Likewise, `mp` MUST NOT be grouped with formation capabilities such as `wi` and `wn` under an ambiguous concept of “syntactic rules.”

---

## 3. Language, Logic, and Concrete Mathematical Domains

### 3.1 Language Precedes Logic

Axioms and inference rules are written in a language. Without a language, it is impossible to determine:

- which Constructors an axiom uses;
- whether an inference rule's premises and conclusion are well-sorted;
- whether substitution crosses a Binder and captures a variable;
- whether two surface strings represent the same Term;
- whether a theory extension changes the meaning of old expressions.

Therefore, a logical system MUST explicitly reference a language and cannot acquire syntax incidentally through import side effects and a global registry.

### 3.2 Logic Defines “Derivation”

A logical system selects logical axioms and Primitive inference rules over a language. Different Logics MAY:

- share the same language but adopt different axioms;
- share the same language and theorems but adopt different primitive Calculi;
- use different organizations of Judgments and deduction, such as Hilbert systems, natural deduction, or sequent calculi;
- make different commitments concerning classicality, intuitionism, relevance, or modality.

Therefore, `RULES` is not “the one set of rules for all mathematics,” but the current Calculus's primitive deductive interface. If a derived rule has been proved by the underlying system, it remains, in essence, a reusable theorem and SHOULD NOT masquerade as a new trusted primitive.

A minimal Judgment interface MAY contain only `Provable : Wff -> Judgment`. Even if the first version supports only Hilbert-style `⊢ φ`, the public Assertion signature SHOULD express premises and conclusion as Judgments rather than hide the Judgment as a global bare `Wff` assumption.

### 3.3 Mathematical Domains Form Theories over Logic

Theories such as set theory, number theory, and algebra generally:

1. inherit the underlying logical language and inference relation;
2. add domain-specific non-logical Sorts, functions, relations, or Binders;
3. add domain axioms or definitions;
4. prove theorems in the extended Theory.

For example, ordinary first-order logic MAY have variables, predicates, equality, and quantifiers; the membership relation `∈` is a non-logical relation in the language of set theory, not a symbol inherent in the concept of first-order logic. A package compatible with `set.mm` MAY provide both together for historical ordering reasons, but its interface MUST indicate that this is a package-boundary choice, not a mathematical classification.

### 3.4 Language Extension Is Not Logical Strengthening

Adding a new symbol only expands “the sentences that can be said”; it does not automatically add “the sentences that can be proved.” Definitional extension, Conservative extension, adding new axioms, and changing inference rules MUST be distinguishable operations:

- adding Notation or a definition MAY be conservative;
- adding an axiom strengthens the Theory;
- adding a primitive rule changes the trusted basis of the consequence relation;
- proving a derived rule does not expand the set of statements provable in the original Theory.

The Theory interface and interface digest SHOULD preserve these distinctions.

---

## 4. Responsibilities of the Standard Package Stack

The standard stack SHOULD form the following unidirectional dependency:

```text
ProofScaffold language toolkit
              |
              v
metamath-prelude LANGUAGE
              |
              v
logic.prop LANGUAGE + CALCULUS + LOGIC
              |
              v
logic.fol LANGUAGE + CALCULUS + LOGIC
              |
              v
set / number-theory / other domain theories
```

### 4.1 ProofScaffold: Meta-Tools for Constructing Languages

ProofScaffold MUST provide mechanisms independent of specific mathematical content, such as:

- declaration types for Sorts, variables, Constructors, and Binders;
- immutable `Term`s with structural equality, using stable identifiers for variables and Constructors;
- explicit construction and composition of registries;
- parsing/formatting driven by `NotationSpec`;
- conversion of symbols to a backend representation driven by Backend bindings;
- substitution, free-variable analysis, and capture checks;
- `LanguageSpec`, `LanguageInterface`, `CalculusSpec`, and layered stable digests.

ProofScaffold MUST NOT hard-code the mathematical meaning of `→`, `∀`, or `∈`. It is a toolkit for making languages, not itself the standard mathematical language.

### 4.2 metamath-prelude: Minimal Concrete Language Foundation

Within the standard build closure, `metamath-prelude` is the sole Foundation Unit. It SHOULD own the minimal concrete language and ambient Metamath frame shared by subsequent standard packages, including:

- the foundational language Sort `wff`, together with the corresponding backend typecode;
- standard foundation variables and global floating hypotheses;
- minimal shared vocabulary, such as `(`, `)`, `-.`, and `->`;
- corresponding abstract Constructors, such as `Not` and `Imp`;
- corresponding Formation assertions, such as `wn` and `wi`;
- the public `LANGUAGE` contract formed by these objects.

`|-` is emitted by the foundation frame, but in the abstract model it MUST be bound to the Calculus's `Provable` Judgment and MUST NOT be declared as an object-language Constructor or an ordinary Sort.

The Prelude is “foundational” as the foundation of the standard object language and foundation scope, not as a home for general-purpose DSL machinery. General-purpose `Var`, `Sort`, `Constructor`, parser frameworks, and frameworks for conversion to a backend representation belong to ProofScaffold; concrete `Imp` and `Not` belong to the Prelude language; their normative token layout belongs to the Prelude's `MetamathLanguageBinding`.

The Prelude SHOULD NOT own ordinary theorems merely because the current downstream Logic happens to use them, nor SHOULD it absorb all symbols from Logic and Mathematical domains. Changes to its contents are foundation ABI changes and MUST be controlled more strictly than ordinary library extensions.

### 4.3 metamath-logic: Logical Language and Consequence Relation

`logic.prop` SHOULD explicitly extend the Prelude language by adding propositional Constructors; `logic.fol` SHOULD explicitly extend the propositional language by adding first-order variables, quantifiers, equality, substitution, and Binder behavior. Each layer SHOULD publish:

```text
LANGUAGE
CALCULUS
AXIOMS
RULES
THEOREMS
```

Concrete Constructor functions and `prove_*` functions MAY remain convenient public Python APIs for direct reuse; the five aggregate objects are machine-readable Theory metadata and cannot replace those functions.

### 4.4 Domain Packages: Extending Language and Adding Non-Logical Axioms

A domain package MUST explicitly declare its inherited language and Theory configuration and add only domain-specific vocabulary to its own `LANGUAGE`. It MAY reuse the underlying `RULES` without mechanically copying a mapping; if it changes the Calculus, it MUST form a different Logic or Theory configuration.

---

## 5. Language Composition and Identification Invariants

**L1. Explicit declaration.** Every buildable Theory MUST explicitly specify a language; it MUST NOT obtain Constructors solely through module-import side effects.

**L2. Single semantic source of truth.** A Constructor's Sorts, arity, and Binder MUST be declared uniquely by `LanguageSpec`. Notation and Backend bindings MUST reference it through a stable `ConstructorId`; they MUST NOT duplicate its signature or maintain independently drifting registries.

**L3. Monotonic extension.** Ordinary language extensions MUST NOT change the identifiers, Sorts, arities, or Binders of inherited Constructors. Changes to these facts MUST be treated as incompatible semantic ABI changes; changes in backend realization are represented separately by the backend digest.

**L4. Sort precision.** Object variables, classes, and wffs MUST NOT all masquerade as `Wff` merely for the convenience of conversion to a backend representation. If a backend bridge temporarily requires a compatible representation, the author-level interface MUST still preserve the true Sort.

**L5. Complete Binders.** A language containing Binders MUST provide contracts for free variables, substitution, and capture avoidance. Merely declaring the printed shape of a quantifier is insufficient for a complete language definition.

**L6. Representation separation.** Abstract Terms, display strings, and Metamath token sequences MUST be objects at distinct stages.

**L7. Separation of formation and derivation.** Formation assertions belong to `MetamathLanguageBinding`; Judgments and Primitive inference rules belong to `CalculusSpec`; logical axioms belong to `AXIOMS`.

**L8. Layered digests.** `semantic_digest` covers only Sorts, Variable kinds, Constructor signatures, and Binders; `notation_digest` covers Notation; `backend_digest` covers typecodes, token templates, Formation bindings, and foundation requirements; `calculus_digest` covers Judgments and primitive rules.

**L9. The backend remains authoritative.** `LanguageSpec` is the source of truth for abstract Term typing; `NotationSpec` is the source of truth for parsing/display; neither MAY bypass BuilderV2, the linker, or the final Metamath verifier.

**L10. Unique foundation.** The standard build closure continues to obey the constraint of one Foundation Unit; language composition MUST NOT become a channel for implicitly loading a second set of foundation symbols or ambient hypotheses.

---

## 6. A Minimal Interface Shape

This document does not freeze Python spelling, but semantically at least the following is required:

```python
LanguageSpec(
    id=...,
    extends=(...,),
    sorts=(...),
    variable_kinds=(...),
    constructors=(...),
    binders=(...),
)

NotationSpec(language=..., entries=(...))
MetamathLanguageBinding(language=..., typecodes=(...), formations=(...))
CalculusSpec(language=..., judgments=(...), rules=(...))

LogicSpec(language=..., calculus=..., axioms=(...))
TheorySpec(
    base_logic=...,
    language_extension=...,
    definitions=...,
    axioms=...,
    theorems=...,
)
```

Read-only legacy views MAY be used for migration inventory, but while old global registries, last-wins behavior, and import order still determine semantics, such a view MUST NOT be claimed as a stable `LANGUAGE`. The final migration direction MUST be reversed so that declarations generate a compatibility registry, rather than registries continuing to generate a second copy of the language.

---

## 7. Review Questions

Every design for a language, Logic, or domain package SHOULD answer:

1. Which language does it inherit?
2. Which Sorts, variables, Constructors, or Binders does it add?
3. Is the addition merely Notation, a definitional extension, or does it introduce new axioms?
4. Which set of Primitive inference rules does it adopt?
5. Which rules are only proved derived rules?
6. How does it compute free variables and perform capture-avoiding substitution?
7. How is an author-level Term deterministically converted to an `.mm` backend representation?
8. Which downstream interface digests are invalidated when the language ABI changes?

If a package cannot answer these questions, it does not yet form a complete Theory interface.

---

## 8. Conclusion

Language is neither an implementation prelude before axioms nor ancillary parser configuration. It is the semantic space jointly referenced by axioms, rules, proofs, and theorems. Once language is promoted to a first-class element, the Prelude can be understood accurately as the standard-language foundation, Logic as a consequence relation over a language, and domains such as set theory and number theory as vocabulary and axiom extensions over Logic.

This distinction reduces both the burden of mathematical understanding and the cost of engineering maintenance: authors see language, assumptions, and deduction; the backend remains responsible for symbol identification, conversion to a backend representation, linking, and verification, but no longer determines the classification of the author API in reverse.
