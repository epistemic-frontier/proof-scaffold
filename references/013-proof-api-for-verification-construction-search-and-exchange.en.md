# Reference 013: Proof API for Verification, Construction, Search, and Exchange

> Status: Architectural decision draft, 2026-07-18.
>
> This document follows [Reference 011: Language as a First-Class Element](011-language-as-first-class.en.md) and
> [Reference 012: Semantic Definition of Structures, Axioms, and Proofs](012-defining-structures-axioms-and-proofs.en.md).
> It evaluates the current `semantic-api-v2` and sets boundaries and priorities for the next phase; class names and file-format names are not yet frozen.

## 0. Conclusions First

The current API is already a good **in-process API for constructing complete proofs**: typed `Term`,
`AssertionSignature`, the unified assertion-application kernel, `ProofAuthor.use()/qed()`, an explicit
catalog/assertion profile (`AssertionProfile`), and DV checking should all be retained.

It is not yet a proof-object specification shared by verification, search, and exchange. The largest gap is not
the absence of yet another expressive capability, but that the boundaries do not close:

```text
An object can be constructed and have a content digest
                  ≠
The object has been verified under a locked theory, dependencies, and trust policy
```

Construction of `ElaboratedProof` performs structural validation of the proof graph; the check that actually
reapplies every assertion according to the calculus, catalog, and assertion profile currently occurs in
`build_semantic_replay_plan()`. Meanwhile, although the existing internal canonical projection carries a version
tag, there is no public normative proof/theory archive codec, strict decoder, wire schema, or complete
`VerificationEnvironmentLock`. It can therefore serve as an internal object in a trusted Python generation
pipeline, but cannot directly serve as an exchange certificate for untrusted input.

The second gap is the absence of a genuine incomplete proof state. The current `ProofDraft` contains only
hypotheses and fully concrete, immediately checked steps; it is closer to `CheckedProofPrefix` and cannot
represent a goal, hole, metavariable, constraint, or persistent branch. Ordinary linear proofs are unaffected,
but interactive construction and search lack an appropriate public state boundary.

The next phase should adopt these decisions:

1. **First elevate the existing complete proof into an independently replayable, exchangeable certificate.** Do
   not create another Proof DAG class parallel to `ElaboratedProof`.
2. **When interactive construction and search are needed, add only one minimal, immutable `ProofState`.** Do not
   put holes or metavariables into the verifier's hole-free `Term` or the final proof.
3. **The three layers are internal invariant boundaries, not three ordinary-user APIs.** Initially reuse existing
   replay and backend conversion, plus Metamath build artifacts, for the execution layer; do not design a new
   Proof VM, binary ISA, or hardware packet without performance evidence.
4. **Start with a thin envelope and companion data for package/provenance concerns.** Do not immediately introduce
   a large, editable, general-purpose Package IR.

Each default user path contains at most three principal concepts:

```text
Ordinary author    Theory -> ProofAuthor -> Proof
Ordinary consumer  Theory + Proof
IDE / search engine Theory + ProofState -> Proof
```

The four capabilities are construction (`prove/refine`), verification (`verify`), external search over
`ProofState`, and exchange (`load/save`). `ProofAuthor` remains the default simplified interface, while
`ProofState` exposes complexity on demand only to roles that need it. Ordinary users should not be required to
understand catalog digests, profile-lock details, packets, Merkle nodes, execution plans, frontiers, or provenance
graphs.

---

## 1. The Public Concept Limit Is an Architectural Constraint

Layering an IR can easily cause an explosion in object count. A layer's internal necessity does not mean it
should become a public type that users must manually construct, pass, and serialize.

This project adopts the following API budget:

### 1.1 One Default Path

Authors of complete proofs should continue to write only mathematical actions:

```python
author = THEORY.prove(MP2B_SIGNATURE)
h_phi, h_phi_psi, h_psi_chi = author.hypotheses
psi = author.use(AX_MP, h_phi, h_phi_psi)
chi = author.use(AX_MP, psi, h_psi_chi)
proof = author.qed(chi)

report = THEORY.verify(proof)
```

Here `THEORY.prove(...)` merely binds the language/calculus/catalog/assertion-profile environment currently
required by `ProofAuthor(...)` and derives a snapshot-local proof ID for ordinary use. An explicit `proof_id=`
belongs only to advanced/debug use; it does not introduce a second proof semantics.

The exchange path should remain equally direct:

```python
THEORY.save(proof, "mp2b.skir")
proof = THEORY.load("mp2b.skir")  # decode + verify，默认出错即拒绝
```

These names are illustrative and not yet frozen; the key is that ordinary users manipulate only `Theory` and
`Proof`. Unverified packets, codec limits, dependency locks, and replay plans are internal or advanced APIs. On
the default path, `save` verifies before writing and `load` verifies before returning. Verification during load
is only the gate for returning a `Proof`; it does not write “verified” status into the proof's content identity.
Obtain a separate `VerificationReport` or certificate when audit evidence is needed.

### 1.2 Expose Complexity on Demand

Only interactive proving, IDEs, or search engines need to see `ProofState`:

```python
state = THEORY.start(MP2B_SIGNATURE)
goal = state.goals[0]
outcome = state.refine(goal.id, assertion=AX_MP)
proof = outcome.state.finish()
```

Ordinary forward proofs continue to use `ProofAuthor.use()`. Search engines directly reuse `ProofState`; a
separate `SearchState` must not be introduced. The frontier, beam score, MCTS visit count, parent edge, and model
score belong to the search engine, not to the mathematical state.

### 1.3 Every Public Abstraction Must Repay Its Cost

A new public type should satisfy at least one of the following conditions; otherwise it remains an internal
implementation detail:

- it owns invariants that conflict with and cannot be merged into adjacent types;
- two or more independent consumers must understand it across processes or implementations;
- hiding it would force users to repeatedly supply information that cannot be derived reliably.

Merely “possibly useful for hardware, AI, collaboration, or analysis in the future” is insufficient reason to
freeze a v1 type.

### 1.4 Each Fact Appears Once

If the verifier can derive the result, DV evidence, and direct dependencies from the assertion, premises, and
substitution, a new archive's content identity should not treat those derived values as a second authoritative
input. An implementation may cache or display them, but must recompute them; caches must not alter the new proof
content identity. The current v2 `semantic_digest` does not yet follow this new canonical projection; see
Section 6.3 for compatibility handling.

---

## 2. What the Current API Already Solves

The current path can be summarized as follows:

```text
LanguageInterface + CalculusInterface + AssertionCatalog/AssertionProfile
                              │
                              v
                         ProofAuthor
                              │ use()
                              v
                 unified assertion application
                              │ qed()
                              v
                      ElaboratedProof
                              │
                              v
                build_semantic_replay_plan
                              │
                              v
                 legacy backend conversion / Metamath
```

The following already form a sound foundation and should not be rewritten:

1. `Term` is a typed, backend-neutral, construction-hole/metavariable-free `Var | App`; it may contain
   schema/local/free variables, and constructors, sorts, and variables have stable nominal identifiers.
2. `AssertionSignature` clearly distinguishes ordered premises, conclusion, schema variables, and the mandatory
   distinct contract; it is the theorem ABI shared by verification, construction, and search.
3. `ProofAuthor.use()` goes through the unified application kernel, performing unification, complete
   substitution, result computation, and DV checking. Explicit `target=` and `subst=` are only constraints, not
   a second semantics.
4. `ElaboratedProof` is immutable, root-reachable, and hole-free, and contains only concrete assertion
   applications; families/combinators have disappeared before elaboration.
5. Under assertion-profile constraints, `build_semantic_replay_plan()` can already resolve each assertion from
   the catalog step by step, then call the public application kernel again with the recorded premises, target,
   and substitution.
6. Language, calculus, catalog, and proof already have versioned canonical projections for digests, laying the
   groundwork for normative archives.
7. Four-domain transpilation has demonstrated that this default complete-proof path handles a realistically
   sized corpus, and baselines exist for generation and for importing/re-elaborating build artifacts;
   per-assertion replay, transitive closure, and an independent Metamath verifier still require separate
   baselines as specified in Section 7.

The next step is therefore not to overturn the proof-authoring API, but to place the existing semantic kernel
behind the correct public boundaries.

---

## 3. The Largest Current Discontinuities

### 3.1 Verification State and Content Identity Are Conflated

`ElaboratedProof.__post_init__()` first calls `_validate_elaborated_proof()` and then immediately generates
`semantic_digest`. This check guarantees that:

- the theorem signature and hypotheses align;
- step IDs do not repeat and premises refer only backward;
- the root equals the theorem conclusion;
- every application is reachable from the root;
- the direct-dependency set and theorem-level DV scope have canonical forms.

It has no calculus/catalog context, so it does not re-resolve each assertion or recompute substitutions, results,
or satisfied DV conditions. Actual semantic replay currently occurs in `build_semantic_replay_plan()`.

Consequently:

- `semantic_digest` is a hash of declared content, not a validity certificate;
- a structurally valid object with an incorrect assertion application can still have a digest;
- the name `build_semantic_replay_plan` conceals the most important verification boundary as preparation for
  backend conversion.

Verification should be elevated into the single, explicit, pure-data public entry point:

```python
report = verify_proof(theory, proof)
# 或：report = theory.verify(proof)
```

At minimum, `report` distinguishes `ok`, a stable error code, step/path, assertion, expected/actual values, and a
DV witness. Whether a `VerifiedProof` wrapper is used internally should not add a required term for ordinary
users; a public `VerificationReport` sufficiently expresses the state.

### 3.2 A Proof Does Not Close Over Its Dependency Semantics

The current proof canonical projection records `calculus_digest` and assertion nominal identifiers, but not a
per-assertion interface digest or an exact theory/import lock. A nominal identifier states “what it is called”;
alone, it cannot state “which signature and which verified implementation this name denotes.”

More importantly, a catalog may contain theorem signatures. Local replay can show that “this step is valid
relative to that signature,” but cannot show that the referenced theorem itself has a valid implementation. If a
whole-theory verifier does not check the dependency DAG, any theorem signature may be mistaken for an oracle.

The current field `dependency_closure` is actually constructed from the current proof's set of step assertions:
it contains direct dependencies, not a transitive closure. The name would mislead incremental verification,
axiom audits, and package publication.

The minimal improvements are:

1. Define that meaning explicitly as `direct_dependencies`; the theory verifier derives the transitive closure.
2. Give assertion signatures a stable `interface_digest`, separate from a theorem proof's
   `implementation_digest`.
3. Introduce read-only `Theory` / `VerificationEnvironmentLock`: the former organizes language, calculus,
   assertion interfaces, and imports; the latter records the exact language, calculus, interfaces, imports,
   assertion profile, `TrustPolicy`, and verification-protocol version selected for verification. The assertion
   profile only restricts “which assertions may be applied”; it cannot grant trust to an unproved theorem.
4. `Theory.verify_all()` verifies every theorem implementation according to the dependency DAG. Default trust
   roots are only primitive declarations explicitly approved by `TrustPolicy`; a local theorem must have a
   verified implementation. An external theorem may come only from a digest-matching verified dependency
   archive, or be explicitly designated an oracle by an advanced policy and included in the trust report.
   Missing implementations, digest mismatches, and cycles must be rejected.
5. The verification result reports actual direct dependencies, the transitive theorem closure, and the final
   assumption/trust closure.

The current `DefinitionDecl` is merely a separately classified premise-free assertion; `kind="definition"` does
not itself prove conservativity. If accepted by policy, it must still appear as an explicit assumption in the
trust closure unless a future conservativity protocol supplies a certificate.

The mathematical implementation content identity of a proof should be separated from verification policy:

```text
implementation_digest
  = H(theorem interface + concrete proof DAG + replay context
      + exact referenced assertion interface requirements)

verification_digest
  = H(implementation_digest + verification_environment_lock_digest)
```

The same proof DAG remains the same implementation under different audit policies, but does not represent the
same verification result. `verification_digest` is only a verification-result identifier/cache key, not the
verification process itself, a digital signature, or a certificate usable apart from its report.

### 3.3 The Existing Exchange Object Is Executable Python, Not a Proof Archive

The current canonical helper only performs `Mapping -> JSON bytes -> SHA-256`. Although internal canonical
projections have version fields, there are still no public normative archive bytes, strict decoder, wire schema,
or accept/reject vectors. Generated packages reconstruct `PROOFS` by importing Python modules and executing
`prove_*()`. This works for trusted build pipelines, but is not a boundary for cross-organization exchange,
untrusted input, or long-term archival.

The first exchange format does not need a general-purpose binary encoding. Strict canonical JSON is sufficient
as the first normative encoding:

The following `VerificationEnvironmentLock` and `ProofArtifactV1` are advanced wire concepts and do not count
against the ordinary author's concept budget:

```text
ProofArtifactV1
  schema version
  VerificationEnvironmentLock
  theorem interface/ref
  active DV / replay context
  ordered applications:
    assertion interface ref
    premise positions
    complete substitution
  root position
  optional non-semantic provenance companion data
```

`result`, `satisfied_distinct`, and direct dependencies are produced by the verifier, not authoritative facts in
the packet. If cached values are carried for debugging or speed, the verifier must recompute and compare them,
and the cache does not enter the implementation content identity.

The boundary from wire data to a public object must be:

```text
strict decoder
  -> private unchecked packet
  -> replay recomputes result, DV evidence, and dependencies
  -> produce a public Proof only after success
```

This is not a second public Proof DAG. The unchecked packet is only the decoder's short-lived internal result and
can never masquerade as `ElaboratedProof`.

The codec must provide:

- a versioned schema and domain-separated digest;
- rejection on error for an unknown version, unknown/missing field, duplicate key, or malformed ID;
- no Python repr, pickle, callback, `SymbolId`, or absolute workspace path;
- deterministic map/array ordering and byte-identical round trips;
- resource limits on term depth, step count, string/collection sizes, and total bytes;
- positive and negative golden vectors reproducible by a second minimal verifier implementation.

`VerificationEnvironmentLock` only records content and policy requirements; it neither materializes dependency
content nor states that verification succeeded. A self-contained archive must embed the interface/implementation
closure needed for verification; a thin archive must obtain exact content through a content-addressed resolver.
Any missing resolver entry or digest mismatch is rejected on error.

A complete theory exchange can use the same envelope to carry interfaces, import locks, trust-root declarations,
and theorem implementations. A single-theorem archive is a slice of the dependency closure and needs no second
proof semantics. Provenance, source maps, narrative, signatures, and build records are linked through the subject
digest and do not contaminate proof content identity.

### 3.4 `ProofDraft` Is Not a Partial Construction State

The current `ProofDraft` requires that:

- every step already has a concrete assertion, complete premises, complete substitution, and result;
- premises may refer only to existing steps;
- step IDs are consecutive `<proof>/step:<index>` values;
- any undetermined schema variable fails immediately.

It has no goal, hole, metavariable, or constraint, nor a stable state digest suitable for search. Calling public
`apply_assertion()` repeatedly on the same immutable `ProofDraft` can form functional branches, but each call
copies the tuple and rescans the prefix, and there is no goal, complete environment lock, or state digest; it is
therefore unsuitable as a search boundary. `ProofAuthor` separately uses Python object identity to determine
whether a step belongs to the current authoring interface. This is a concise, safe linear façade, but cannot
itself persist or branch across processes.

The improvement is not to place every incomplete object in `ProofDraft`, but to add a thin `ProofState`:

- an immutable snapshot;
- public `goals`, `is_complete`, and a conservative exact `snapshot_digest`;
- value-based `GoalId` / `StepRef`;
- internally locked Theory/assertion-profile references, plus metavariables and equality/sort/DV constraints;
- `finish()` produces the existing complete proof only after every goal and constraint is closed;
- the old `ProofDraft` can gradually become internal `_CheckedProofPrefix`, with an alias retained during the
  compatibility period.

The verifier's hole-free `Term` must remain only `Var | App`. Construction-only `MetaTerm`, `MetaStore`, and
`ConstraintStore` must never leak into the final proof or the verifier's term union. Public `Goal` is only a
read-only/opaque view: initially it need only expose a `GoalId`, rendered target, and limited kind/head queries,
then pass the ID back to `refine()`; it does not promise to expose a public `Judgment` union containing
`MetaTerm`.

Immutability is the observable contract; whether the implementation copies containers, uses structural sharing,
or uses an arena is determined by branch benchmarks and is not promised in the v1 API.

### 3.5 Current Application Failures Are Unsuitable for Search

Existing assertion application mainly raises `AssertionApplicationError` with text. Humans can read it, but
search, batched candidates, repair, and training data need stable classifications such as:

```text
unknown_assertion
profile_forbidden
premise_arity_mismatch
unification_conflict
underdetermined_substitution
sort_mismatch
target_mismatch
missing_distinct_pair
dependency_unverified
```

Internally, a concrete application checker independent of `ProofDraft`/`StepId` should be extracted.
`ProofAuthor.use()`, verifier replay, and `ProofState.finish()` must share it for their final unified validity
decision. Backward `refine()` instead uses a constraint-generating elaborator to produce metavariables and
residual constraints; once a partial application closes, it must be reified and pass the same concrete checker
before entering the final proof. The two paths may share term matching, substitution, and DV primitives, but must
not pretend that incomplete refinement and a concrete validity decision are the same execution path.

---

## 4. Minimal APIs for the Four Classes of Requirements

| Requirement | Reusable current components | Largest deficiency | Minimal public improvement |
|---|---|---|---|
| Verification | application kernel, replay, calculus/catalog digests, and profile checks | construction/digest conflated with verified status; theorem dependency closure not verified | `Theory.verify()`, `verify_all()`, structured report, exact lock |
| Proof construction | concise default path through `ProofAuthor.use()/qed()` | too many environment parameters; no genuine partial state | `Theory.prove()` binds the environment; only advanced users use `ProofState` |
| Search | typed signatures, functional draft branches, shared final validity decision | expensive branch copying/rescanning; no goals/refinement, locked state content identity, or machine-readable failures | reuse `ProofState.refine()`; leave frontier/scoring to the search engine |
| Exchange | stable nominal identifiers and versioned internal canonical projections for digests | no public wire schema/codec/decoder or complete verification environment lock; producer Python must execute | `Theory.load/save` plus a strict normative archive format; load must verify |

### 4.1 Verification

Verification has two levels, although the ordinary API can expose one entry point:

```text
local replay
  checks every proof step against exact assertion interfaces

theory closure verification
  recursively checks every referenced theorem implementation, terminating at declared trust roots
```

`Theory.verify(proof)` checks the required closure by default. Advanced options may request a full trace,
incremental closure verification after cached dependencies, or backend-conversion/Metamath evidence; the default
behavior must be safe and must not require users to assemble a calculus, catalog, and assertion profile.

### 4.2 Proof Construction

A complete forward proof does not need a goal/hole API. Retain:

```python
mid = author.use(assertion, *premises, target=None, subst=None)
proof = author.qed(mid)
```

Only underdetermined or backward construction enters:

```python
state = THEORY.start(signature)
goal = state.goals[0]
outcome = state.refine(goal.id, assertion, subst=None)
```

`refine()` matches the assertion conclusion against the goal; assertion premises produce ordered subgoals, and
undetermined schema variables remain in the internal constraint store. Failure returns only a structured
diagnostic; because the input state is immutable, the caller need not receive a duplicate “unchanged state.”

### 4.3 Search

The core library is responsible only for deterministic state transitions, not search algorithms:

```text
ProofState + RefineRequest
        -> RefineSuccess(new state, created/closed goals)
         | RefineFailure(code, details)
```

Calling `refine()` multiple times from the same immutable state creates branches; retaining the old state is
undo, so v1 needs no `fork()` or `undo()` methods. The final proof extracts only the root-reachable closure;
failed exploration remains in the external search arena.

Initially, the only guarantee is that equal canonical snapshot bytes have equal `snapshot_digest` values. This
is a conservative state-snapshot content identifier, not a promise of mathematical state equivalence or search
deduplication across lineages; equivalent states may have different digests. Alpha-equivalence, proof
equivalence, and aggressive normalization do not enter the public identity contract until real corpus data
demonstrates a benefit.

The first phase needs only a read-only candidate index derived from Theory by conclusion judgment kind, head
constructor, and premise count. It is a rebuildable internal index or search companion data and does not enter
the semantic catalog/digest. Embeddings, historical frequency, and model ranking are likewise advisory companion
data linked by digest.

### 4.4 Exchange

Exchange should distinguish:

- `Proof`: the complete mathematical proof DAG;
- `VerificationEnvironmentLock`: the exact content and policy requirements needed to interpret and verify it;
- archive envelope: schema, optional dependency payload, and non-semantic metadata.

All three may be placed in one file, but must not therefore be conflated into one semantic digest. The default
loader must decode, check limits, resolve the lock, and verify the closure before returning an ordinary `Proof`.
Only an advanced API may expose an unchecked packet.

A self-contained archive supplies the closure in the file; a thin archive requires the caller's resolver to
supply it by digest. A loader must reject a `VerificationEnvironmentLock` whose content cannot be resolved.

The first version promises only a lossless round trip between the ProofScaffold semantic model and Metamath
backend conversion. Lean, Coq, Isabelle, or SMT adapters must declare their fidelity level and reconstruction
requirements; do not first design a semantic union of all proof systems.

---

## 5. Necessary Internal Layers, but Not Three User APIs

The three object kinds have conflicting invariants, so internal boundaries remain necessary:

| Internal layer | Core invariants | Visible to ordinary users? |
|---|---|---|
| Construction / `ProofState` | permits goals, metavariables, and constraints; atomic actions; persistent branching | exposed on demand only for interaction and search |
| Complete Proof / DAG | complete, typed, resolved, acyclic, root-reachable; concrete assertion applications only | yes, public as `Proof`; evolved from current `ElaboratedProof` |
| Execution representation | inference-free, resolved references, linear; `SemanticReplayPlan` remains backend-neutral, while the bound legacy proof / `.mm` is backend-specific | no; initially reuse the existing two-stage path |

Orthogonal to these are not a huge fourth IR, but two thin objects:

```text
TheoryInterface / VerificationEnvironmentLock
  provides the semantic environment and exact content and policy requirements

Companion data
  source map, provenance, narrative, search score, embedding, timing
```

A recommended data flow is:

```text
                 ordinary author
                    │
              ProofAuthor façade
                    │
                    v
Theory ────────> complete Proof ────────> verify / save
   │                  │
   │                  v
   │          internal replay/backend conversion ─────> .mm / verifiers
   │
   └────> ProofState ── refine ──> ProofState
              ^                         │
              └──── search engine ──────┘
```

There is no workflow in which users manually “convert Construction IR to Proof DAG, then to Execution IR.”
`finish()`, `verify()`, and backend tools cross the boundaries automatically.

---

## 6. Identifiers, Identity, Digests, and Caching

### 6.1 Separate Nominal Identifiers from Content Compatibility

- language, sort, constructor, assertion, and theory use stable, readable nominal identifiers;
- an interface digest expresses exact content requirements for a given nominal identifier;
- a theorem signature's `interface_digest` is separate from a proof body's `implementation_digest`;
- the assertion profile and trust policy enter `VerificationEnvironmentLock` and, through its digest, the
  verification digest; they do not alter the implementation content identity of an unchanged proof DAG;
- source paths, authors, models, times, notes, rendering, and backend tokens do not enter proof content identity.

### 6.2 StepRefs and Snapshots Are Not Global Mathematical Identifiers

Proof-local canonical positions suffice for references in v1 archives. There is currently no need to turn every
step into a global Merkle object. If future incremental-verification data shows that a node-level cache is a
major benefit, add domain-separated node digests then; do not prematurely promise subgraph equivalence across
proofs.

`GoalId`, `MetaId`, and `StepRef` in a construction state need only be value-stable within a snapshot lineage,
not permanently globally unique. `snapshot_digest` covers only the exact canonical snapshot and does not perform
cross-lineage deduplication.

### 6.3 Digests Prove Only Equal Content

No content digest can replace a verifier result. APIs and documentation must not use `semantic_digest` to imply
“verified.” Retain legacy `semantic_digest` during the compatibility period; the new versioned
`implementation_digest` uses a different digest domain/canonical projection, includes exact assertion-interface
requirements, and may exclude derivable caches. It therefore need not equal the old value and cannot merely be
an alias for the old field. During migration, a verification report may carry both and explicitly state
`verification_environment_lock_digest` and `verification_digest`.

---

## 7. Performance Must Be Measured at the Real Boundaries

The existing four-domain benchmark is important, but the next phase must time the following separately rather
than calling all of them validation:

1. Python/build-artifact import or JSON decoding;
2. theory interface/lock resolution;
3. proof-object structural validation and digest computation;
4. assertion-by-assertion semantic replay;
5. transitive theorem closure verification;
6. backend conversion and the independent Metamath verifier;
7. warm incremental verification;
8. scalar `refine` throughput, and batch throughput after introducing a batch API;
9. archive codec throughput, bytes, and peak RSS.

Every benchmark must record the source commit, ProofScaffold/transpiler commit, archive digest, Python/runtime,
cold/warm cache state, wall/user/sys time, peak memory, and the median of at least three runs. Comparing only
object counts or digests after import must not be labeled complete proof verification.

Public `apply_assertion()` currently creates a new tuple and has `ProofDraft` rescan the prefix each time, so the
naive cumulative cost for long proofs may reach O(n²); the mutable fast path in `ProofAuthor` already avoids the
main cost for linear generation. Future `ProofState` promises only immutable observable behavior; whether to use
structural sharing or an arena must be determined by branch benchmarks.

A compact Execution IR, batch packet, or binary codec enters design only after these measurements confirm that
JSON decoding, replay, or `.mm` backend conversion is the principal bottleneck. Performance targets must first
come from data; do not freeze an ISA because “hardware might need it in the future.”

---

## 8. Minimal Migration Order

Migration should consist of small vertical slices, not a one-shot implementation of a complete IR blueprint.

### 8.1 Shared Prerequisite: Stabilize the Unified Validity Decision

1. Add a read-only `Theory` façade with a verification environment lock, uniformly binding language, calculus,
   catalog, assertion profile, `TrustPolicy`, and theorem registry; existing low-level objects remain available.
2. Extract from current application code a concrete checker independent of `ProofDraft` and positional StepIds,
   and define stable diagnostic codes. It becomes the shared unified validity decision for `ProofAuthor.use()`,
   proof replay, and future `ProofState.finish()`.
3. Promote public `verify_proof()` from `build_semantic_replay_plan()`; backend conversion consumes verified
   replay, and the replay-plan builder no longer doubles as the sole verification entry point.

Once these three items are stable, verification/exchange and construction/search may proceed in parallel; the
latter need not wait for all archive-exchange work to finish.

### 8.2 Track A: Verification and Exchange

1. **A1, local replay:** return a structured `VerificationReport`, provide an optional step trace, and establish
   an assertion-by-assertion performance baseline.
2. **A2, theory closure:** distinguish assertion `interface_digest`, proof `implementation_digest`, direct
   dependencies, transitive theorem closure, and trust closure; implement `Theory.verify_all()`, rejecting on
   error for missing implementations, cycles, unverified dependencies, oracles, and policy violations.
3. **A3, data archives:** unify the Term/Judgment/Signature/Proof canonical projections; implement a strict
   decoder, wire schema, resource limits, and golden accept/reject vectors; replay through a private unchecked
   packet adapter into the existing complete proof, without creating a second public DAG.
4. The first canary requires only round-trip and replay in a new process without importing the producer package.
   A second minimal codec/verifier implementation is a release gate before schema freeze, but does not block the
   A1 API.

### 8.3 Track B: Construction and Search

1. Around the shared checker, add a constraint-generating elaborator and minimal `ProofState`, opaque `Goal`,
   `start/refine/finish`, and exact `snapshot_digest`.
2. Initial constraints include only typed term equality/unification, sorts, and the existing DV contract; do not
   prematurely add freshness or a general-purpose plugin framework.
3. `ProofState` uses lineage-scoped value references; on `finish/save`, normalize root-reachable steps into
   proof-local canonical positions, and store only those positional references in the archive. `ProofAuthor` may
   continue using Python object handles for safe, concise façade ownership checks; the existing default path need
   not accept arbitrary external `StepRef` values.
4. Make `ProofAuthor` reuse the shared checker for its final unified validity decision so generated code needs no
   rewrite.
5. Derive a minimal conclusion-head query index from Theory; decide on structural sharing, arenas, and
   `refine_many()` only after scalar branch benchmarks.

### 8.4 Later: Measurement-Driven Optimization and Ecosystem Capabilities

Only after the preceding correctness and performance data is stable should evidence select among:

- node-level hashes and an incremental verification cache;
- proof repair and semantic diff;
- streaming/NDJSON or compact binary archives;
- batch candidate packets and a specialized Execution IR;
- dependency-closure slicing and signed certificates;
- a more complete module/package publication envelope.

---

## 9. Acceptance Criteria

### Verification and Exchange

- When an assertion reference, premise, substitution, DV context, or root is modified, the public verifier
  rejects it with a stable code; possession of a digest does not affect the result. Missing theorem
  implementations, digest mismatches, dependency cycles, and undeclared oracles are likewise rejected, and the
  report distinguishes direct, transitive, and trust closures.
- The verifier can check an archive in a new process without importing the producer's Python package. A
  self-contained archive carries its closure; a thin archive is rejected when its resolver lacks an entry or
  returns a digest mismatch.
- Unknown/missing fields, duplicate keys, unknown schemas, malformed IDs, and resource bombs are all rejected.
  Before schema freeze, a second minimal implementation must reproduce canonical bytes and golden vectors.
- Changes to provenance/source maps do not affect the implementation digest; changes to a proof body do not
  affect the theorem interface digest; the assertion profile, trust policy, and verification result are not
  mixed into proof content identity.

### Construction, Search, and Usability

- Existing `ProofAuthor.use()/qed()` code remains usable. Ordinary authors see only
  `Theory -> ProofAuthor -> Proof`; consumers need only `Theory.verify/load/save`; unchecked packets are hidden
  by default.
- `ProofState` can represent an open goal and underdetermined substitution; `Goal` is an opaque view, and final
  `Proof` contains no holes/metavariables. The same complete action sequence through `ProofAuthor` and
  `ProofState.finish()` yields the same implementation digest.
- Multiple branches can be produced from the same immutable state without side effects; failure returns only a
  diagnostic. Equal canonical snapshot bytes have equal digests, but cross-lineage equivalence deduplication is
  not promised. Frontier, cost, and model scores do not enter state content identity.
- If a batch transition is later added, its itemwise results must agree with scalar transitions; until then,
  batching is not a v1 acceptance prerequisite.

### Performance

- Import/decode, structure/digest, semantic replay, theory closure, backend conversion, independent verifier, and
  incremental paths are timed separately; a lightweight object/digest check must not be labeled complete
  verification.
- New abstractions must not add ceremony to the default proof path; structural sharing, binary codecs, and
  execution packets must be justified by benchmarks.

---

## 10. Explicit Non-Goals

To prevent IR inflation, none of the following may be made a P0/P1 prerequisite in the near term:

- adding `Hole | MetaVar` to `Term` or final `Proof`;
- simultaneously exposing four object graphs for Construction IR, Search IR, Proof DAG IR, and Execution IR;
- creating a Proof DAG parallel to `ElaboratedProof` with duplicate fields;
- putting the frontier, ranking, embeddings, cost-to-go, or model state into the semantic core;
- freezing a Proof VM, binary ISA, FPGA packet, or CBOR/Protobuf schema now;
- deploying a global Merkle store now or promising canonical identity for proof/alpha equivalence;
- designing a general-purpose framework in which every constraint type is pluggable;
- designing a lowest common denominator for all Lean/Coq/Isabelle/SMT semantics;
- mixing source maps, authors, models, times, or narrative into the proof semantic digest;
- treating generated Python import as an exchange, verification, or long-term archival protocol;
- inflating existing legacy `skfd.proof.ir` into the new semantic IR merely to unify names;
- building an editable general-purpose Package/Module/Provenance IR before real performance data shows it is
  necessary.

---

## 11. Answers for Broader Scenarios

Once the four boundaries of verification, construction, search, and exchange are established, other scenarios
should be derived capabilities rather than forces that shape the v1 core backward:

- normalization, compression, diff, repair, and dependency minimization derive from the complete Proof DAG and
  dependency data;
- IDEs, LLM trajectories, candidate validation, and curricula derive from `ProofState` transitions and
  structured diagnostics;
- publication, citation, provenance, narrative, and source maps derive from archive companion data;
- distributed frontiers, GPU/FPGA packets, and hardware execution derive from backend conversion of verified
  Proofs;
- knowledge graphs, proof mining, and historical analysis derive from read-only views of proof/theory archives.

The final architectural principle is neither “use one flat IR for everything” nor “build a separate IR for every
scenario,” but:

> Use one concrete assertion-application kernel and one constraint-generating elaborator to maintain the
> mutually distinct invariants of partial state, complete proof, and execution representation; then use a
> minimal façade so that each class of user sees only the entry points it needs.

The most valuable near-term work is not adding more IR terminology, but closing this path for the first time:

```text
write a proof simply
    -> verify it deterministically under an exact theory
    -> save it as a versioned pure-data archive without executing producer Python
    -> load and reverify it in another process or implementation
```
