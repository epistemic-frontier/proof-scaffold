# Project 023: Concrete Proof Families and Combinators

## Status

Draft, 2026-07-16.

This project turns the transpiled-corpus addenda in
[Project 021](./021-authoring-ir-for-human-and-llm-authors.md) and
[Project 022](./022-authoring-api-v0.1.md) into a bounded implementation and
evaluation plan. It is not a general macro-system proposal and does not define
on-demand theorem-family materialization.

Normative words such as MUST, SHOULD, and MAY describe the experiment contract.
Pseudocode fixes semantic responsibilities, not final public API spelling.

### Dependency on the first-class-language slice

Project 023 remains downstream of the semantic sequence established by
[Reference 011](../references/011-language-as-first-class.en.md) and
[Project 024](./024-first-class-language-refactor.en.md):

```text
Term v2 -> Language -> Judgment/Calculus -> apply_assertion -> combinators
```

This does not change the experiment's role. Family factories and combinators
MUST still expand to ordinary concrete assertion declarations and applications
before elaborated proof semantics. They MUST NOT introduce a second Term,
notation, calculus, substitution model, or lowering path. Their typed
parameters use the stable Term and judgment contracts supplied by the earlier
layers.

## Executive decision

Project 023 will test two mechanisms over existing, concrete, labeled
assertions:

1. **Concrete family factories (A)** produce ordinary Source assertion
   declarations for already known theorem members.
2. **Proof combinators (B)** atomically expand typed parameters and input
   `StepRef`s into ordinary applications of existing concrete assertions.

The proof-semantic kernel remains the concrete assertion application proposed
by Project 022. Factories and combinators sit above that kernel and disappear
from elaborated proof semantics:

```text
family source / combinator invocation
                |
                v
       typed deterministic expansion
                |
                v
 concrete declarations and ApplyAssertion steps
                |
                v
          ElaboratedProof
                |
                v
      existing lowering and verification
```

The project will use the complete 2,675-theorem transpiled corpus as an expanded
semantic oracle and migrate two representative family shapes first:

- conjunction projection, represented by the `simp...` cohort;
- conjunction-tree syllogism, represented by all identified `syl...anc`
  members.

Project 023 explicitly excludes dynamic family references that create unnamed
or previously absent assertions. That capability requires a separate project.

## Context and evidence

A complete logic-range transpilation combined `mono`, `partition`, and
`metamath-replay` metadata without changing those projects. It produced:

- 2,736 partition targets;
- 2,675 concrete theorem constructors;
- 61 foundation statements;
- 14 `metamath-logic` implementation modules;
- 2,675/2,675 assertion docstrings;
- 352 theorems with mandatory DV and zero missing mandatory contracts;
- 83 theorems with additional proof-only auxiliary DV;
- 387 generated labels with non-empty active DV context;
- successful mmverify, reference Metamath, and metamath-knife verification.

The corresponding generated authoring code is approximately 2.07 MiB and
36,401 lines, compared with approximately 1.04 MiB and 24,505 lines in the
continuous `set.mm` source range. Function source consists of approximately
22.7 percent docstring bytes, 30.8 percent formula-string bytes, and 46.5
percent proof-construction structure.

AST analysis found:

- 10 repeated exact concrete-reference recipes covering 20 functions, about
  0.7 percent of constructors;
- 167 repeated proof-topology clusters covering 2,280 functions, about 85.2
  percent, when concrete referenced theorem names are ignored;
- a conservative 373-member, approximately 197 KB cohort of clearly named and
  structurally related families.

The conservative cohort includes:

| Cohort | Members | Approximate current source |
| --- | ---: | ---: |
| `syl...anc` | 37 | 26.9 KB |
| conjunction projection / `simp...` | 121 | 50.4 KB |
| ternary positional operations | 93 | 52.5 KB |
| antecedent insertion | 34 | 18.6 KB |
| `mp3an...` | 19 | 10.4 KB |
| positional connective operations | 69 | 38.5 KB |

The 85.2 percent topology result is discovery evidence, not a migration target.
Only a family with a typed mathematical interpretation and verified concrete
expansion is eligible for authoring abstraction.

## Problem statement

The current generated constructors faithfully preserve the source theorem
corpus, but they repeat information that Python and a typed authoring layer can
derive:

- theorem-local step labels;
- instantiated result formulas;
- formula-tree position and grouping operations;
- repeated applications of known concrete assertions;
- registry and constructor boilerplate.

Naively replacing these functions with a recipe interpreter would reduce text
while preserving none of the intended authoring benefit. It would create a
second proof serialization, weaken types and diagnostics, and hide concrete
assertion dependencies.

The experiment must answer a narrower question:

> Can typed concrete-family factories and deterministic proof combinators
> materially reduce author-supplied repetition while expanding to the same
> concrete declarations, proof DAGs, DV contracts, lowered Metamath, and
> verifier results?

## Goals

1. Establish an unambiguous source-of-truth policy for imported and newly
   authored theorem families.
2. Define a typed, immutable experimental representation for family member
   parameters without freezing a general family API.
3. Generate ordinary static `AssertionSignature` and Source declaration data
   for every concrete family member.
4. Define atomic, deterministic proof-combinator expansion over the Project 022
   concrete `apply_assertion` kernel.
5. Preserve concrete assertion identity, labels, signatures, documentation,
   proof dependencies, ordering, and exact DV data.
6. Build a semantic-diff harness against the complete transpiled corpus.
7. Evaluate projection and `syl...anc` as complete family cohorts rather than
   cherry-picked examples.
8. Measure authoring reduction, readability, diagnostics, determinism, source
   size, and build cost independently.
9. Produce evidence that can refine Projects 021 and 022 before their public
   APIs are frozen.

## Non-goals

- On-demand generation of a theorem not already represented by a concrete
  declaration.
- A `FamilyRef` in Elaborated IR, Proof IR, BuilderV2, or emitted Metamath.
- Dynamic assertion IDs or labels derived during lowering.
- A general macro language, proof recipe interpreter, or embedded tactic DSL.
- Automatic acceptance of every topology cluster as a mathematical family.
- Heuristic theorem choice, premise search, or silent first-match behavior.
- Changing BuilderV2, linker semantics, verifier policy, or foundation scope.
- Modifying `mono`, `partition`, or `metamath-replay` for this experiment.
- Migrating all 2,675 constructors before evaluating the first slice.
- Making compression ratio the sole or primary correctness criterion.
- Freezing public Python class names, serialized family syntax, or a
  cross-process combinator registry in the first prototype.

## Terms

- **Imported assertion record**: the source statement, ordered hypotheses,
  proof replay, source label, documentation, scoped active DV, and mandatory DV
  obtained from the pinned `set.mm` corpus and replay metadata.
- **Concrete declaration**: one assertion with a stable `AssertionId`, canonical
  Metamath label, static signature, implementation, visibility, and provenance.
- **Family parameter**: a typed value such as conjunction shape, projection
  path, position, mode, or direction that selects or constructs a concrete
  member. It is not a Metamath schema substitution.
- **Concrete family factory**: source tooling that maps one accepted family
  member specification to an ordinary concrete Source declaration.
- **Proof combinator**: a deterministic derived operation that maps typed
  parameters and existing `StepRef`s to ordinary concrete assertion
  applications.
- **Expansion trace**: non-semantic provenance connecting a factory or
  combinator invocation to generated declarations, actions, and steps.
- **Expanded semantic oracle**: the pinned, concrete assertion and proof-DAG
  projection extracted from the verified 2,675-constructor baseline.
- **Family candidate**: an analysis result that has not yet been accepted as an
  authoring abstraction.

## Source-of-truth policy

### Imported families

For the transpiled corpus, pinned `set.mm` plus replay and assertion-site
metadata remain authoritative for each concrete theorem's:

- canonical label;
- ordered schema variables and floating order;
- ordered essential hypotheses;
- conclusion;
- concrete proof dependencies and premise order;
- documentation;
- complete assertion-site `active_dv_pairs`;
- derived public `mandatory_dv_pairs`;
- source order and source provenance.

An imported-family specification is a checked projection over those records.
It may describe shared construction and typed parameters, but MUST NOT carry a
second independently editable copy of theorem statements, documentation, DV,
or public identity.

```text
pinned set.mm + replay metadata
              |
              v
    imported assertion records
              |
        +-----+-----+
        |           |
        v           v
 concrete oracle   checked family view
                        |
                        v
              regenerated declarations
```

If family expansion disagrees with an imported assertion record, the experiment
fails. The family definition does not overwrite or reinterpret the source
record.

### Newly authored families

For a future theorem family whose members do not originate in an imported
corpus, the typed family source may be authoritative. It must still materialize
ordinary concrete Source declarations before elaboration and must provide or
derive every concrete member's static signature, documentation, replay
context, visibility, and provenance through one declaration path.

Imported-family views and newly authored-family sources MUST use distinct
construction entrypoints or explicit modes. A package cannot treat the same
member as simultaneously authoritative from imported metadata and hand-edited
family data.

### Generated artifacts

Legacy `ProofBuilder` constructors, registries, catalogue rows, module files,
coverage tables, and compatibility manifests are derived artifacts. In a
migrated slice, only one declaration path is editable. Generated outputs MUST
identify their source digest and family implementation version where relevant.

## Core semantic boundary

Project 023 retains the Project 022 assertion-application contract:

```python
result = apply_assertion(
    state,
    assertion=concrete_assertion_id,
    premises=ordered_step_refs,
    target=optional_checked_constraint,
    subst=optional_partial_schema_substitution,
)
```

The operation:

1. resolves exactly one concrete assertion in a fixed theory interface and
   profile;
2. matches ordered premises against ordered essential hypotheses;
3. infers only unique local schema substitutions;
4. checks explicit target and partial substitution constraints;
5. computes the result Term;
6. checks sort, binder, capture, and mandatory-DV constraints;
7. appends one fully reified concrete application to immutable Draft state.

Family parameters MUST NOT be encoded as premises or schema substitutions.
The concrete assertion application neither selects a family member nor knows
that its caller is a combinator.

The semantic proof kernel for this experiment consists of initial hypothesis
steps, concrete assertion application, and final root selection. Modus ponens
SHOULD be represented as application of the concrete `ax-mp` signature unless a
legacy adapter requires a temporary specialized spelling.

## Typed formula construction

Family implementations operate on immutable typed `Term`s, not concatenated
formula strings or build-local token IDs.

The first slice needs at least:

- WFF schema variables;
- implication construction and decomposition;
- binary and ternary conjunction construction and decomposition;
- typed conjunction-tree shapes;
- typed projection paths;
- structural equality and hashing;
- canonical Unicode rendering for the legacy adapter;
- canonical Metamath lowering through the existing bridge.

The compatibility boundary MUST satisfy:

```text
parse(render(term)) == term
```

across every generated hypothesis, target, intermediate result, and conclusion
in the migrated cohort. Parsing and rendering errors identify the family,
member, parameters, and concrete assertion.

An already compiled `Wff` token container is not a stable family parameter.
Its symbols belong to one runtime interner. Typed Terms bind to build-local
`SymbolId`s only at the existing semantic-to-backend boundary.

## Static declaration contract

Every materialized family member has static consumer-facing data available
without executing its proof body:

```python
@dataclass(frozen=True)
class FamilyMemberSpec(Generic[P]):
    params: P
    assertion_id: AssertionId
    canonical_label: str
    source_assertion: SourceAssertionRef | None


class ConcreteFamily(Protocol[P]):
    def materialize_source(
        self,
        member: FamilyMemberSpec[P],
        context: FamilyContext,
    ) -> SourceTheoremDeclaration: ...
```

This pseudocode does not freeze names. It fixes these rules:

- `P` is immutable, typed, and canonicalizable;
- a concrete member has an explicit identity and label before proof expansion;
- imported signatures and DV come from the authoritative source record;
- the produced object is untrusted Source/Draft input, not an admitted
  `TheoremDecl`;
- proof construction proceeds through ordinary authoring operations;
- duplicate IDs and labels fail before proof execution;
- materialization order is explicit and deterministic;
- family membership does not alter assertion identity or interface policy.

The legacy adapter MAY expose `Callable[[System], Proof]` constructors for
existing consumers, but constructor execution is no longer signature
discovery. The adapter derives from the static declaration.

## Proof-combinator expansion contract

The experimental combinator boundary is conceptually:

```python
@dataclass(frozen=True)
class ExpansionRequest(Generic[P]):
    combinator: CombinatorId
    params: P
    inputs: tuple[StepRef, ...]
    draft_revision: RevisionId
    theory_interface_digest: Digest


@dataclass(frozen=True)
class ExpansionResult:
    state: ProofDraft
    generated_steps: tuple[StepRef, ...]
    trace: ExpansionTrace
```

A combinator expansion MUST:

1. canonicalize and validate parameters before mutating Draft state;
2. resolve every child role to one concrete, profile-permitted `AssertionId`;
3. emit only ordinary `apply_assertion` requests;
4. preserve explicit premise order;
5. allocate deterministic theorem-local `StepRef`s;
6. execute atomically against one immutable Draft revision;
7. return unchanged input state on any failure;
8. expose a structured diagnostic containing the enclosing theorem,
   combinator, canonical parameters, generated operation index, and concrete
   failing assertion;
9. leave local DV unchanged;
10. produce a non-semantic expansion trace.

For v0.1, a source/client library MAY produce ordinary typed actions without a
server-side macro registry. If persisted action logs record combinator
invocations rather than expanded actions, the combinator implementation and
parameter-schema digest MUST be part of the Draft input lock.

## Step identity and expansion namespaces

Combinators create multiple theorem-local steps and may be nested or invoked
more than once. They MUST NOT rely on global counters, Python object identity,
set iteration, import order, or mutable module state.

The prototype MUST define and test:

- a stable invocation occurrence key within one Draft snapshot;
- deterministic child operation indices;
- nested expansion namespaces;
- optional caller-provided stable keys for source diff quality;
- collision behavior when a caller repeats a supplied key;
- display labels separately from semantic `StepRef` identity;
- expansion-trace mapping from invocation to generated `StepRef`s.

Generated `StepRef`s are semantic proof-DAG occurrence identities. Human step
labels are presentation. A rename that leaves occurrence references and the
concrete DAG unchanged MUST NOT change mathematical content, while a changed
premise graph MUST change the proof semantic digest.

## Distinct-variable contract

Project 023 preserves the provider/consumer distinction.

### Concrete family members

Each member's static `AssertionSignature` contains exact
`mandatory_dv_pairs`. Its implementation/replay record contains complete
`active_dv_pairs`, including proof-only auxiliary variables. For imported
members both derive from the pinned source assertion record.

A family implementation MUST NOT:

- infer DV from conclusion shape;
- copy DV from a neighboring member;
- merge independent pairs into a clique;
- take a transitive closure;
- drop proof-only pairs;
- use family shape or path as a substitute for variable identity.

### Combinators

A combinator has no assertion signature or DV context. Each generated concrete
application checks its substituted mandatory contract against the enclosing
theorem's local DV. The combinator MUST NOT add a missing pair automatically or
widen the local relation as a repair strategy.

Missing consumer-local DV is a structured failure and leaves Draft state
unchanged. Formula variables and DV endpoints use the same semantic identity
and relocation path.

## Provenance, analysis, and semantic digests

The following are semantic:

- concrete declaration identity and canonical label;
- ordered static signature;
- assertion kinds and assumption contracts where defined by Projects 021/022;
- concrete proof DAG applications, premises, substitutions, results, and
  satisfied constraints;
- replay context required for faithful lowering;
- public policy included in the theory interface digest.

The following are non-semantic provenance or regenerable analysis:

- family name and candidate-cluster ID;
- family parameters when the expanded concrete declaration already determines
  identical mathematical content;
- combinator source file and implementation symbol;
- expansion trace and explanatory notes;
- source layout and partition module;
- authorship, timestamps, and model information;
- topology signatures and compression measurements.

Changing non-semantic provenance without changing the concrete declaration or
expanded DAG MUST leave the semantic digest unchanged. Changing concrete
applications, premise edges, substitutions, results, constraints, signature,
or DV MUST change the appropriate proof, declaration, or interface digest.

If an action log persists an unexpanded combinator invocation, the expansion
implementation digest is part of replay input, even though it is not part of
the final proof's mathematical identity.

## Family discovery and approval

Automated clustering produces candidates, not APIs. The approval pipeline is:

```text
formula/ref/topology analysis
            |
            v
    candidate family report
            |
            v
 typed parameter interpretation
            |
            v
 mathematical responsibility review
            |
            v
 checked expansion against every member
            |
            v
      accepted family source
```

An accepted family report answers:

1. What mathematical operation does the family represent?
2. What is the typed parameter domain?
3. Does one canonical parameter value identify one concrete member?
4. How are parent parameters transformed into concrete child roles?
5. Are formulas constructed exclusively from typed Terms?
6. Which members are exceptions, and are they excluded or explicitly handled?
7. Does the abstraction improve author readability and diagnostics?
8. Does complete expansion preserve the concrete semantic oracle?

A helper that merely interprets generic step tuples or topology hashes is not
an accepted proof combinator.

## Prototype families

### Projection family

The projection slice represents conjunction component selection using typed
tree paths. It SHOULD exercise:

- binary and ternary conjunction nodes;
- left/right and positional path segments;
- theorem, inference, deduction, and biconditional variants where present;
- nested paths;
- repeated equal leaves, proving that path cannot always be inferred from the
  target formula;
- invalid and out-of-range paths;
- stable mapping from parameter values to existing concrete labels.

The first implementation MAY start with a representative subset, but acceptance
of the family abstraction requires expansion checks over the full declared
projection cohort.

### `syl...anc` family

The syllogism-conjunction slice includes all 37 identified members. It SHOULD
exercise:

- typed conjunction-tree shapes;
- ordered implication premises;
- selection of `jca`, `3jca`, and concrete child `syl...anc` assertions;
- parent-to-child shape transformation;
- family-to-family references resolved to concrete labels before application;
- deterministic recursive expansion;
- unsupported shapes and missing child mappings;
- expansion-cycle protection even though the accepted mapping is acyclic.

The family name and shape do not enter Elaborated IR. Every generated step
names the same concrete assertion as the oracle.

### Controls

The experiment also includes:

- one predicate theorem whose proof performs an actual mandatory-DV assertion
  application, not merely a theorem carrying unused DV metadata;
- one irregular long theorem from the `axioms` module that remains a direct
  concrete proof.

The irregular control demonstrates that Authoring v0.1 does not require every
proof to fit a family or combinator abstraction.

## Semantic-diff harness

The harness compares baseline and candidate at three levels.

### Per-declaration comparison

For every migrated concrete assertion, compare:

- `AssertionId` and canonical label;
- schema-variable identities, sorts, and mandatory floating order;
- ordered essential hypotheses;
- conclusion Term;
- mandatory DV;
- complete active DV and auxiliary local variables;
- documentation and source provenance presence;
- visibility and declaration order.

### Per-proof comparison

Compare:

- concrete assertion dependency sequence and set;
- premise order and proof-DAG edges;
- reified schema substitutions;
- intermediate result Terms;
- final root and theorem conclusion;
- proof-only variables and replay context;
- assumption and dependency closure where available.

The primary requirement is semantic equivalence. For the imported
behavior-preserving slice, the experiment SHOULD additionally preserve the
concrete ref sequence and intermediate results byte-for-byte after canonical
serialization, because the source oracle supplies those facts exactly.

### Artifact comparison

Compare:

- emitted Metamath;
- names and Unicode/canonical mappings;
- exports and public manifest;
- declared, lowered, emitted, and excluded counts;
- deterministic declaration and final emission order;
- interface and semantic digests;
- dependency and assumption reports;
- all configured verifier results.

Regenerating expected output is not acceptance. Every difference is classified
as presentation-only, implementation-only, public-interface, or semantic and
must be reviewed according to Projects 021/022.

## Negative and adversarial tests

The prototype MUST cover at least:

1. invalid projection path;
2. out-of-range ternary position;
3. unsupported conjunction shape;
4. duplicate or non-canonical family parameters;
5. ambiguous parameter-to-member mapping;
6. missing concrete child assertion;
7. duplicate generated `AssertionId`;
8. duplicate generated canonical label;
9. factory body whose root disagrees with its static conclusion;
10. factory hypotheses whose order disagrees with its static signature;
11. stale source or theory-interface digest;
12. partial combinator failure after one otherwise valid generated operation;
13. caller-supplied stable step-key collision;
14. generated target or substitution conflict;
15. combinator attempt to add or widen local DV;
16. missing consumer-local mandatory DV;
17. proof-only active DV omitted by a family adapter;
18. nondeterministic dict/set iteration changing member or expansion order;
19. nested combinator expansion diagnostic preserving the full invocation
    chain;
20. unresolved family/combinator node reaching finalization or lowering.

Every failure is fail-closed and leaves immutable input state unchanged where
the operation is transactional.

## Metrics

### Semantic correctness

- migrated members matching the expanded oracle;
- signature and DV equivalence rate;
- concrete proof-DAG equivalence rate;
- deterministic replay across clean processes;
- verifier pass rate and explicit verifier skips.

### Authoring cost

- author-supplied formula and target count;
- author-supplied internal step-label count;
- explicit concrete ref and premise-plumbing count;
- source lines and bytes;
- code required to add one existing member to an accepted family;
- number and size of family-specific exceptions.

### Readability and diagnostics

- whether source visibly communicates shape, path, mode, and direction;
- whether concrete dependencies remain inspectable;
- IDE navigation from member identity to source and expanded proof;
- diagnostic localization to family, member, parameter, and concrete step;
- traceback/source-map quality through the legacy adapter.

### Performance

- family materialization time;
- combinator expansion time;
- semantic-diff time;
- full build and verification time;
- peak memory;
- any cache hit rate, with cache keys and invalidation policy recorded.

Compression is reported but cannot compensate for semantic drift, opaque
source, weak diagnostics, or nondeterminism.

## Cross-project ownership

### `proof-scaffold`

Owns generic mechanisms:

- typed `Term` and static assertion declarations;
- concrete `apply_assertion` semantics;
- immutable Draft operations and atomic expansion support;
- deterministic `StepRef` allocation;
- generic expansion diagnostics and traces;
- semantic-diff infrastructure;
- legacy lowering adapters.

Framework runtime code MUST NOT contain `syl`, `simp`, logic-specific family
member tables, or set.mm-specific clustering rules.

### `transpiler`

Owns imported-corpus integration and analysis:

- extraction of concrete assertion records;
- static declaration generation;
- source digest and provenance mapping;
- family candidate reports;
- baseline expanded semantic fixtures;
- generated compatibility projections.

Candidate discovery does not grant family approval.

### `metamath-logic`

Owns the mathematical instances:

- accepted logic-specific family definitions;
- parameter-to-concrete-member mappings;
- curated proof combinators;
- theorem documentation and public policy;
- corpus-specific verification evidence;
- decisions to leave irregular proofs direct.

### `mono`, `partition`, and `metamath-replay`

Remain input providers for this experiment. Project 023 does not require code
changes in them. Partition module and search-region assignments remain
implementation and discovery metadata, not assertion or family identity.

## Work plan

### Phase 0 - Pin and package the oracle

Deliverables:

- record exact repository revisions, set.mm source hash, partition boundaries,
  generator version, package versions, and verifier set;
- canonicalize per-assertion declaration, proof-DAG, documentation, and DV
  fixtures;
- record module order, registry order, emitted artifacts, and current metrics;
- prove deterministic fixture generation in two clean processes.

Exit gate:

- the full 2,675-assertion oracle is reproducible and differences are
  machine-reportable without executing a family implementation.

### Phase 1 - Build the semantic-diff harness

Deliverables:

- static-signature comparison;
- proof-DAG comparison;
- active/mandatory-DV comparison;
- artifact and verifier comparison;
- structured mismatch diagnostics with source and candidate origins.

Exit gate:

- intentional mutations to statement, premise order, ref, result, root,
  mandatory DV, active DV, and declaration order are each detected by focused
  negative fixtures.

### Phase 2 - Typed Term and static declaration slice

Deliverables:

- minimum typed propositional Term constructors;
- conjunction shape and path types;
- canonical formatter and legacy parser adapter;
- static declarations for the selected family slice;
- legacy `ProofBuilder` adapter derived from static declarations.

Exit gate:

- all slice formulas satisfy round-trip equality, signatures are inspectable
  without proof execution, and legacy direct proofs still lower identically.

### Phase 3 - Projection family

Deliverables:

- reviewed projection parameter model;
- imported-member mapping;
- concrete family factory or checked declaration projection;
- projection combinator expansion;
- full positive and negative family tests;
- source and authoring-cost metrics.

Exit gate:

- the declared projection cohort expands to the oracle with deterministic,
  atomic behavior and improved authoring evidence.

### Phase 4 - `syl...anc` family

Deliverables:

- reviewed conjunction-tree parameter model;
- all 37 member mappings;
- deterministic parent/child parameter transformation;
- concrete child assertion resolution;
- recursive expansion diagnostics and cycle protection;
- complete oracle and verifier comparison.

Exit gate:

- all 37 members match concrete expanded semantics and no family reference
  reaches Elaborated IR or lowering.

### Phase 5 - DV and irregular controls

Deliverables:

- one real predicate mandatory-DV application through the new core;
- missing-consumer-DV and active-DV-loss negative tests;
- one irregular long direct theorem through the same static declaration and
  lowering path;
- comparison showing no pressure to invent a generic recipe abstraction.

Exit gate:

- provider/consumer DV ownership is preserved and both family and non-family
  proofs coexist in one theory slice.

### Phase 6 - Evaluate and feed back

Deliverables:

- semantic, authoring, readability, diagnostics, size, and performance report;
- API changes proposed for Projects 021/022, if any;
- list of accepted, rejected, and deferred family candidates;
- compatibility and rollback plan;
- decision on whether to expand toward the remaining 373-member cohort.

Exit gate:

- the evidence supports an explicit adopt, revise, or stop decision rather
  than automatic promotion of the prototype API.

## Acceptance criteria

Project 023 succeeds when all of the following are true.

1. The full expanded oracle is pinned and reproducible.
2. Static signatures are available without executing proof bodies.
3. Projection and all 37 `syl...anc` members have typed parameter models and
   accepted mathematical responsibilities.
4. Every migrated member retains independent concrete identity, label,
   documentation, signature, proof, and DV data.
5. Factories produce ordinary Source/Draft declarations and do not bypass
   verification or admission.
6. Combinators expand atomically to concrete `apply_assertion` operations.
7. Elaborated IR and lowering contain no unresolved family or combinator node.
8. Family parameters never enter proof premises or schema substitutions.
9. Expanded concrete DAGs match the oracle for behavior-preserving members.
10. Mandatory and active DV compare exactly, and missing consumer DV fails.
11. Duplicate identities and labels fail before proof execution.
12. Expansion, diagnostics, declaration order, and artifacts are deterministic
    across clean processes.
13. The predicate and irregular direct-proof controls pass.
14. Normal BuilderV2, linker, and verifier authority is unchanged.
15. The experiment demonstrates a material reduction in author-supplied
    repetition or a clear readability/diagnostic improvement.
16. All metrics, deviations, and verifier skips are recorded.

Project 023 does not succeed merely because source bytes shrink, one generated
artifact verifies, or a generic factory can instantiate Python closures.

## Stop and rollback criteria

The experiment stops or revises its abstraction if any of these persist after
a focused fix attempt:

- family source becomes less understandable than direct concrete declarations;
- imported statement, proof, documentation, or DV must be duplicated as a
  second editable source;
- concrete dependencies become hidden from Elaborated IR or diagnostics;
- family exceptions dominate the parameter model;
- deterministic expansion requires global mutable state;
- semantic equivalence cannot be checked independently of the implementation;
- combinators need to synthesize DV or weaken assertion-application checks;
- BuilderV2, linker, or verifier contracts must change to support A/B;
- the prototype silently grows into on-demand theorem materialization.

Rollback keeps the static declaration and semantic-diff improvements where
independently useful, removes family/combinator adoption for the failed slice,
and retains the verified direct constructors through the compatibility adapter.

## Deferred C trigger and future project

On-demand theorem-family materialization may be proposed separately only when:

1. an author needs a valid shape, path, or arity absent from the concrete
   assertion registry;
2. the result must have an independently reusable or exported theorem identity;
3. proof-combinator inlining is measured and found inadequate;
4. a reviewed label and interface compatibility policy exists.

A future project must define at least:

- `FamilyId` and versioned canonical parameter schemas;
- deterministic `FamilyInstanceKey`, `AssertionId`, and Metamath label policy;
- static instance header before proof body construction;
- recursive instance closure, deduplication, caching, and cycle handling;
- mandatory and active DV specialization;
- visibility, profile, assumption, admission, and export policy;
- interface serialization and digest effects;
- complete provenance and diagnostics.

No Project 023 API should reserve a loose `params: Any` field on current proof
references as a shortcut toward that design.

## Risks

- **Compression-driven abstraction.** Byte savings can promote mathematically
  meaningless helpers. Mitigation: typed responsibility review and complete
  member expansion evidence.
- **Dual source of truth.** Imported records and family tables can drift.
  Mitigation: family views reference source assertion IDs and semantic hashes
  rather than copying assertion content.
- **Macro opacity.** A compact invocation can hide actual dependencies.
  Mitigation: concrete Elaborated IR, expansion traces, and dependency views.
- **Diagnostic collapse.** Errors may point only into a shared helper.
  Mitigation: invocation/member/parameter/concrete-step origin chains.
- **Identifier instability.** Nested expansion can create noisy diffs.
  Mitigation: deterministic occurrence keys and separate display labels.
- **DV leakage.** A helper may appear to own a required relation.
  Mitigation: no combinator DV mutation and mandatory negative tests.
- **Runtime signature recursion.** Factory execution can become signature
  discovery. Mitigation: static declaration headers before proof bodies.
- **Overfitting to propositional trees.** Generic APIs may acquire logic-specific
  shape assumptions. Mitigation: framework owns only generic typed mechanisms;
  logic owns the family instances.
- **Generated-source ergonomics.** Closures may harm IDE and documentation
  quality. Mitigation: static declaration identity, source maps, and legacy
  adapters rather than closure identity as the public API.
- **Scope creep into C.** Missing members may encourage dynamic materialization.
  Mitigation: explicit stop boundary and a separate future project.

## Open questions

The experiment, rather than this draft, should decide:

1. Whether an imported concrete family is best represented as a checked family
   view, a generated Source declaration table, or both with one authoritative
   projection.
2. The minimum typed conjunction-shape and path algebra that remains readable.
3. Whether client-side expanded actions are sufficient for v0.1 or an atomic
   server-side expansion operation is needed for diagnostics and transactions.
4. The exact theorem-local `StepRef` occurrence-key scheme.
5. Which expansion provenance belongs in Source IR, Draft IR, and a sidecar.
6. Whether exact intermediate-step equivalence remains required after a future
   reviewed proof refactor, versus only semantic root and verifier equivalence.
7. The minimum source reduction or authoring-cost improvement that justifies
   adopting a family abstraction.
8. Whether the remaining positional cohorts share reusable parameter types or
   should remain logic-specific independent families.
9. How family documentation is presented without hiding each concrete
   theorem's original docstring and source history.
10. Which parts of the semantic-diff harness become permanent generic
    `proof-scaffold` tooling versus transpiler-owned corpus fixtures.

## Required evidence record

Every completed phase records:

```text
Project 023 phase/slice:
proof-scaffold SHA/version:
transpiler SHA/version:
metamath-logic SHA/version:
mono/partition/metamath-replay revisions:
set.mm source hash and selected range:
family implementation and parameter-schema digest:
oracle fixture digest:
members attempted/passed/excluded:
semantic and artifact diff summary:
mandatory/active DV comparison:
source and authoring-cost metrics:
expansion/build/verification performance:
negative and adversarial tests run:
verifiers run and explicit skips:
known deviations and owner:
adopt/revise/stop decision:
rollback path:
```

This record prevents a smaller generated file or one successful verifier run
from being mistaken for a sound authoring abstraction.
