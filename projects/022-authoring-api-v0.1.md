# Project 022: Authoring API v0.1 Draft

## Status

Draft, 2026-07-14.

This document turns the broader direction in
[Project 021](./021-authoring-ir-for-human-and-llm-authors.md) into a deliberately
small v0.1 API proposal. It is a design and experiment contract, not a frozen
public release. The next step is to test it in `proof-lab`; this document does
not implement that test.

[Project 023](./023-concrete-proof-families-and-combinators.md) defines the
companion transpiled-corpus experiment for concrete family factories and proof
combinators.

Normative words such as MUST, SHOULD, and MAY describe the intended v0.1
contract. Python and action examples are pseudocode. Their semantics are more
important than their final spelling.

### 2026-07-16 architecture amendment

The first-class-language work in
[Reference 011](../references/011-language-as-first-class.en.md) and
[Project 024](./024-first-class-language-refactor.en.md) narrows several types in
this draft before they may be frozen:

- `LanguageSpec` contains only semantic sorts, variable kinds, constructors,
  and binder structure.
- Parsing and rendering belong to `NotationSpec`.
- Metamath typecodes, token templates, syntax assertions, and lowering belong
  to `MetamathLanguageBinding`.
- `Judgment` and `CalculusSpec` sit between language and logic. `|-` is not an
  object-language constructor.
- `AssertionSignature.premises` and `.conclusion` are judgment patterns, not
  bare Terms. v0.1 may implement only `Provable(Wff)`, but its public types MUST
  NOT make that one judgment implicit.
- Semantic, notation, backend, calculus, and theory-interface digests are
  separate. Display-only changes MUST NOT invalidate Term or proof identity.

The legacy `Expr`/`App` and global constructor registries are compatibility
surfaces, not the implementation of these contracts. A structural immutable
Term v2 MUST precede finalization of `ProofDraft`, `ApplyAssertion`, and
`ElaboratedProof` public types. The proof operation described by this project
remains valid; its input types are retargeted to Term v2 and explicit judgments.

## Executive decision

Authoring v0.1 has one semantic core, not four authoring systems.

Two independent axes describe an author:

| Axis | Alternatives | API consequence |
| --- | --- | --- |
| Interaction | human / agent | concise facade versus typed query/action projection |
| Authority | proof author / library author | capabilities and writable objects |

The three `proof-lab` task types are a third, external dimension:

- `proof`: the theory and target statement are already fixed;
- `formalize`: source interpretation, definitions, and assumptions must be
  made explicit before or alongside proof work;
- `discover`: computation or research may propose candidates, but does not
  itself create trusted assertions.

These are workflows and evidence states. They MUST NOT create three different
term languages or proof semantics. Human and agent projections MUST elaborate
to the same immutable objects. Every result claimed as a completed formal proof
or admitted assertion MUST follow the normal BuilderV2, linker, and Metamath
verification path. A valid computational or audited research outcome need not
become a formal assertion at all.

The minimal v0.1 semantic path is:

```text
human facade -----------\
                        > typed request -> immutable ProofDraft
agent query/actions ----/                         |
                                                  v
                                      deterministic elaborator
                                                  |
                                                  v
                                         ElaboratedProof
                                                  |
                                      legacy lowering adapter
                                                  |
                                                  v
                                  BuilderV2 -> linker -> verifier
```

The package-level path wraps the same proof objects in an `AuthoringBundle`:

```text
base TheoryInterface + AuthoringBundle -> ElaboratedBundle -> LoweredUnit
                                                -> VerifiedArtifact
                                                -> explicit admission
                                                -> new TheorySpec/Interface
```

## Evidence used for this draft

This draft combines four evidence sources.

1. Project 021 and its direct design dependencies:
   [Authoring](../references/005-authoring.md),
   [BuilderV2](../references/009_builder-v2.md), and
   [Foundation Scope](../references/010-foundation-scope.md).
2. The three task shapes in
   [`proof-lab`](https://github.com/epistemic-frontier/proof-lab): textbook
   proof construction, Sheridan formalization, and finite-model research.
3. Historical package failures and maintenance costs in
   [`metamath-logic`](https://github.com/epistemic-frontier/metamath-logic) and
   the special foundation boundary in
   [`metamath-prelude`](https://github.com/epistemic-frontier/metamath-prelude).
4. The module, naming, and public-surface experiments in
   [`partition`](https://github.com/epistemic-frontier/partition), especially
   the
   [structural experiment](https://github.com/epistemic-frontier/partition/blob/main/reports/logic/structural-experiment.md),
   [curated API report](https://github.com/epistemic-frontier/partition/blob/main/reports/logic/consolidated-curated.md),
   [naming report](https://github.com/epistemic-frontier/partition/blob/main/reports/logic/naming.md),
   and
   [external-usage report](https://github.com/epistemic-frontier/partition/blob/main/reports/logic/external-usage.md).

The partition experiment is particularly important: its K=14 grouping is a
useful implementation layout, while the K=37 regions are useful search
features. Neither is a stable author-facing namespace. Original Metamath
labels, curated public policy, and semantic topics have different jobs and
must remain separate.

## Scope of v0.1

v0.1 is intended to answer one question with real evidence:

> Can a small typed semantic kernel remove repetitive proof plumbing for both
> humans and agents while preserving package interfaces, Metamath output, DV
> behavior, and verifier authority?

### Included

- stable semantic references for public sorts, constructors, assertions, and
  theory profiles;
- immutable typed terms;
- static assertion signatures, including mandatory DV and binder contracts;
- a read-only `TheoryInterface` and `CatalogView`;
- immutable proof draft state with goals, hypotheses, steps, and holes;
- one deterministic assertion-application operation;
- finalization into an explicit proof DAG;
- a concise Python facade and a typed action/query projection with identical
  semantics;
- structured, deterministic diagnostics;
- declarative library objects sufficient to make declarations, exports,
  coverage, catalogues, and lowering derive from one source;
- an additive adapter to current BuilderV2/linker/verifier infrastructure;
- a documented experiment across all three `proof-lab` workflows.

### Not included

- a frozen canonical JSON format or public schema migration policy;
- separate compilation, cross-process linker objects, or interface caches;
- a general tactic engine or heuristic proof search;
- natural-deduction syntax, assumption discharge, or a `show`/`have` language;
- a compact proof-script grammar;
- theorem ranking or a unifiability index;
- LaTeX and model-context exporters;
- MCP, JSON-RPC, editor, or model-specific transports;
- full transaction services such as CAS commit, fork, rollback, and merge;
- automatic definition-conservativity certification;
- unrestricted agent creation of languages, axioms, dependencies, exports, or
  releases;
- replacement of BuilderV2, the linker, or verifier aggregation;
- treating partition's generated modules as the public API.

The public semantic types must be designed so these features can be added
without changing proof meaning, but v0.1 does not claim to implement them.

## Inherited frozen backend boundaries

v0.1 adds an authoring layer; it does not reopen the BuilderV2 v1 contract.

- Each package keeps one `build(ctx)` entrypoint.
- BuilderV2 and linker truth remains process-local `SymbolId` after the final
  semantic binding step.
- BuilderV2 LIR and emitted `.mm` remain canonical ASCII. Unicode and other
  notations are authoring/display projections, with names mappings preserved in
  the normal names artifact.
- Existing automatic `$f` behavior and foundation-owned `$f` reuse remain in
  force.
- The linker continues to own scope, relocation, cross-unit order, and access
  control; authoring order is only deterministic input.
- Integration is additive. Existing packages can migrate one declaration or
  module slice at a time without replacing BuilderV2 or changing verifier
  authority.

`LanguageInterface` is authoring truth for parsing, typing, and display. It is
not a parallel linker symbol table and cannot bypass the final binding step.

## Boundaries that must not be collapsed

### Authoring stage is not workflow state

The semantic pipeline has these states:

```text
source metadata -> Draft -> Elaborated -> Lowered -> VerifiedArtifact
```

`proof`, `formalize`, and `discover` describe how a task reaches those states.
They do not alter the meaning of `Term`, `AssertionSignature`, or
`ElaboratedProof`.

### Verification state is not admission state

A theorem may be:

- syntactically drafted;
- completely elaborated;
- successfully lowered;
- verifier-accepted;
- admitted into a package build;
- exported by a public manifest;
- released.

These are distinct facts. A `proof-lab` research candidate can be elaborated or
even independently checked without being admitted to a released package. A
task registry flag such as `buildable` must not silently stand for all of
these states.

### Mathematical identity is not provenance

Source citation, author identity, model version, prompts, timestamps, research
candidate IDs, and action logs are valuable records. They MUST NOT affect term
equality, assertion identity, semantic digests, or verifier results.

### Public API is not implementation layout

Partition reveals four different layers:

| Layer | Stable purpose | v0.1 representation |
| --- | --- | --- |
| Public API | compatibility and exact reference | canonical label, `SemanticId`, explicit public manifest |
| Discovery | human and agent navigation | topics, tags, curated core, generated docs/JSONL |
| Search regions | machine ranking and retrieval | advisory, versioned index; never identity |
| Implementation modules | ownership, build order, refactoring | internal unit metadata; never author import syntax |

Moving `syl` between K=14 modules MUST NOT change its public identity. A K=37
cluster number MUST NOT appear in a proof. `registry` means all known
declarations; it is not an export policy. A linker export is a mechanical
cross-unit capability; it is not automatically a semver public API.

## Requirements from the three Proof Lab workflows

The
[`proof-lab` project plan](https://github.com/epistemic-frontier/proof-lab/blob/main/PROJECT_PLAN.md)
already separates three workflows. Their different needs shape the API without
changing its semantic core.

| Workflow | Primary authoring need | Data that remains outside mathematical IR |
| --- | --- | --- |
| Task 1 `proof` | apply known assertions inside a fixed statement, hypothesis set, profile, and lemma allowlist | task status, expected-answer join, admission policy |
| Task 2 `formalize` | declare a local vocabulary/theory, record holes, and prove against an exact assumption profile | source lock, claim mapping, interpretation audit, evidence status |
| Task 3 `discover` | turn an explicitly promoted candidate into an ordinary formal draft, if formal prerequisites permit | experiments, solver runs, bounded results, inconclusive outcomes, promotion review |

Task 1 provides three useful proof-author canaries:

- [repeated MP](https://github.com/epistemic-frontier/proof-lab/blob/main/src/proof_lab/tasks/task_01_textbook/proofs/double_modus_ponens.py);
- [imported lemma plus MP](https://github.com/epistemic-frontier/proof-lab/blob/main/src/proof_lab/tasks/task_01_textbook/proofs/modus_tollens.py);
- [exact imported reference](https://github.com/epistemic-frontier/proof-lab/blob/main/src/proof_lab/tasks/task_01_textbook/proofs/linearity_import.py).

The proofs themselves are compact. The surrounding task builder still performs
reflection loading, dependency/catalogue closure, dependency export and alias
merge, coverage, floating-variable reconstruction, lowering, and root export.
v0.1 should remove this compatibility plumbing from the proof author.

Task 2 additionally requires claim, formula, source occurrence, and assertion
identities to remain distinct. It needs persistent holes and exact theory
profiles, but a hole cannot lower. The core and Extensionality extension must
have distinct profile digests and actual assumption closures. Source and
interpretation records are digest-linked provenance references rather than
fields in `Term` equality.

Task 3 confirms the outer trust boundary. A computationally certified,
counterexample, bounded-frontier, restricted, or audited-inconclusive result
may legitimately close a research task without creating any theorem. Research
artifacts are never proof premises. External promotion is the first operation
that creates a formal `TheoremDraft` and `AssertionId`; finalization preserves
that ID.

Across all tasks, Python registry entries, task YAML, bundle roots, proof names,
emitted labels, verification, admission, and public support are separate views
or states. YAML may reference stable IDs and CI should check the joins, but
changing a YAML status cannot grant admission or authoring capability.

## Role and capability model

The API MUST use explicit capabilities, not infer authority from whether the
caller is human or an agent.

Suggested capability atoms are:

```text
READ_THEORY
CREATE_PROOF_DRAFT
EDIT_PROOF
FINALIZE_PROOF
DECLARE_ASSERTION
EDIT_THEOREM_SIGNATURE
DECLARE_DEFINITION
DECLARE_LANGUAGE
DECLARE_AXIOM
CHANGE_PUBLIC_MANIFEST
CHANGE_DEPENDENCIES
CHANGE_THEORY_PROFILE
PUBLISH
FOUNDATION_SCOPE
```

Capabilities are a set, not a numeric ladder. Permission to declare a theorem
does not imply permission to declare an axiom; permission to edit exports does
not imply permission to publish.

| Role projection | Expected v0.1 surface | Explicitly unavailable by default |
| --- | --- | --- |
| Human proof author | read interface, start proof, `use`, inspect, finalize | language/axiom/export/dependency mutation |
| Agent proof author | same operations as typed actions and queries | arbitrary Python execution and all library mutations |
| Human library author | declarative language/assertion/theory objects plus proof facade | foundation ambient scope unless separately granted |
| Agent library author | read, propose, validate, and diff the same declaration objects | axiom, dependency, export, and publish actions unless separately granted |

Foundation authoring is a separate privileged boundary, not merely the most
powerful ordinary library role. `metamath-prelude` owns top-level ambient `$f`
state, and the standard prelude emits no `$d` statement at all. Ordinary
library APIs MUST NOT reproduce that ambient privilege. `FOUNDATION_SCOPE` is
a backend-owned package capability; no ordinary human or agent action can use
it to create a second foundation.

## Public semantic model

### Stable identity

Public objects use `SemanticId`; backend objects use process-local `SymbolId`.
The two MUST NOT be confused.

Example IDs are:

```text
metamath-logic/propositional#sort:wff
metamath-logic/propositional#constructor:imp
metamath-logic/propositional#assertion:syl
proof-lab/task-01#assertion:double-modus-ponens
```

The exact serialized spelling remains experimental in v0.1, but these
properties are normative:

- identity is independent of file path, Python object identity, import order,
  implementation module, process-local allocation, and presentation alias;
- package version and interface digest are requirements on an identity, not
  parts of the identity itself;
- moving a declaration is not a rename;
- a public rename requires an explicit alias/deprecation record;
- short handles are session-local conveniences and are reified to a full ID
  before elaboration;
- canonical Metamath label lookup is exact and case-sensitive.

The recommended public access projections follow partition's result:

```python
logic.core.syl                    # small reviewed convenience surface
logic.by_label["syl"]             # exact complete label access
logic.topics.propositional        # discovery, not identity
catalog.assertion(full_id)        # stable protocol access
```

Labels that are not valid Python identifiers remain fully accessible through
`by_label`. Only a small curated core receives convenience attributes.

### Variables and same-spelling isolation

Variable spelling is presentation, not identity. v0.1 distinguishes at least
two kinds of persisted variable reference:

```python
DeclaredVariableId(owner=language_or_theory_id, local_key="x")
SchemaVariableId(owner=assertion_id, local_key="x")
```

The first represents a declared vocabulary/source variable identity where one
is required. The second is an assertion-local schema slot. `Term` variable
nodes and DV endpoints MUST carry the same variable-reference value.
For an assertion, every `VariableDecl.id` is its `SchemaVariableId`; the
declaration also carries the sort and preferred display name.

At runtime, a scoped binding layer maps these references to one build's
`SymbolId` space. Distinct live identities and contracts MUST NOT collide, but
non-overlapping Metamath scopes may legitimately reuse a final token. Two
imports may share backend identity only when they resolve to the same complete
semantic ID through import or re-export. A display or deprecation alias may
resolve to one ID; it can never equate two different IDs.

Consequently:

- two same-spelling variables that are simultaneously live under distinct
  semantic owners cannot be merged merely because both display as `x`;
- one imported variable referenced through two paths cannot be duplicated;
- deterministic alpha-renaming may change final Metamath token spelling but
  must change formula tokens and DV endpoints together;
- no process-local `SymbolId` may be serialized into `TheoryInterface`.

The current runner loads the transitive package closure into one process and
uses one build-global interner. v0.1 uses that backend and does not claim
separate compilation. The semantic API nevertheless prevents that current
implementation detail from becoming public ABI.

### Typed terms

The semantic term model is immutable and structurally comparable:

```python
VariableRef = DeclaredVariableId | SchemaVariableId

Term = Var(variable: VariableRef, sort: SortId) | App(
    constructor: ConstructorId,
    arguments: tuple[Term, ...],
    sort: SortId,
)
```

Required properties are:

- explicit sort on every node;
- structural equality and hashing include constructor and arguments;
- binder/free-variable behavior is obtained from `LanguageSpec`;
- source spans and display choices are non-semantic side information;
- strings are accepted only as boundary conveniences and are parsed, resolved,
  normalized, and typed before proof reasoning;
- Unicode, ASCII, and LaTeX are renderings of the same term.

The parser may accept compatibility aliases such as `->`, but the authoring
formatter emits one repository-canonical Unicode form and lowering emits one
canonical ASCII Metamath form. Parser acceptance, repository style, and
backend serialization are three distinct policies.

### Language declarations (amended boundary)

`LanguageSpec` is the authoritative declaration of semantic sorts and
constructors. A constructor declaration minimally contains:

```text
SemanticId
input and output sorts
binder/free-variable behavior when applicable
```

`NotationSpec` separately contains accepted aliases, preferred authoring
notation, precedence and associativity. `MetamathLanguageBinding` separately
contains canonical token layout and syntax-assertion linkage. Both reference
the same stable `ConstructorId`; neither repeats its signature. v0.1 need not
implement every formatter or binder form, but these layers MUST NOT become
independent declarations of the same semantic fact.

### Assertion signature

`AssertionSignature` is static consumer-facing data. Reading it MUST NOT
execute a proof body.

```python
@dataclass(frozen=True)
class AssertionSignature:
    id: AssertionId
    canonical_label: str
    kind: AssertionKind
    schema_variables: tuple[VariableDecl, ...]  # mandatory `$f` order
    premises: tuple[JudgmentPattern, ...]       # mandatory `$e` order
    conclusion: JudgmentPattern
    mandatory_dv_pairs: frozenset[DistinctPair]
    binder_constraints: tuple[BinderConstraint, ...]
```

Assertion kind and visibility are separate. The partition reports call the
first dimension “role”; this API uses `AssertionKind` to avoid confusing it
with human/agent author roles. Suggested kinds include `syntax`, `axiom`,
`definition`, `theorem`, and `support_lemma`. Suggested declaration/interface
visibility values include `public`, `package_internal`, and `private`.
Visibility is policy around a signature, not part of its mathematical content.
A support lemma may be public; an important theorem may intentionally remain
package-internal.

Both mandatory floating-variable order and essential-hypothesis order are
contract data. Reordering either changes the lowered application ABI and the
interface digest.

### Assertion declaration variants

The trust boundary MUST be represented by distinct types:

```python
AuthoringDeclaration = (
    SyntaxDecl
    | DefinitionDecl
    | AxiomDecl
    | TheoremDraft
    | TheoremDecl
)

FinalDeclaration = SyntaxDecl | DefinitionDecl | AxiomDecl | TheoremDecl
```

In particular, `proof=None` MUST NOT mean “emit an axiom.”

- `AxiomDecl` requires the `DECLARE_AXIOM` capability and explicit assumption
  provenance.
- `DefinitionDecl` requires `DECLARE_DEFINITION` and an explicit trust/admission
  decision. Because v0.1 does not certify conservativity, a definition without
  a proof is trusted input and is not automatically safer than an axiom.
- `TheoremDraft` contains a `ProofDraft` and may contain holes. It cannot be
  lowered, exported, or treated as verified.
- `TheoremDecl` contains a `ProvedImplementation` whose elaborated root matches
  the declared signature and whose replay context preserves active DV data.
- unsupported or failed proof construction remains a diagnostic; it never
  changes the declaration variant.

An `AuthoringBundle` may contain `TheoremDraft`; a lowerable candidate theory
revision may contain only `FinalDeclaration`. It becomes an admitted
`TheorySpec` and may produce a consumer interface only after normal lowering,
verification, and authorized admission. This makes it impossible for an
unfinished theorem to enter an interface merely because both objects share a
base class.

The provider-side implementation record also carries the full replay context:

```python
@dataclass(frozen=True)
class AssertionReplayContext:
    local_variables: tuple[VariableDecl, ...]
    active_dv_pairs: frozenset[DistinctPair]

AssertionImplementation = (
    ProvedImplementation
    | ImportedImplementation
    | ExplicitTrustedImplementation
)
```

Each tagged implementation contains a signature and replay context.
`ProvedImplementation` contains `ElaboratedProof`; `ImportedImplementation`
contains checked imported proof data; `ExplicitTrustedImplementation` names
its syntax/axiom/definition trust kind and justification. There is no nullable
proof field and therefore no “missing proof means axiom” fallback.

`mandatory_dv_pairs` is derived from replay context and the signature's
mandatory variables. Formula, `$f`/`$e` order, active DV, mandatory DV,
proof-reference template, and emission all compile from the same
declaration/implementation record; no parallel hand-authored token schema is
permitted.

### Distinct-variable contract

The API preserves the distinction established in Project 021:

- `active_dv_pairs` is the full pair relation active at a provider assertion's
  original proof site. It is provider implementation/replay context.
- `mandatory_dv_pairs` is the subset over mandatory assertion variables. It is
  the public application contract.

`AssertionSignature` exposes only `mandatory_dv_pairs`. A provider's raw `$d`
statement is not a module export. When a consumer applies an assertion, the
elaborator substitutes the signature and checks the resulting requirement
against the consumer theorem's own explicit DV context.

For imported `set.mm`, the frontend MUST snapshot the complete scoped `$d`
environment at each assertion and expand it into exact pairs before flattening
the assertion into an independent declaration. Pair sets MUST NOT be widened
by clique or transitive-closure logic.

Formula variables and DV endpoints MUST pass through the same semantic binding
and relocation map. Any alpha-renaming must update both. This is the concrete
compatibility condition between modules and `$d`; the final independent
Metamath verifier remains the semantic backstop after flattening.

### Theory specification and consumer interface

`TheorySpec` is a library-author object. `TheoryInterface` is its immutable,
read-only consumer projection.

```python
@dataclass(frozen=True)
class LanguageInterface:
    id: LanguageId
    interface_digest: Digest
    sorts: Mapping[SortId, SortSignature]
    constructors: Mapping[ConstructorId, ConstructorSignature]
    binder_rules: Mapping[ConstructorId, BinderRule]
    canonical_token_layouts: Mapping[ConstructorId, TokenLayout]
    accepted_aliases: Mapping[str, SemanticId]

@dataclass(frozen=True)
class TheorySpec:
    id: TheoryId
    language: LanguageSpec
    imports: tuple[InterfaceRequirement, ...]
    declarations: tuple[FinalDeclaration, ...]
    public_manifest: PublicManifest
    profiles: tuple[TheoryProfile, ...]

@dataclass(frozen=True)
class TheoryInterface:
    id: TheoryId
    interface_digest: Digest
    foundation_digest: Digest
    language: LanguageInterface
    assertions: Mapping[AssertionId, AssertionSignature]
    assumption_closures: Mapping[AssertionId, frozenset[AssertionId]]
    public_manifest: PublicManifest

@dataclass(frozen=True)
class TheoryAnalysis:
    theory_interface_digest: Digest
    analysis_digest: Digest
    direct_dependencies: Mapping[AssertionId, tuple[AssertionId, ...]]
    discovery: DiscoveryProjection
```

The interface digest covers language contracts, assertion signatures, public
policy, foundation state, and assumption/trust contracts. It does not cover
file layout, direct proof dependencies, timestamps, provenance, docs rendering,
or search ranking, and it never includes `SymbolId`. This permits a proof
refactor with the same statement and assumption closure to leave public ABI
unchanged. `TheoryAnalysis` is a digest-linked, regenerable sidecar.

An `InterfaceRequirement` keeps package resolution concerns separate:

```python
@dataclass(frozen=True)
class InterfaceRequirement:
    theory_id: TheoryId
    version_constraint: VersionConstraint
    expected_interface_digest: Digest | None
    local_alias: str | None
```

`local_alias` is session/package syntax and does not enter semantic identity.
Distribution name and Python import path are resolver metadata rather than
assertion IDs.

`TheorySpec` is the single source from which the framework derives:

- registry and exact label map;
- deterministic declaration dependencies and ordering;
- declared and emitted proof coverage;
- package-internal linker exports;
- public manifest;
- curated core and discovery projections;
- interface digests and compatibility diffs;
- lowering inputs and generated catalogue data.

No generated projection becomes a second editable source of truth.

`CatalogView` is a read-only, capability-filtered view over one or more
interfaces and optional analysis sidecars. Its minimum v0.1 surface is:

```python
catalog.assertion(assertion_id) -> Result[AssertionSignature, Diagnostic]
catalog.by_label(exact_label) -> Result[AssertionSignature, Diagnostic]
catalog.resolve_exact(reference) -> Result[SemanticId, Diagnostic]
catalog.dependencies(assertion_id) -> Result[tuple[AssertionId, ...], Diagnostic]
catalog.assumptions(assertion_id) -> Result[frozenset[AssertionId], Diagnostic]
catalog.render(term, style="unicode") -> Result[str, Diagnostic]
catalog.topic(topic_id) -> Result[tuple[AssertionId, ...], Diagnostic]
```

`resolve_exact` may accept a short name only when the current import scope has
one result. A full `SemanticId` is never ambiguous; ambiguity belongs only to a
scoped short reference. It is a diagnostic, not an ordering rule. Topic and
curated core queries are discovery projections and return stable IDs before
any proof action occurs.

### Theory profiles

A `TheoryProfile` fixes the assumptions and interfaces available to a proof:

```python
@dataclass(frozen=True)
class TheoryProfile:
    id: TheoryProfileId
    requirements: tuple[InterfaceRequirement, ...]
    allowed_assumptions: frozenset[AssertionId]
    policy: ProfilePolicy
    digest: Digest
```

This supports the Sheridan requirement that a core theory and an extensional
extension have different assumption closures. A proof cannot silently import
an axiom outside its profile. Changing profile is an explicit operation and
changes the elaboration input digest. `proof-lab` may use the profile reference
to select a separate evidence/artifact namespace, but that namespace is
workflow policy and is not part of the profile's mathematical semantics.

The actual transitive assumption closure, not merely direct proof references,
is compared with `allowed_assumptions`. Profile requirements may only select,
pin, or narrow interfaces already available through `TheorySpec.imports`; they
cannot introduce an undeclared dependency. A dependency change is a theory
patch requiring `CHANGE_DEPENDENCIES`.

## Package and draft containers

### `AuthoringBundle`

`TheorySpec` is the only authoritative package theory. `AuthoringBundle` is an
immutable draft/admission change set against a base interface, not a second
published theory:

```python
@dataclass(frozen=True)
class AuthoringBundle:
    id: BundleId
    namespace: SemanticId
    base_interface: TheoryInterfaceRef | None
    profile: TheoryProfileRef
    declarations: tuple[AuthoringDeclaration, ...]
    roots: tuple[AssertionId, ...]
    proposed_theory_patch: TheoryPatch | None
    policy: BundlePolicy
    provenance: BundleProvenance = field(compare=False)
```

Simple proof authors normally do not construct every field. A task supplies a
fixed profile, namespace, base interface, and policy; the facade creates one
`TheoremDraft`, and `proposed_theory_patch` is absent. A library-author bundle
may propose dependency, declaration, profile, or manifest changes, but only an
explicit admission operation with the corresponding capabilities can apply the
patch and produce a new `TheorySpec` revision.

Declaration bodies occur only in `declarations`. `proposed_theory_patch`
contains import/profile/manifest deltas and references declaration IDs; it
cannot carry a second editable copy of a declaration.

Bundle roots drive the selected link/lowering closure. All admitted theorem
declarations, including those not selected as roots, remain in the validation
and coverage set. Roots therefore cannot hide a broken unreferenced theorem.
Public export remains `TheorySpec.public_manifest` policy, not an accidental
consequence of being a bundle root. A task builder must not separately scan
proof objects, maintain a second dependency catalogue, reconstruct floating
variables, and then list emitted roots again.

The downstream product names mean:

- `ElaboratedBundle`: every selected declaration and proof reference is typed,
  resolved, complete, and associated with its profile and interface digests;
- `LoweredUnit`: target-specific scoped IR ready for the existing BuilderV2 and
  linker contract, including `$f`/`$e`/`$d`, proof order, and relocation data;
- `VerifiedArtifact`: emitted Metamath plus names, interface/build reports, and
  verifier evidence. It is an output and cannot become a trusted proof input.

Verification does not mutate the bundle into `TheorySpec`. Admission consumes
the verified result and an authorized theory patch to create a new immutable
theory revision.

### `ProofDraft`

```python
@dataclass(frozen=True)
class ProofDraft:
    proof_id: ProofId
    theory_digest: Digest
    draft_signature: AssertionDraftSignature
    input_lock_digest: Digest
    hypotheses: tuple[HypothesisStep, ...]
    steps: tuple[DraftStep, ...]
    open_goals: tuple[Goal, ...]
    local_dv_pairs: frozenset[DistinctPair]
    provenance: ProofProvenance = field(compare=False)
```

A draft may contain typed holes and unresolved obligations. It can be rendered,
reviewed, or persisted experimentally. It cannot be finalized while any hole,
unknown reference, type error, ambiguity, missing constraint, or stale
interface remains.

`draft_signature` fixes the conclusion, ordered essential hypotheses, sorted
variables, and local constraints for the lifetime of an ordinary proof
session. Editing it requires `EDIT_THEOREM_SIGNATURE`, creates a new input-lock
digest, and invalidates proof state that depended on the old obligation.

All fields named `semantic_digest`, `interface_digest`, `analysis_digest`, or
`input_lock_digest` are derived and validated outputs, never caller-selected
identity. Dataclass examples that carry provenance use an explicit semantic
projection for equality and hashing; `field(compare=False)` is illustrative of
that rule, not a promise that Python dataclasses are the final implementation.
Mappings, sets, DV pairs, and constraints are canonically sorted by their
stable IDs before hashing. Source spans, display metadata, authorship,
diagnostic prose, and the mechanics of constraint evidence are excluded; the
normalized fact that required constraints were satisfied remains semantic.

### `ElaboratedProof`

Every elaborated step records all information that was inferred:

```python
@dataclass(frozen=True)
class ElaboratedStep:
    id: StepRef
    assertion: AssertionId
    premises: tuple[StepRef, ...]
    substitution: Substitution
    result: Term
    satisfied_constraints: tuple[ConstraintEvidence, ...]

@dataclass(frozen=True)
class ElaboratedProof:
    signature: AssertionSignature
    steps: tuple[ElaboratedStep, ...]
    root: StepRef
    replay_context: AssertionReplayContext
    dependency_closure: tuple[AssertionId, ...]
    assumption_closure: tuple[AssertionId, ...]
    semantic_digest: Digest
```

The elaborated DAG uses stable step references, not Python object identity.
Generated step IDs need only be deterministic within a proof snapshot in v0.1;
declaration IDs must be stable across snapshots. The replay context preserves
proof-local/auxiliary variable declarations and the full `active_dv_pairs`;
finalization never discards provider DV context merely because only mandatory
pairs appear in the public signature.

## Proof operation semantics

### Core operation

The minimal semantic operation is assertion application:

```python
result = apply_assertion(
    state,
    assertion=assertion_id,
    premises=(step_ref_1, step_ref_2),
    target=None,
    subst=None,
)
```

It follows these rules:

1. Resolve `assertion` to exactly one `AssertionSignature` in the fixed
   `TheoryInterface` and profile.
2. Match ordered premises against ordered essential hypotheses.
3. Infer only local, unique substitutions.
4. Treat an explicit `target` or partial `subst` as a constraint that must agree
   with the solution. It may resolve otherwise underdetermined information but
   can never override a uniquely inferred value.
5. Reject incompatible or multiply valid substitutions as structured
   obligations or diagnostics.
6. Compute the result term; never trust a caller-supplied result.
7. Check sort, binder, capture, and DV constraints in the consumer context.
8. Append one fully reified step and return a new immutable state.

The operation does not search for a theorem, choose premises heuristically, or
silently pick the first unifier. Discovery may suggest candidates, but the
proof-changing request names one stable assertion ID.

### Finalization

```python
proof = finalize(state, root=step_ref)
```

Finalization succeeds only if:

- the root exists and exactly matches the declared goal;
- every step is typed and fully elaborated;
- every referenced assertion is permitted by the profile;
- every DV/binder/capture constraint is satisfied;
- every hole and obligation is closed;
- the referenced interface digests are current;
- the caller has `FINALIZE_PROOF`.

Finalization creates `ElaboratedProof`; it does not claim Metamath verification.
It copies the draft's exact local/active DV relation and auxiliary variables
into `AssertionReplayContext`. A theorem declaration wraps this result in
`ProvedImplementation`. Verification occurs after lowering and linking.

## Human projection

The human facade minimizes derivable ceremony while remaining an ordinary
projection of the core requests:

```python
def prove_double_mp(p: HumanProof) -> None:
    h_phi = p.hyp("h_phi")
    h_psi = p.hyp("h_psi")
    h_nested = p.hyp("h_nested")
    mp = logic.by_label["ax-mp"]

    mid = p.use(mp, h_phi, h_nested)
    out = p.use(mp, h_psi, mid)
    p.qed(out)
```

The author does not provide:

- an internal Metamath step label;
- a repeated instantiated result formula;
- process-local symbols;
- floating-variable maps;
- dependency closure or export order;
- inferred substitutions that are unique.

When inference is underdetermined, the facade requests the smallest explicit
addition:

```python
step = p.use(assertion, premise, target="φ -> ψ")
# or
step = p.use(assertion, premise, subst={schema.x: term})
```

The facade returns `StepRef`-backed handles. It may display terms and source
locations for convenience but cannot alter core semantics.

## Agent projection

The agent API uses typed, bounded requests against immutable state. It is a
projection of the same operations, not an RPC-specific second IR.

Minimal proof-changing actions are:

```text
StartProof
AddHole
ApplyAssertion
FillHole
FinalizeProof
```

`StartProof` receives a fixed theorem obligation and materializes its declared
hypotheses as initial steps. A simple proof author cannot add a new hypothesis
or change the conclusion after the proof starts. Creating or editing an
assertion signature is a library-author operation with a different capability.

Minimal read-only queries are:

```text
InspectState
InspectAssertion
ResolveExactReference
ParseTerm
RenderTerm
```

An illustrative request is:

```json
{
  "action": "ApplyAssertion",
  "assertion_id": "metamath-logic/propositional#assertion:syl",
  "premise_step_ids": ["step:h1", "step:h2"],
  "target": null,
  "subst": null
}
```

v0.1 may expose this through Python dataclasses before freezing JSON. The same
request value must produce the same semantic result regardless of transport or
model. A failed action returns the original state unchanged.

Search, ranking, compact handles, and context summaries are advisory query
features. Before mutation, every suggestion is resolved to a full stable ID
and checked against the current interface digest.

## Diagnostics

Diagnostics are part of the public protocol. They MUST be structured,
deterministic, and useful without parsing an exception string.

```python
@dataclass(frozen=True)
class AuthoringDiagnostic:
    code: DiagnosticCode
    phase: AuthoringPhase
    message: str
    subject: SemanticId | StepRef | None
    expected: DiagnosticValue | None
    supplied: DiagnosticValue | None
    candidates: tuple[SemanticId, ...]
    obligations: tuple[Obligation, ...]
    source_span: SourceSpan | None
    state_unchanged: bool
```

The candidate ordering and typed payload are deterministic protocol data; they
need not enter mathematical proof identity. Prose wording may evolve.
Minimum stable codes include:

```text
REFERENCE_UNKNOWN
REFERENCE_AMBIGUOUS
INTERFACE_STALE
CAPABILITY_DENIED
PROFILE_VIOLATION
SORT_MISMATCH
PREMISE_MISMATCH
SUBSTITUTION_UNDERDETERMINED
SUBSTITUTION_CONFLICT
DV_UNSATISFIED
BINDER_CAPTURE
DRAFT_INCOMPLETE
DECLARATION_CONFLICT
LOWERING_UNSUPPORTED
VERIFICATION_FAILED
```

Discovery and build orchestration MUST NOT swallow an exception and omit a
declaration or proof. A failure is either returned as a diagnostic or aborts
the requested build according to explicit policy.

## Module, linker, and include compatibility

Metamath `$[ file $]` is textual inclusion. It provides neither ownership nor
an interface. ProofScaffold modules add scope, ownership, explicit exports,
relocation, and dependency policy, but must ultimately flatten to ordinary
Metamath semantics.

The authoring contract with the current linker is:

1. `TheoryInterface` references semantic identities; it does not expose unit
   numbers, partition modules, relocation slots, or `SymbolId`.
2. A runtime binding phase maps all required interfaces into one build-global
   interner and records an origin-aware relocation.
3. That mapping preserves identity alignment across formulas, floating
   hypotheses, proofs, and DV endpoints.
4. Ordinary local `$f`, `$e`, and `$d` state closes with the provider unit.
   Explicitly exported vocabulary and assertion signatures cross interfaces;
   foundation-owned ambient `$f` is the one privileged special case.
5. Current linker conformance level 1 checks assertion export visibility and
   ordinary hypothesis ownership. It does not prove declared direct-import
   enforcement because `ProofUnitIR` currently has no explicit imports field.
6. The transient monolith is verified by a verifier that knows nothing about
   ProofScaffold modules.

This establishes compatibility for the current one-process build. It does not
establish serialized object linking or independent-interner composition.
Before those claims are made, ProofScaffold needs a canonical
`TheoryInterface` codec, stable origin identities, scoped lowered objects,
relocation records, and a cross-process round-trip gate.

Before v0.1 claims direct-edge enforcement, the semantic compiler and lowered
unit contract must both carry explicit imports and test them independently of
transitive availability.

## Public surface, discovery, and generated reports

Partition's long-tail usage data supports a small curated core, but frequency
is only a review-priority signal. It MUST NOT automatically make a theorem
public.

The required policy is:

- canonical label plus `SemanticId` is the exact identity layer;
- `PublicManifest` is the reviewed compatibility policy;
- `core` is a small convenience projection of that manifest;
- `by_label` provides exact access to all permitted labels;
- topics and tags are multi-valued discovery metadata;
- implementation module and search-region assignments are replaceable;
- human Markdown and agent JSONL catalogues are derived from the same data;
- ABI and manifest diffs are generated and reviewed during releases.

Build statistics are also derived artifacts. Declared, elaborated, lowered,
emitted, verifier-accepted, and declared-but-unemitted counts belong in a
machine-generated `BuildReport`; they must not be independently copied into
multiple README files.

## Historical failures mapped to API requirements

The point of reviewing past issues is not to hide implementation bugs behind a
new facade. Each failure shape becomes an API invariant or gate.

At this review, `metamath-prelude` has no GitHub issues. `metamath-logic` has
closed issues #3 and #4 and open issues #5 and #6. Prelude evidence below comes
from its ownership/foundation migration history; an empty issue tracker is not
evidence that the API boundary needs no tests.

| Evidence | Failure shape | v0.1 prevention |
| --- | --- | --- |
| [`metamath-logic` #3](https://github.com/epistemic-frontier/metamath-logic/issues/3) | removed or unregistered lemmas remained referenced; multiple Metamath verifiers accepted an internally consistent but incomplete emitted artifact | all admitted declarations are validated and covered; selected roots only derive link closure; unknown references fail; declared-but-unemitted must be zero |
| [`metamath-logic` #4](https://github.com/epistemic-frontier/metamath-logic/issues/4) | an MP antecedent mismatch was detected but a permissive wrapper skipped the failed proof and continued | one typed `ApplyAssertion`; no safe-skip path; failed action is unchanged state plus diagnostic; build fails closed |
| [`metamath-logic` #5](https://github.com/epistemic-frontier/metamath-logic/issues/5) | predicate axiom schemas were duplicated between token emission and authoring expressions, allowing formula drift and an omitted `ax-5` `$d x ph` contract | one static `AssertionDecl`; signature, DV, emission, catalogue, and proof template derive from it |
| [`metamath-logic` #6](https://github.com/epistemic-frontier/metamath-logic/issues/6) | compatibility syntax and repository-canonical Unicode style became mixed in static formulas | accepted parser aliases, canonical authoring formatter/lint, and canonical ASCII lowering are separate policies |
| `metamath-logic` documentation drift | emitted-proof counts were copied into several documents and diverged | generated `BuildReport` and catalogue are the sole statistics source |
| current `proof-lab` Task 1 builder | reflection, manual dependency closure, alias merge, coverage, floating map, lowering, and root export repeat the same facts | fixed `TheoryInterface` plus bundle roots derive closure, lowering, coverage, and export |
| current package registries | import-time mutable discovery can depend on execution order or silently omit declarations | immutable `TheorySpec`; static signatures; deterministic derivation; no exception swallowing |
| current proof step objects | repeated labels/results and Python identity are used as proof references | caller omits result/label; elaborator computes them; DAG uses stable `StepRef` |
| historical global `hyp` label collision | local proof names were treated as globally unique emitted labels | hypothesis and step names are theorem-local; lowering scopes or deterministically generates final labels |
| repeated registry keys, proof homes, shims, and catalogues | one theorem move required coordinated edits across several editable inventories | declaration and implementation have one owner; registry, re-export, catalogue, coverage, and ABI are derived |
| predicate structures represented set variables, classes, and wffs as one WFF shape | high proof coverage did not prove that the authoring type model was faithful | distinct first-class sorts and static constructor signatures; DV endpoints use typed variable identity |
| current runtime interner boundary | module-local same-spelling symbols can be confused with semantic public identity | public semantic/variable references; scoped collision-checked origin binding; formula/DV alignment; no serialized `SymbolId` |
| handwritten `origin_module_id` and prelude token ownership | prelude removed logic vocabulary, while logic-side builtins could still intern logic tokens under a reserved prelude module ID; semantic identity, declaring unit, and package ownership were conflated | separate vocabulary identity, declaring unit, and export owner; authors cannot write reserved owner strings and obtain imported symbols from typed dependency interfaces |
| distribution name, Python import name, and dependency alias | raw strings at call sites made package resolution and interface selection fragile | one manifest declares package ID, local typed alias, version requirement, and interface digest |
| legacy `raw` proof construction | an escape hatch could bypass lowerability and faithful proof semantics | no exportable raw proof in v0.1; any future unsafe/trusted escape is explicit, privileged, and carries an obligation |
| oversized package `build.py` orchestration | build files accumulated token interning, `$f`/axiom emission, filters, coverage, and hand exports | compile typed declarations through the BuilderV2 LIR/`ProofUnitIR` path; `build(ctx)` assembles declarations and invokes the compiler |
| prelude foundation scope | top-level `$f` ownership can be mistaken for an ordinary package facility | explicit `FOUNDATION_SCOPE`; read-only foundation interface; ordinary packages cannot synthesize ambient state |

## Trust, assumptions, and provenance

The following transitions are explicit and independently reviewable:

```text
research evidence --promotion--> formal draft --finalize--> elaborated proof
       --lower/link/verify--> verified artifact --admit--> package root
       --public manifest--> supported API --release--> distribution
```

No arrow is implied by the previous state.

- A research artifact can suggest a term or proof action, but cannot be a
  trusted proof input.
- Promotion creates a new immutable formal identity and records provenance.
- Axiom declaration is an explicit privileged variant, never a fallback from
  unsupported proof work.
- The actual assumption closure is calculated from the elaborated proof and
  compared with the selected theory profile.
- Admission into a package uses an explicit allowlist independent of task YAML
  and discovery registries.
- Public support uses `PublicManifest`, not “all linker exports.”

## Proof Lab experiment plan

The next implementation phase should test the draft, not merely demonstrate
that its types can be instantiated.

### Experiment A: Task 1 simple proofs

Migrate all three existing proof shapes:

1. hypotheses plus repeated MP;
2. an imported lemma followed by MP;
3. a proof that is an exact imported assertion reference.

For each proof:

- lock the exact statement, ordered hypotheses, theory profile, and permitted
  lemma/assertion allowlist before proof actions begin;
- reject direct citation of the target theorem itself;
- construct it once through the human facade;
- replay the equivalent typed action log;
- require structurally equal canonical `ElaboratedProof` projections;
- require the same dependency and assumption closure;
- emit a structured trace joining the expected theorem, bundle root, action
  steps, and emitted label;
- lower through the existing stack and compare verifier-visible Metamath;
- remove task-local manual closure, alias, floating-map, coverage, and export
  bookkeeping that the bundle can derive.

Negative cases must include unknown and ambiguous references, premise
mismatch, underdetermined substitution, stale interface digest, and attempted
axiom declaration by a proof author. CI also joins registry, task YAML, bundle
root, proof identity, and emitted label; changing YAML status alone cannot grant
admission. Task 2 and Task 3 implementation modules remain quarantined and
unimported, and their presence must not change Task 1 emitted Metamath,
interface, or build report.

### Experiment B: Task 2 Sheridan formalization

The real Sheridan source lock, interpretation audit, and released FOL gate must
be complete before any Sheridan assertion is implemented or admitted. Until
then, v0.1 may use only a clearly named synthetic/quarantined API canary; an
attempt to start the real formalization should return the existing blocked
state rather than use a private FOL workaround.

The experiment has two parts.

1. A draft canary references digest-locked source, `ClaimId`, and interpretation
   records as non-semantic provenance and contains a local declaration, fixed
   core profile, and one typed proof hole. It is inspectable and renderable, but
   finalization and lowering fail with `DRAFT_INCOMPLETE`.
2. A positive local-theory canary declares one small assertion and completes a
   theorem through lower/link/verify. Before the Sheridan prerequisites pass,
   this positive case is synthetic and cannot claim a Sheridan result. After
   they pass, it is replaced by a source-locked real slice.

The profile tests calculate actual transitive assumption closure and enforce
the exact local-axiom allowlist. Native unique-existence's two axioms and the
expanded four-axiom formulation are mutually exclusive alternatives, not a
union. Comprehension, Foundation, Extensionality, and “every object is a set”
are rejected by the core profile. A separately reviewed Extensionality profile
has a different digest and closure; `proof-lab`, not `TheoryProfile`, selects a
separate evidence/artifact namespace from that reference.

CI joins `ClaimId` to `AssertionId`, formula digest, source occurrence, and
profile digest and rejects stale or mismatched joins. Those records remain
outside mathematical equality. Any unproved `DefinitionDecl` follows the
explicit trusted/manual admission path; its name does not imply certified
conservativity.

### Experiment C: Task 3 research promotion boundary

The current finite-model semantics/metatheory gate remains authoritative. The
experiment either verifies that promotion is rejected while that gate is
blocked or uses an explicitly synthetic promotion fixture; it does not imply
that the current `NoFiniteModel` candidate is ready for formalization.

Before promotion, a research candidate has only a research identity and no
`TheoremDraft` or `AssertionId`. External `proof-lab` promotion creates the
first formal draft and ID plus a provenance edge. Finalization preserves this
ID. Verify that:

- research and artifact paths are never imported or read by the formal builder
  as proof inputs;
- the candidate does not change the admitted package build, emitted Metamath,
  interfaces, or build report;
- it cannot appear as a proof premise or create an axiom through an unsupported
  path;
- normal elaboration, profile, lowering, admission, and verifier gates apply
  after a permitted promotion;
- computationally certified, counterexample-found, restricted, bounded, and
  inconclusive outcomes can remain final `proof-lab` outcomes without creating
  a formal assertion.

### Cross-repository freeze canaries

`proof-lab` can determine whether v0.1 is usable, but cannot by itself freeze a
general logic API. Before v0.1 is called stable, also migrate:

- one representative propositional theorem from `metamath-logic`;
- one predicate/binder/DV theorem from `metamath-logic`;
- one read-only foundation interface use from `metamath-prelude`.

The predicate canary must exercise mandatory DV application, not only carry an
unused pair in metadata.

## Acceptance gates

### Semantic gates

- Human and agent projections produce the same terms, substitutions, DAG, and
  semantic digest.
- The caller does not supply inferred result formulas or internal labels.
- Unique inference is reified; ambiguity and incompleteness fail closed.
- Unsupported proof work cannot change trust classification.
- Proof-author capabilities cannot mutate language, axioms, dependencies,
  profiles, manifests, or releases.
- Provenance changes do not change semantic digests.
- Drafts with holes cannot lower, export, or verify as theorems.

### Package/interface gates

- Exact labels and exported theorem statements remain unchanged unless an
  explicit reviewed migration says otherwise.
- Public manifest, internal exports, discovery topics, search regions, and
  implementation modules are independently diffable.
- Declaration roots derive a complete dependency closure.
- Deleting a referenced declaration fails before emission and reports the
  complete reference path.
- Duplicate assertion IDs, semantic owners, or module identities fail at
  declaration loading.
- Different theorems may reuse local names such as `hyp`, `s1`, and `result`
  without emitted-label collision.
- Declared-but-unemitted is zero for an admitted bundle.
- Declared, compiled, emitted, and exported sets appear in one machine-readable
  report; any intentional partial build names its roots explicitly.
- Generated catalogues and build counts agree with the bundle report.
- No interface contains workspace paths, object reprs, timestamps, or
  process-local `SymbolId` values.
- A logic constructor cannot acquire prelude ownership merely because a caller
  supplies a reserved module-name string.
- Distinct simultaneously live semantic-symbol or variable references cannot
  collide on one `SymbolId`, even if they share a display alias; an explicit
  import/re-export of the same complete ID is the only identity-sharing case.

### Language and declaration gates

- Set-variable, class, and wff sort misuse fails during authoring compilation.
  The predicate canary checks at least `All: SetVar × Wff -> Wff`,
  `cv: SetVar -> Class`, and `Eq`/`Elem: Class × Class -> Wff`, plus reversed or
  WFF-placeholder negative cases returning `SORT_MISMATCH`.
- Compatibility ASCII and preferred Unicode inputs lower to the same canonical
  token sequence, while strict repository style reports non-canonical source.
- An assertion's formula, ordered hypotheses, lowering template, DV contract,
  registry entry, catalogue record, and export view derive from one declaration.
- Changing one declaration's DV data or mandatory `$f` order updates its
  signature, lowering template, and interface digest together; no one-sided
  update path exists.
- A predicate DV canary such as `ax-5` emits its mandatory `$d x ph` contract;
  removing the pair makes the regression fail.
- A failed theorem is never omitted, downgraded, or reclassified as an axiom.

### Module and DV gates

The existing native linker tests remain mandatory at conformance level 1:

- consumer-local DV satisfies an imported mandatory contract;
- missing consumer-local DV is rejected;
- same-spelling module-local variables remain distinct before linking, and
  relocation keeps formula and DV endpoints aligned.

The package runner's cross-package DV gate also remains mandatory. These tests
use one build-global interner; their description MUST NOT call them an
independent-interner or separate-compilation test.

Before any future separate-compilation claim, add a fourth gate that builds
provider and consumer interfaces in independent processes, round-trips stable
semantic IDs and DV pairs byte-identically, and proves that no `SymbolId`
escapes.

This round trip is necessary but not sufficient for separate compilation.
Scoped lowered objects, relocation records, and actual cross-process positive
and negative object-link gates are also required.

The standard prelude additionally has a zero-ambient-DV gate: encountering any
foundation `$d` in a normal v0.1 build is rejected. Any future exception would
require a separately reviewed backend capability, change `foundation_digest`,
and invalidate every dependent interface.

### Verification and distribution gates

- Lower through the existing BuilderV2/linker path.
- Verify the final transient monolith with the built-in reference verifier.
- Run configured independent verifiers or report each unavailable verifier
  explicitly.
- Compare baseline and candidate emitted Metamath, names, exports, dependency
  closure, assumption closure, and verifier results.
- Test first with an editable candidate stack, then publish in dependency
  order, update exact pins and lockfiles, and replay from clean wheels before
  release acceptance.

## Migration strategy

The migration is additive.

1. Introduce immutable semantic types and a legacy adapter without changing
   BuilderV2.
2. Export read-only `TheoryInterface` fixtures for prelude and a small logic
   slice.
3. Implement the pure proof-state operations and both projections.
4. Run the three `proof-lab` experiments.
5. Run propositional and predicate/DV freeze canaries.
6. Derive registry, closure, coverage, public manifest, and catalogue from
   declarations one vertical slice at a time.
7. Deprecate duplicated package plumbing only after output and verifier parity.

Existing ASCII input, canonical emitted ASCII, public labels, exports, and
`build(ctx)` behavior remain supported during migration. Current `Expr` and
`ProofBuilder` objects are implementation inputs to an adapter, not objects to
rename and freeze as the new API.

## Decisions intentionally left open

The experiments should decide, rather than pre-emptively freeze:

- exact Python package and class names;
- canonical serialized spelling of `SemanticId`;
- whether v0.1 persists `ProofDraft` or only action fixtures;
- exact generated `StepRef` scheme beyond snapshot-local determinism;
- how much of `LanguageSpec` binder metadata is required by the first
  predicate canary;
- whether topic/tag discovery lives directly in `TheoryInterface` or in a
  digest-linked sidecar;
- the smallest useful ABI diff format;
- the boundary between generic `BundleProvenance` references and
  `proof-lab`-specific source/evidence schemas.

These are not permission to weaken the invariants. In particular, stable
declaration identity, typed-before-proof reasoning, fail-closed trust behavior,
explicit DV contracts, human/agent semantic parity, and verifier authority are
already decisions.

## v0.1 success criterion

v0.1 succeeds if the same small kernel lets a human and an agent author the
representative `proof-lab` proofs with less repeated bookkeeping, produces
identical elaborated semantics, preserves the current module/DV and package
interfaces, and fails with precise repairable diagnostics in the negative
cases.

It does not succeed merely because a new set of classes exists, a generated
`.mm` file verifies once, or all current implementation modules can be
imported. The evidence must connect author experience, semantic determinism,
trust boundaries, package policy, and final independent verification.

## Addendum: v0.1 Metaprogramming and Transpiled-Corpus Contract

This addendum incorporates the complete logic transpilation evidence described
in the Project 021 addendum. It narrows the first metaprogramming experiment and
defines how factories and combinators relate to the v0.1 semantic kernel.

### Additional evidence source

The v0.1 evidence set now includes the transpiled `set.mm` logic corpus:

- 2,675 concrete theorem constructors across 14 implementation modules;
- complete assertion docstrings;
- exact mandatory and full active DV metadata;
- successful mmverify, reference Metamath, and metamath-knife verification;
- about 2.07 MiB of generated authoring source for about 1.04 MiB of continuous
  Metamath source;
- only 0.7 percent exact concrete-ref recipe reuse, but 85.2 percent shared
  proof topology after ignoring concrete refs;
- a conservative 373-member parameterized-family cohort.

This evidence tests proof-kernel scale, metadata preservation, declaration
derivation, and compatibility. The three `proof-lab` workflows continue to
test interaction, capabilities, drafts, trust transitions, and human/agent
parity. Neither corpus replaces the other.

### v0.1 scope refinement

The following experimental capabilities are included in v0.1 vertical slices.

1. **Concrete family factories (A).** A typed factory may generate concrete
   Source declarations for existing, already named assertions. Every generated
   member has an explicit `AssertionId`, canonical label, static signature,
   implementation, documentation, provenance, visibility, and exact DV data.
2. **Proof combinators (B).** A typed deterministic combinator may expand into
   an ordered sequence of ordinary `ApplyAssertion` operations over existing
   concrete assertions.
3. **Typed formula-tree construction.** Shape, path, position, mode, and
   direction parameters operate on typed Terms. String rendering is permitted
   only at the legacy compatibility boundary.

The following capability is explicitly not included.

4. **On-demand theorem-family instantiation (C).** v0.1 does not define a
   family-instance registry, dynamic assertion identity or label allocation,
   parameter-specialized signatures or DV, recursive instance materialization,
   or publication of newly requested family members.

The A/B API spelling remains experimental, but this boundary is normative.
A/B MUST compile to the same concrete semantic objects as direct authoring. C
requires a separate post-v1 design.

### `apply_assertion` remains the sole proof-semantic primitive

The v0.1 core operation always applies one concrete `AssertionId` from the
fixed theory interface and profile:

```python
result = apply_assertion(
    state,
    assertion=concrete_assertion_id,
    premises=(step_ref_1, step_ref_2),
    target=optional_checked_constraint,
    subst=optional_partial_schema_substitution,
)
```

Its fields have strict meanings:

- `assertion` selects one existing concrete assertion;
- `premises` are ordered proofs of its essential hypotheses;
- `subst` maps assertion-local schema variables to typed Terms;
- `target` constrains an otherwise inferred result and is checked, never
  trusted as the result;
- the elaborator computes and reifies the final substitution and result.

Family shape, path, arity, mode, direction, child selection, and materialized
label policy are not assertion schema variables. They MUST NOT appear in
`premises` or `subst`. A combinator resolves those parameters before invoking
the concrete operation. Modus ponens may be represented as application of the
concrete `ax-mp` assertion; it does not require a second proof-semantic
primitive.

`apply_assertion` does not select a family member, validate a combinator's
domain parameters, generate a declaration, or materialize a new assertion.
Those are typed operations around the kernel.

### Experimental combinator expansion contract

v0.1 SHOULD exercise, but need not freeze, an operation with the following
semantics:

```text
expand(
    combinator_id,
    typed_params,
    input_step_refs,
    draft_revision,
    theory_interface_digest,
)
    -> ordered ApplyAssertion requests
       + new immutable Draft snapshot
       + non-semantic ExpansionTrace
    | structured diagnostic + unchanged input snapshot
```

The expansion contract is:

1. parameters are immutable, typed, and canonicalized before expansion;
2. every generated request names a concrete, profile-permitted assertion ID;
3. expansion order and generated `StepRef`s are deterministic;
4. the entire expansion is atomic;
5. invalid parameters, stale interface state, failed assertion application, or
   unsatisfied constraints leave the input Draft unchanged;
6. diagnostics identify the combinator invocation, canonical parameters, and
   failed concrete application;
7. expansion MUST NOT add or widen local DV pairs;
8. an implementation/version digest participates in the Draft input lock if a
   persisted action log records a server-side combinator invocation.

For the simplest v0.1 implementation, a source/client combinator library may
emit ordinary typed actions directly. Server-side macro identity is not needed
to prove the semantic model.

### Factory-to-declaration contract

A concrete family factory is declaration tooling, not an admission or trust
shortcut. For every member it produces ordinary source data equivalent to a
direct declaration:

```text
factory + canonical parameters
    -> concrete assertion identity and static signature
    -> ordinary proof Draft/actions
    -> concrete ElaboratedProof
    -> normal lowering, verification, admission, and export policy
```

A factory MUST NOT directly create a trusted `TheoremDecl` merely because
another family member verified. It MUST NOT infer assertion DV from formula
shape or copy a neighboring member's pairs. Imported corpus metadata provides
the member's exact provider `active_dv_pairs`; its static signature carries the
derived `mandatory_dv_pairs`.

Factory parameters and family membership may be recorded in declaration
provenance or `TheoryAnalysis`. They do not replace `AssertionId`, canonical
label, signature, or proof dependencies. Generated declarations participate in
duplicate-ID/label checks and retain deterministic source declaration order.

### IR and digest rules

The authoritative semantic result of A/B is the expanded concrete form:

- Source IR may record factory or combinator syntax and typed parameters;
- Draft IR contains the resulting ordinary hypothesis and assertion-application
  steps, with optional expansion origin for diagnostics;
- Elaborated IR contains only concrete assertion IDs, premise `StepRef`s,
  substitutions, computed Terms, and constraint evidence;
- lowering sees no unresolved family or combinator reference.

An `ExpansionTrace` is provenance, not proof semantics. Renaming or relocating
a combinator while preserving the same expanded DAG does not change the proof
semantic digest. A change to the concrete assertion sequence, premise graph,
substitutions, results, or satisfied constraints does change that digest.

Proof-topology signatures and family-cluster IDs belong in a digest-linked
analysis sidecar. They MUST NOT enter `AssertionId`, `TheoryInterface`, or
proof semantic equality.

### Revised experiment matrix

The v0.1 experiment has three evidence lanes.

**Global regression oracle.** Preserve all 2,675 transpiled constructors and
compare concrete labels, static signatures, ordered hypotheses, conclusions,
direct references, premise order, formula results, active and mandatory DV,
declaration order, lowered Metamath, and verifier results.

**A/B authoring cohort.** The preferred first slice contains all 37
`syl...anc` members and a representative or complete conjunction-projection
cohort. It additionally includes one predicate theorem that exercises a real
mandatory-DV application and one irregular long theorem that remains a direct
proof. Later slices may cover the full 373-member conservative family cohort.

**Proof Lab workflows.** Task 1 remains the concise human/agent application
canary. Tasks 2 and 3 remain the draft, capability, profile, promotion, and
trust-boundary canaries. They are not the sole proof-kernel scale evidence.

### Additional acceptance gates

An A/B v0.1 slice is accepted only when:

- every factory member has an independent concrete identity, label, static
  signature, documentation, and exact DV metadata;
- every expanded combinator reference resolves to a concrete assertion in the
  selected profile;
- no family parameter appears as a proof premise or schema substitution;
- factory and combinator expansion is deterministic across clean processes;
- duplicate generated identities or labels fail before proof execution;
- invalid shape, path, mode, or direction fails atomically with a structured
  diagnostic;
- combinators cannot synthesize DV, and a missing consumer-local mandatory DV
  remains a failure;
- expanded concrete DAGs match the compatibility oracle for behavior-preserving
  migrations;
- public labels, signatures, exports, declaration order, lowered Metamath, and
  verifier results remain unchanged unless an explicit reviewed migration says
  otherwise;
- source reduction and author-supplied redundancy are measured alongside
  diagnostics and verified correctness.

### Revised v0.1 success evidence

In addition to the original `proof-lab` success criterion, v0.1 must show at
least one verified concrete factory family and one verified deterministic
combinator over the transpiled corpus. Their expanded semantics must match the
global oracle while materially reducing repeated author-supplied formulas,
step labels, or proof plumbing.

Success does not require C, a general macro language, or migration of all 2,675
constructors. It requires evidence that typed declarations plus concrete
`apply_assertion` form a sufficient semantic kernel, and that useful
metaprogramming remains a deterministic, inspectable layer above that kernel.
