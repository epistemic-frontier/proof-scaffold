# Project 021: Authoring IR for Human and LLM Authors

## Status

Draft

This document records the proposed direction. It is not yet a frozen v1
contract. Stable interfaces and serialization formats described here must be
validated by representative migrations before they are frozen.

## Context

`metamath-logic` is the first non-trivial package released on top of
ProofScaffold. At the time this specification is being drafted, its authoring
and migration work has passed the halfway point. That makes it more than a
demonstration package: it is now a substantial empirical corpus containing
many successful proof-authoring patterns, failed abstractions, compatibility
constraints, and repeated maintenance costs.

The experience confirms that the lower half of the architecture is broadly
sound:

- packages have a single `build(ctx)` entrypoint;
- BuilderV2 accepts `SymbolId`-level payloads and constructs IR;
- the linker owns dependency, scope, relocation, ordering, and emission;
- emitted Metamath remains ASCII canonical;
- the Metamath verifier remains the semantic authority.

These boundaries are already specified by
[BuilderV2 v1](../references/009_builder-v2.md) and
[Foundation Scope v1](../references/010-foundation-scope.md). This project does
not reopen them.

The same experience shows that the authoring half has not yet reached an
equally clean boundary. `metamath-logic` contains enough real work to reveal
recurring costs that smaller examples did not expose:

- language facts such as sort, arity, notation, canonical token, parser rule,
  syntax assertion, and lowering shape are registered in multiple places;
- an assertion's signature, proof constructor, registry entry, export,
  coverage declaration, catalogue entry, and build ordering are maintained
  separately;
- proof steps repeat labels, instantiated result formulas, references,
  premises, and notes even when most of that information is derivable;
- authoring expressions, token formulas, and proof unification use overlapping
  representations of the same syntax;
- global registries and caches introduce import-order state;
- incomplete or unsupported proof states are not represented as first-class
  drafts;
- the current authoring representation is not a stable public API that tools
  can query, serialize, or transform.

The author model has also changed. The original
[authoring-first design](../references/005-authoring.md) primarily describes a
human writing Python and mathematical notation. Future authors include IDEs,
formatters, refactoring tools, and LLM agents. Humans and LLMs should share the
same mathematical semantics, but they have different interaction needs:

- humans prioritize readable Unicode notation, low ceremony, and local source
  clarity;
- LLMs need bounded actions, explicit state, stable identifiers, structured
  diagnostics, checkpoints, and a short propose/validate/repair loop;
- both need deterministic elaboration and the same verifier-backed result.

This project therefore treats `metamath-logic` as the evidence base for a
second authoring design pass. The goal is not to design a special logic API for
one package. The goal is to extract a smaller, public, reusable authoring model
that serves both human and machine authors.

## Problem Statement

ProofScaffold currently has a stable build and link boundary, but no equivalent
public semantic boundary for authoring.

The current path is approximately:

```text
Python/string input
    -> authoring Expr
    -> SymbolId token formula
    -> proof-specific parsed shape
    -> SymbolId token formula
    -> BuilderV2 / linker / verifier
```

This creates two related problems.

First, the framework cannot reliably derive authoring services from a single
source of truth. Parsing, pretty printing, schema matching, catalogue
generation, LaTeX rendering, dependency queries, and lowering each reconstruct
some part of the theory.

Second, an external authoring tool has no stable object to operate on. It can
either edit Python text or depend on current internal classes. Neither provides
the versioned, typed, partially complete, replayable state needed by an IDE or
LLM.

The target is a shared semantic core with different author-facing projections:

```text
Human Unicode DSL / Python facade ----\
                                       \
Compact proof script ------------------> typed authoring actions
                                       /
IDE / LLM tool protocol --------------/
                |
                v
       Draft Authoring IR / Workspace
                |
       deterministic elaboration
                v
        Elaborated Authoring IR
                |
         Metamath lowering
                v
      BuilderV2 / linker / verifier
```

## Current State and Empirical Findings

The following observations are evidence for the project, not frozen behavior:

- The current authoring AST is not ready to serve as public semantic IR. In
  particular, [`App`](../src/skfd/authoring/dsl.py#L139-L146) currently excludes
  both its constructor and arguments from generated equality and hashing.
- The current [`ProofBuilder`](../src/skfd/proof/ir.py#L32-L169) stores
  token-level `Wff` results, asks callers to repeat instantiated formulas and
  labels, and uses Python object identity to recover step references.
- The current proof path reparses token formulas for unification instead of
  keeping one typed semantic tree through proof construction and lowering.
- Under a loose configuration, the current
  [unsupported-step path](../src/skfd/authoring/emit.py#L656-L683) classifies a
  theorem for axiom emission. That behavior is incompatible with untrusted or
  automated authors and must not survive in Authoring v2.
- ProofScaffold already has a useful structured-diagnostic foundation in
  [`Diagnostic`](../src/skfd/core/diag.py#L8-L40), but authoring failures do not
  yet consistently use an equally rich, machine-repairable schema.
- [`BuildContextV2`](../src/skfd/api_v2.py#L66-L83) is a successful explicit
  boundary. Authoring v2 should follow the same principle: pass capabilities
  and immutable interfaces explicitly rather than relying on import-time
  globals.

These findings explain why this project starts with correctness hardening and
representation unification before adding a richer human DSL or an LLM tool
surface.

## Goals

1. Define one typed semantic representation for authoring terms, assertion
   signatures, and proof applications.
2. Define `LanguageSpec` and `AssertionDecl`/`TheorySpec` as the sources from
   which parser, notation, interfaces, registries, and lowering metadata are
   derived.
3. Expose versioned, deterministic Authoring IR through a public Python API and
   canonical serialization.
4. Make incomplete proofs first-class through typed goals, holes, constraints,
   and workspace snapshots.
5. Provide a concise human facade and a structured LLM/IDE action protocol over
   the same semantics.
6. Infer only information that is local, unique, deterministic, and fully
   reified in the result.
7. Preserve verifier authority and fail closed at every authoring boundary.
8. Enable future tools such as LaTeX renderers, theorem browsers, dependency
   analyzers, canonical formatters, and model-context generators without
   reading BuilderV2 internals.
9. Migrate incrementally while preserving existing package output, labels,
   exports, and verification behavior.

## Non-Goals

- Changing Metamath semantics or enlarging the trusted computing base.
- Replacing BuilderV2, the linker pipeline, or existing verifier aggregation.
- Shipping a particular LLM provider, model runtime, prompt template, MCP
  server, or editor integration as part of the semantic core.
- Making heuristic proof search part of deterministic elaboration.
- Automatically deciding which connectives are primitive, whether a proposed
  definition is mathematically appropriate, or which assertions form the
  public API of a theory.
- Automatically approving axioms, language extensions, dependency changes, or
  releases proposed by an LLM.
- Guaranteeing lossless round-tripping of arbitrary Python control flow.
- Migrating every `metamath-logic` theorem in one change.
- Requiring natural-deduction authoring in the first implementation slice.

## Existing and Frozen Boundaries

The following constraints remain authoritative.

1. `build(ctx)` remains the package build entrypoint.
2. BuilderV2 remains a `SymbolId`-level IR builder.
3. Cross-package build/link truth remains `SymbolId`-based. A companion
   authoring interface may carry semantic metadata, but it must resolve to the
   same exported symbols and must not bypass linker access control.
4. BuilderV2 LIR, linked IR, and emitted `.mm` remain ASCII canonical. Source,
   Draft, and Elaborated Authoring IR may retain Unicode presentation metadata,
   but it must be normalized away from the BuilderV2 payload.
5. Unicode belongs to authoring and display projections. LanguageSpec-based
   alias handling must preserve the existing `NameResolver`/Lexicon and
   machine-readable `*.names.json` mapping contract.
6. Auto-`$f` behavior remains available, including reuse of existing
   foundation floating hypotheses rather than generating duplicates.
7. Foundation-owned `$f` visibility remains special by linker ownership.
   Ordinary package `$f` and `$e` labels do not become public authoring
   dependencies through `TheoryInterface` metadata.
8. Linker stages remain authoritative for dependency access, foundation scope,
   relocation, deterministic ordering, and diagnostics at the build boundary.
9. Every emitted theorem remains subject to Metamath verification.
10. Existing BuilderV2 v1 APIs evolve additively.

## Terms

- **Concrete syntax**: a human- or model-written formula string, including its
  Unicode spelling and source span.
- **Term**: the canonical, typed semantic tree produced after parsing and name
  resolution.
- **SemanticId**: a stable authoring identity for a symbol, assertion, or other
  declaration. It is not a process-local integer `SymbolId`.
- **Source Authoring IR**: declarations and author-provided proof operations,
  retaining source spelling and spans where available.
- **Draft Authoring IR**: a partially elaborated proof state containing goals,
  holes, local hypotheses, and unresolved constraints.
- **Elaborated Authoring IR**: a complete, typed, resolved proof DAG with every
  application and substitution made explicit.
- **Metamath Lowered IR**: target-specific authoring output containing canonical
  token layout, labels, hypotheses, and proof order before binding to the
  current build's `SymbolId`s.
- **Facade**: a human, Python, editor, or LLM interface that produces the same
  typed authoring operations.
- **Workspace snapshot**: an immutable, digest-addressed view of an authoring
  session.
- **Query**: a typed, read-only inspection of a workspace snapshot or theory
  interface. It does not create a new revision.
- **Action**: one typed request to transform a workspace snapshot.
- **Transaction commit**: atomically persists a new Draft snapshot. It may
  still contain open holes.
- **Finalization/publication**: turns a complete draft into an assertion
  candidate after elaboration, lowering, and verification gates succeed.
- **Elaboration**: deterministic parsing, resolution, type checking,
  instantiation, constraint checking, and proof construction. It is not
  heuristic proof search.

## Proposed Invariants

The target implementation must satisfy these invariants before its public API
is frozen.

**A1. Shared semantic core.** Human and LLM facades MUST produce the same Term,
declaration, proof, and diagnostic semantics.

**A2. Verifier authority.** No Authoring IR, action result, cached elaboration,
or model output may bypass normal lowering and verification.

**A3. Fail closed.** A failed, unsupported, incomplete, or ambiguous proof MUST
NOT be emitted as an axiom, raw assertion, or verified theorem.

**A4. Typed before proof reasoning.** Parsing and name resolution MUST produce a
typed Term before equality, unification, substitution, or proof application is
performed.

**A5. Unique-only inference.** A facade MAY omit an input only when it is
locally and uniquely determined. The elaborator MUST reify every inferred
premise, substitution, and result in Elaborated IR. Ambiguous theorem choice,
premise choice, or substitution MUST become an explicit obligation or
diagnostic.

**A6. Stable declaration identity.** Public symbols and assertions MUST use
explicit SemanticIds that do not depend on import order, Python object identity,
file location, or process-local integer allocation.

**A7. Deterministic requests.** Given the same interface digests, workspace
snapshot, policy, and query or action, the system MUST return byte-equivalent
canonical results and diagnostics.

**A8. Draft isolation.** Drafts MAY contain holes and unresolved obligations
and MAY be transactionally persisted, but a draft with any open obligation
MUST NOT lower, finalize, export, or publish as a verified assertion.

**A9. Model and transport neutrality.** The semantic API MUST NOT depend on a
specific model, prompt, editor, RPC transport, or tool-call encoding.

**A10. Presentation is not identity.** Unicode, ASCII aliases, LaTeX, short
session handles, and pretty-printed names MUST be projections of semantic
objects, not independent identities.

**A11. Additive backend integration.** Authoring v2 MUST lower through the
existing BuilderV2/linker contract without changing its frozen v1 behavior.

**A12. Provenance is non-semantic.** Human/LLM authorship, model version, source
span, action log, and explanatory notes MAY be recorded, but MUST NOT change the
mathematical identity or verifier result of a proof. Timestamps, session IDs,
runtime metadata, and author identity MUST be excluded from semantic equality,
the semantic digest, and the canonical semantic projection.

## Target Semantic Model

### `LanguageSpec`

A logical constructor should be declared once. A declaration includes at least:

- a stable semantic key, such as `prop.imp`;
- input and output sorts;
- canonical Metamath token layout;
- preferred Unicode display notation;
- preferred metavariable display families by sort, such as `φ`, `ψ`, `χ` for
  propositional schema atoms;
- accepted input aliases;
- prefix, infix, binder, or mixfix form;
- precedence and associativity where applicable;
- syntax assertion metadata required by lowering;
- optional LaTeX notation;
- binder and free-variable behavior where applicable.

The framework SHOULD derive the following from the same `LanguageSpec`:

- lexer and parser registrations;
- typed constructors;
- alias normalization;
- canonical human pretty printing;
- authoring style validation;
- generic Term traversal and schema matching;
- Metamath token layout and syntax-construction proof metadata;
- LaTeX and model-facing projections.

If a constructor requires a syntax assertion, that assertion should be derived
from `LanguageSpec` or linked to it by one SemanticId. It must not become a
second independently editable declaration of the same language fact.

Adding a connective to an ordinary theory should not require editing the
framework parser, unifier, and emitter independently.

### Typed `Term`

`Term` is the semantic backbone of Authoring v2. It must support at least:

- `Wff` terms;
- set-variable terms;
- class terms;
- sorted schema metavariables;
- constructor applications;
- binder-aware free-variable and capture analysis;
- structural equality and hashing;
- source spans as optional side information.

Formula strings are concrete syntax, not semantic values. APIs MAY accept a
`FormulaLike = Term | str` convenience type, but strings must be parsed,
resolved, normalized, and typed at the boundary.

Different constructors or argument trees MUST produce unequal Terms. Display
aliases such as `->`, `→`, and `⇒` MAY parse to the same semantic constructor.

### `AssertionDecl` and `TheorySpec`

An assertion declaration includes at least:

- stable assertion SemanticId;
- canonical Metamath label;
- kind: syntax, axiom, definition, rule, lemma, or theorem;
- sorted schema variables;
- essential hypotheses;
- conclusion;
- distinct-variable, binder, and capture constraints;
- proof or an explicit absence of proof for declared axioms;
- visibility and export intent;
- stability status, documentation, and origin.

The assertion signature MUST be available without executing its proof body.

A `TheorySpec` or `PackageSpec` SHOULD be the source from which the framework
derives:

- assertion registries;
- authoring proof-dependency graphs and deterministic within-unit declaration
  input order;
- declared proof coverage;
- public exports and authoring interfaces;
- catalogues and theorem-browser data;
- release-interface diffs.

Ordinary package build orchestration should eventually approach:

```python
def build(ctx: BuildContextV2) -> None:
    emit_package(ctx, PACKAGE)
```

Low-level BuilderV2 calls remain an escape hatch for foundation and specialized
emission, but such hooks must be explicitly marked as opaque to authoring tools.

### Stable IDs and package interfaces

Public authoring IDs should be explicit and readable, for example:

```text
metamath-logic/propositional#symbol:imp
metamath-logic/propositional#assertion:syl
```

The package version and content digest are separate from identity. Moving a
declaration between Python files must not change its SemanticId. Renaming a
public assertion is an explicit API change or a deprecated alias migration.

`ExportsView[str, SymbolId]` remains the build/link interface. Authoring v2 adds
a companion `TheoryInterface` containing notation and exported assertion
signatures. The interface must identify the same exports and must carry a
canonical content digest so tools can detect stale context.

## Authoring IR Stages

### Source Authoring IR

Source IR preserves author-provided information:

- raw formula spelling where supplied;
- parsed or constructor-built terms;
- unresolved references before elaboration;
- explicitly supplied premises, targets, and substitutions;
- documentation, visibility, and status;
- package-relative source spans;
- optional human-readable notes.

Executing a declarative Python facade may produce Source IR, but Source IR does
not promise to reconstruct arbitrary Python control flow.

### Draft Authoring IR

Draft IR represents work in progress. A typed hole contains at least:

- `HoleId`;
- expected Term and sort;
- local hypotheses;
- unresolved metavariables;
- distinct-variable and binder constraints;
- originating action and source span when available;
- status and related diagnostics.

Both forward construction and backward refinement are permitted:

- applying an assertion to existing steps computes a new result;
- refining a goal with an assertion creates ordered subgoals.

A draft can be saved, forked, inspected, and resumed. It cannot be lowered or
published until it has zero holes and zero unresolved obligations.

### Elaborated Authoring IR

Elaborated IR is the default public semantic API for downstream tools. It
contains:

- language-scoped typed Terms;
- normalized semantic symbol identities;
- resolved assertion references;
- complete assertion signatures and constraints;
- an explicit proof DAG;
- stable premise references;
- the final substitution and inferred result for every proof application;
- dependency and provenance information;
- source spans where available.

It does not contain process-local SymbolIds or depend on Python object identity.

### Metamath Lowered IR

The lowered authoring stage contains target-specific information:

- canonical ASCII token keys and layouts;
- canonical labels;
- `$f`, `$e`, `$a`, `$p`, and `$d` requirements;
- syntax-construction proofs;
- RPN proof order;
- deterministic within-unit declaration and export input order.

Only the final build bridge binds these semantic/canonical keys to the current
build's SymbolIds and calls BuilderV2.

Authoring order is input to the linker, not a replacement for it. The linker
continues to decide cross-unit topological order, scope placement, relocation,
and final emission order.

## Human Authoring Facade

The human facade should optimize mathematical readability and remove choices
that carry no mathematical information.

The core proof operation should approach:

```python
step = p.use(assertion, *premises, target=None, subst=None)
```

The elaborator follows these rules:

1. Match supplied premises against the assertion's typed hypotheses.
2. Infer substitutions that are uniquely determined by those premises.
3. Derive the assertion result rather than trusting a caller-supplied result.
4. Require `target` or `subst` for remaining schema variables.
5. Reject ambiguity rather than choosing a candidate.
6. Check distinct-variable, binder, and capture constraints.
7. Return a typed `StepRef`, not a formula object used as an identity proxy.
8. Generate internal step labels deterministically unless the author supplies a
   stable key for tooling.
9. Treat notes as explanatory metadata, not proof semantics.

Unicode is the preferred human presentation. ASCII Metamath spelling remains an
accepted input compatibility mode, and a style profile may enforce preferred
Unicode in package source. Both forms normalize to the same Term.
Preferred schema-atom displays are selected by the language/style policy, so a
formatter can render `φ`, `ψ`, and `χ` consistently without relying on an LLM
or human to reproduce the glyph convention manually.

Searching all prior proof steps for matching hypotheses is not core
elaboration. It may be exposed as an explicit, bounded tactic whose chosen
premises and substitution are reified in the resulting proof DAG.

## LLM and IDE Authoring Protocol

An LLM should be treated as an untrusted client of Authoring IR, not as a human
whose primary capability is writing arbitrary Python.

The semantic protocol is a deterministic state transition:

```text
transition(snapshot, action, policy)
    -> (new_snapshot, explicit_effect)
     | structured_diagnostic
```

The transport may be a Python API, CLI, JSON-RPC, MCP tool, or another editor
protocol. Transport choice is outside this specification.

### Request envelope

A machine request should carry:

- protocol/schema version;
- session and optional transaction ID;
- base workspace revision/digest;
- theory/interface digest;
- typed query or action payload;
- explicit inference/search policy when applicable.

A mutating action additionally carries a client-generated idempotency ID.

Read-only queries should remain small and composable:

- inspect capabilities and current proof state;
- parse or render a Term;
- search and inspect assertion interfaces;
- request a dependency or context slice;
- diff or validate a snapshot without mutating it.

Mutating actions should remain small and composable:

- open a theorem or proof hole;
- assume, apply, refine, solve, or close a goal;
- begin, checkpoint, fork, rollback, or commit a draft transaction;
- request finalization or publication.

The model may supply a target as a constraint, but the framework computes the
actual result, premise order, and substitution. A model claim is never accepted
as semantic truth.

For efficiency, the protocol MAY support atomic action batches or a compact
proof-script syntax. Such syntax is only sugar: it must compile to the same
typed actions and pass the same transaction and elaboration checks. The core
must not `eval` model-generated Python.

### Workspace and transaction behavior

1. A read-only query returns the current revision and leaves it unchanged.
2. Every successful mutating action returns a new revision and explicit effect.
3. A failed mutating action is atomic and reports that the state is unchanged.
4. Repeating a mutating action ID against the same base is idempotent.
5. Stale-base transaction commits fail through compare-and-swap semantics.
6. Checkpoints and forks allow alternative proof attempts without mutating the
   accepted branch.
7. Draft transaction commit is distinct from assertion finalization and
   publication. A transaction may persist a partial draft.
8. Parse, resolve, typecheck, elaborate, lower, and verify are distinct
   finalization/publication gates with structured results.
9. Identical base state, interface digests, policy, and action log produce
   byte-equivalent Elaborated IR and diagnostics.
10. Any search seed, candidate order, or resource budget is explicit and
   recorded if a non-core tactic is used.

### State and query surface

An LLM should not receive the entire theory in every prompt. A proof-state query
returns a bounded, addressable frontier:

- current goals and local hypotheses;
- recent typed steps;
- unresolved metavariables and constraints;
- workspace and theory digests;
- validation status;
- optional remaining resource budget.

Larger data is retrieved on demand:

- assertions by symbol, conclusion shape, sort, hypothesis count, or
  unifiability;
- complete assertion signatures;
- dependency slices;
- selected proof examples;
- Term and proof rendering in Unicode, structured form, or LaTeX.

Search is advisory. A client must select a stable assertion SemanticId before a
proof-changing action occurs. Short session handles may reduce token usage, but
they are valid only under the context digest that issued them.

### Prompt independence and untrusted prose

The core exposes semantic context, not a blessed `to_llm_prompt()` string.
Model-specific message construction belongs to an adapter outside the semantic
API.

Package documentation, theorem prose, and examples are untrusted data when
included in model context. They must remain distinguishable from tool policy
and system instructions. Free-form model rationale may be stored as
non-semantic metadata, but the framework neither requires nor relies on hidden
chain-of-thought.

## Structured Diagnostics

Diagnostics are part of the public authoring protocol, not merely formatted
exceptions.

A diagnostic should contain at least:

- stable error code and phase;
- action path or source span;
- workspace revision and `state_unchanged` status;
- expected and supplied sorts or Terms;
- mismatch path;
- inferred substitution so far;
- unresolved metavariables;
- failed distinct-variable or binder constraints;
- related declaration and premise spans;
- deterministically ordered candidates where relevant;
- typed repair suggestions;
- stable diagnostic fingerprint.

Examples include:

- unknown or unavailable SemanticId;
- stale workspace or theory digest;
- parse or sort mismatch;
- premise mismatch;
- unresolved or ambiguous substitution;
- goal mismatch;
- binder capture or distinct-variable violation;
- dependency access violation;
- proof cycle;
- open holes at finalization or publication;
- unavailable capability.

Natural-language messages are human projections of the same structured data.
Clients should be able to repair common failures using codes and typed fields
without parsing prose.

## Trust and Capabilities

LLM safety must be enforced by capabilities and validation, not by prompt
instructions.

Suggested capability levels are:

1. read, search, and render;
2. create theorem drafts;
3. edit proofs within an allowed package/theory;
4. declare definitions or theorem statements;
5. extend a language;
6. declare axioms or change dependencies/exports;
7. release a package.

Ordinary LLM sessions should default to levels 1-3. Language extensions,
axioms, dependency changes, public exports, conformance changes, and releases
require separate explicit authority and normally human review.

The following rules are mandatory:

- axioms are explicit declarations, never a fallback from proof failure;
- `raw` or opaque proof steps cannot close a normal verified goal;
- relaxing distinct-variable, scope, or conformance policy requires a separate
  capability;
- finalization/publication requires zero holes, complete elaboration,
  successful lowering, and normal verifier success;
- author provenance does not change verification requirements.

## Public API and Serialization

The core public surface should expose immutable data, queries, codecs, and
visitors rather than implementation registries. Candidate public concepts are:

- `LanguageSpec` and `TheorySpec`;
- `SemanticId`, `Term`, `AssertionSignature`, and `TheoryInterface`;
- `SourceAuthoringIR`, `DraftAuthoringIR`, and
  `ElaboratedAuthoringIR`;
- `Goal`, `Hole`, `StepRef`, `ProofDAG`, and `WorkspaceSnapshot`;
- `Query`, `QueryResult`, `Action`, `ActionResult`, and
  `AuthoringDiagnostic`;
- query and exporter protocols.

Each serialized stage has an independent format identifier, for example:

- `skfd-authoring-source-v1`;
- `skfd-authoring-draft-v1`;
- `skfd-authoring-elaborated-v1`;
- `skfd-authoring-metamath-v1`.

Serialization requirements:

- canonical JSON and a published JSON Schema;
- deterministic field and map ordering;
- explicit arrays for semantically ordered declarations and proof premises;
- structured Term trees, not only pretty strings;
- package-relative source paths;
- no Python repr, pickle, absolute workspace path, or process-local SymbolId;
- language and dependency interface digests;
- a semantic digest over the canonical semantic projection, excluding
  timestamps, sessions, runtime metadata, and author identity;
- an optional archival/document digest for a projection that includes
  non-semantic provenance;
- explicit migrations for supported schema revisions.

A migration implementation is required only after a second schema revision is
declared supported. Unknown or unsupported versions still fail explicitly from
the first release.

Canonical JSON is an interchange and cache format. This project does not yet
decide that JSON replaces Python or a future human-readable declarative format
as package source.

## Exporters and Authoring Tools

Exporters consume immutable IR and must not affect semantics.

A LaTeX exporter should normally consume Elaborated IR and use notation from
`LanguageSpec`. It can render signatures, proof tables, dependency-only views,
or full derivations without consulting BuilderV2 internals.

An LLM context exporter also consumes Elaborated or Draft IR, but emits a
model-neutral semantic projection:

- stable theorem and symbol IDs;
- variables and sorts;
- hypotheses, goal, and constraints;
- proof-step references, substitutions, and results;
- bounded dependency and example slices;
- optional documentation and source context.

Prompt templates remain outside the exporter. Any proof returned by a model
re-enters Source/Draft IR and normal elaboration; structured input never grants
a verification shortcut.

## Current Hardening Preconditions

Before current authoring objects can become the public semantic IR, at least the
following issues must be addressed:

1. Structural equality and hashing must include constructor and arguments for
   authoring applications.
2. Unsupported proof steps must fail closed instead of being emitted as axioms
   under a loose configuration.
3. Language/parser/proof registries must become theory-scoped and deterministic
   rather than import-time global mutable state.
4. Alias normalization must preserve one semantic constructor identity.
5. Assertion signatures must be static data rather than discovered by executing
   proof constructors.
6. Proof steps must use typed `StepRef`s rather than Python object identity.
7. Proof and Term origins must include usable source spans.
8. Authoring and signature discovery must not swallow exceptions and silently
   omit failed declarations.

These are correctness prerequisites, not optional ergonomics work.

## Compatibility and Migration

- All new APIs begin additively under an Authoring v2 namespace or similarly
  explicit version boundary.
- Existing `ProofBuilder`, registries, and hand-written `build.py` files remain
  supported through adapters during migration.
- Existing ASCII/set.mm spelling remains accepted input; preferred Unicode is a
  formatter/style policy.
- Public labels, canonical tokens, export order, and verifier-visible theorem
  content remain unchanged for migrated proofs unless a separate change says
  otherwise.
- Representative migrations must use golden output and verifier aggregate
  checks.
- Opaque custom build hooks remain possible, but their authoring interface is
  explicitly incomplete and tools must not invent missing semantic data.
- Packages can migrate declaration by declaration or module by module; a single
  release need not convert all existing proofs.

## Work Plan

### Phase 0 - Empirical baseline

Deliverables:

- Select representative propositional, derived-connective, predicate, binder,
  and distinct-variable proofs from `metamath-logic`.
- Record current emitted `.mm`, names metadata, exports, ordering, and verifier
  aggregate results.
- Record authoring metrics such as repeated formulas, manually supplied labels,
  explicit substitutions, diagnostics, and proof-construction call counts.

Acceptance:

- The corpus is reproducible from pinned package revisions.
- It contains positive proofs and known authoring failure cases.
- Golden artifacts are deterministic across two clean processes.

### Phase 1 - Fail-closed authoring hardening

Deliverables:

- Fix structural Term/Expr equality.
- Remove proof-failure-to-axiom behavior from verified authoring paths.
- Make axiom declaration explicit.
- Replace silent registry overwrite and swallowed discovery errors with
  structured diagnostics.
- Capture useful origins for Terms, declarations, and proof steps.

Acceptance:

- Adversarial tests prove that different application trees are unequal.
- An unsupported proof cannot lower or verify as an axiom.
- Import order does not silently select a different constructor or assertion.
- Failure diagnostics are deterministic.

### Phase 2 - `LanguageSpec` and typed `Term`

Deliverables:

- Introduce theory-scoped immutable language declarations.
- Derive parser, aliases, pretty printing, typing, and lowering metadata from
  those declarations for a representative propositional slice.
- Support `Wff`, set-variable, and class sorts needed by the predicate slice.
- Introduce generic binder-aware Term traversal and schema matching.
- Add a canonical human formatter/style checker derived from language notation
  and metavariable display policy.

Acceptance:

- Adding a test connective requires one language declaration plus its
  mathematical declaration, without framework parser/unifier/emitter edits.
- Two theories can use the same glyph without import-order interaction.
- Unicode and ASCII aliases normalize to equal Terms and emit identical
  canonical tokens.
- The formatter/style checker presents declared connectives using preferred
  Unicode and propositional schema atoms using declared Greek display names,
  while ASCII input, ASCII BuilderV2 output, and stable names mapping remain
  supported.
- Predicate binder and sort errors fail at the Term boundary.

### Phase 3 - Static assertions and human proof facade

Deliverables:

- Introduce static `AssertionSignature`, `AssertionDecl`, and typed `StepRef`.
- Implement `use(assertion, *premises, target=None, subst=None)` with unique-only
  inference.
- Adapt the new proof HIR to current lowering.
- Keep the old `ProofBuilder` path through a compatibility adapter.

Acceptance:

- An assertion catalogue can be generated without executing proof bodies.
- Premises that uniquely determine an instance derive the same result without a
  repeated target formula.
- An underdetermined instance requests `target` or `subst` through a structured
  diagnostic.
- Migrated representative proofs emit verifier-equivalent output.

### Phase 4 - `TheorySpec`, package interface, and public IR

Deliverables:

- Introduce `TheorySpec`/`PackageSpec` and generic package emission.
- Derive registry, coverage, authoring dependency, catalogue, export, and
  within-unit declaration-order data.
- Publish immutable Source and Elaborated IR, canonical JSON codecs, JSON
  Schema, visitors, and `TheoryInterface` sidecars.
- Define SemanticId and interface digest policies.

Acceptance:

- Canonical serialize/deserialize round trips preserve Terms, signatures,
  constraints, and proof DAGs.
- Source and Elaborated fixtures validate against their published schemas.
- Codecs reject process-local SymbolIds and absolute workspace paths, and an
  unknown schema version fails explicitly.
- The same interface serializes byte-identically in separate processes.
- Equivalent proofs with different non-semantic authorship metadata have the
  same semantic digest.
- A downstream authoring client can inspect an exported assertion signature
  without importing and executing its implementation module.
- Existing linker access control and verifier behavior remain unchanged.

### Phase 5 - Draft workspace and action protocol

Deliverables:

- Introduce typed goals, holes, constraints, immutable snapshots, and action
  results.
- Implement transaction, revision, checkpoint, fork, rollback, validation, and
  draft-commit versus finalization/publication semantics.
- Implement structured machine-repairable authoring diagnostics.
- Provide a transport-neutral query/action API.
- Publish a canonical Draft snapshot codec and schema.

Acceptance:

- Replaying one action log from one base digest produces byte-identical Draft
  IR and, when the draft is complete, byte-identical Elaborated IR.
- Draft snapshot fixtures round-trip and validate against the published schema.
- Read-only queries leave the revision unchanged.
- A failed action leaves the workspace revision unchanged.
- Retrying an idempotent action does not duplicate a step.
- A stale transaction commit is rejected without overwriting newer state.
- A draft with a hole can be persisted but cannot lower, finalize, export,
  publish, or verify as complete.
- Human facade operations and equivalent machine actions elaborate to the same
  proof DAG.

### Phase 6 - Tool projections and LLM evaluation

Deliverables:

- Add model-neutral context queries and bounded dependency slices.
- Add initial LaTeX and LLM semantic exporters.
- Build a benchmark by hiding selected existing `metamath-logic` proofs while
  retaining their allowed dependency interfaces.
- Compare structured action authoring with direct Python/source generation.

Acceptance:

- Exporters consume public IR and do not read BuilderV2 private state.
- Model context can be bounded without changing theory identity.
- A bounded context query accepts an explicit item/depth/size budget, reports
  truncation and a continuation cursor, and leaves the theory digest unchanged.
- Every accepted generated proof passes the normal verifier and preserves the
  declared trust boundary.
- Evaluation reports verified completion, invalid actions, diagnostic recovery,
  context cost, replay success, and dependency/trust violations rather than
  code volume alone.

### Phase 7 - Post-v1 optional higher-level proof HIR

This phase is not required for the Project 021 Definition of Done.

Deliverables:

- Evaluate scoped assumptions, `show`/`have`/`exact`, assumption discharge, and
  natural-deduction-like authoring over the same Term and Draft IR.
- Elaborate accepted high-level steps to explicit Hilbert proof DAGs.

Acceptance:

- High-level proofs lower to normally verified Metamath proofs.
- The elaboration trace exposes every generated dependency and substitution.
- Heuristic search, if any, remains an explicit bounded tactic outside the
  deterministic core.

## Definition of Done

Project 021 is complete when:

1. Human and machine facades share one typed Term and assertion semantics.
2. Public, versioned Source and Elaborated Authoring IR can be queried and
   canonically serialized without process-local identities.
3. Incomplete proof work is represented by a persistable, canonically
   serializable Draft IR that cannot enter a verified release path.
4. Deterministic queries, actions, revisions, transactions, and structured
   diagnostics support replayable IDE/LLM authoring.
5. `LanguageSpec` and `TheorySpec` remove the principal duplicated language and
   assertion registrations demonstrated by `metamath-logic`.
6. Representative human proofs require only mathematically meaningful choices;
   internal labels, results, and substitutions are derived where uniquely
   determined. Explanatory notes remain optional and are never fabricated or
   trusted as proof semantics.
7. Normal LLM capabilities cannot add axioms, relax constraints, change
   dependencies, or release a package.
8. LaTeX and model-context tools consume public IR rather than internal
   registries or BuilderV2 tokens.
9. Migrated `metamath-logic` slices preserve canonical output, exports, and
   verifier results.
10. BuilderV2 v1, foundation scope, linker behavior, and verifier authority
    remain intact.

## Risks

- **Overfitting to propositional logic.** The first slice is easy to model but
  can hide sort, binder, capture, and distinct-variable requirements. Predicate
  cases must participate before the IR is frozen.
- **Freezing too early.** Public serialization is costly to change. Initial
  formats should remain explicitly experimental until representative migrations
  and replay tests pass.
- **Creating another source of truth.** IR, Python declarations, registries, and
  generated files can drift if all are editable. Derived artifacts must identify
  their source and digest, and only one declaration path may be authoritative in
  a given package slice.
- **Overly verbose machine protocols.** Full JSON trees can waste model context.
  Stable references, bounded queries, atomic batches, and compact syntax sugar
  should reduce repetition without weakening semantics.
- **Automation creep.** Convenient auto-matching can become context-sensitive
  proof search. Unique-only elaboration and explicit tactic boundaries must be
  preserved.
- **Unsafe source execution.** Treating generated Python as the machine protocol
  can execute unrelated code. Structured actions are authoritative; Python is a
  human facade or explicitly sandboxed extension.
- **Prompt injection through package prose.** Documentation included in model
  context must be kept separate from tool policy and semantic fields.
- **Identifier migration.** Stable SemanticIds introduce an API commitment.
  Alias and deprecation policy must be designed before broad publication.

## Open Questions

1. Should declarative proof documents eventually become package source, or
   should Python remain primary while canonical IR is an exchange format?
   Initial recommendation: keep both options open; do not require round-tripping
   arbitrary Python.
2. Which SemanticIds are stable across package versions, and which proof-node
   IDs are only snapshot-local? Initial recommendation: declarations are stable;
   generated step IDs are occurrence-local unless explicitly keyed.
3. Which transport should ship first for the action protocol? Initial
   recommendation: implement a typed Python service first and derive JSON/tool
   schemas from it.
4. When should JSON formats be frozen? Initial recommendation: after
   propositional and predicate/DV migrations both pass determinism and replay
   tests.
5. How should conservative definitions be certified? This requires a separate
   design before definition-authoring capabilities can be granted broadly.
6. When should assumption-aware or natural-deduction HIR enter the roadmap?
   Initial recommendation: only after Term, assertion signatures, Draft IR, and
   deterministic elaboration are shared and stable.
