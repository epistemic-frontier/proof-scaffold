# Ontology Before Dependency: Knowledge Organization and Foundational Pluralism in Formal Mathematics

> Status: non-normative architectural and epistemological commentary (2026-07-20).
>
> Scope: rationale for treating human mathematical ontology as the primary
> principle of public knowledge organization, while treating proof-dependency
> DAGs and linear extensions as implementation and verification constraints.
>
> Relationship to current standards: this document deepens
> [Reference 014](014-module-partition-and-knowledge-classification.md),
> [Reference 015](015-setmm-linearization-empirics.md), and
> [Reference 016](016-mathbox-community-practice.md)
> and identifies a proposed revision to
> [Project 026 §1.2](../projects/026-package-evolution-standard.en.md).
> It does not by itself amend Projects 025–027 or
> [Terminology Standard 000](000-terminology.en.md).

---

## 0. Thesis: Ontology Organizes; Dependency Constrains

The public organization of a mathematical library should not be generated
from a proof-dependency DAG, and still less from one linear extension of that
DAG. A dependency graph records what a particular collection of proof
implementations needs in order to verify. It does not, by itself, record what
the mathematics is about, which concepts explain a result, which structures a
construction acts on, or which transformations make two bodies of knowledge
intelligible to one another.

The order of principles should therefore be reversed:

```text
curated mathematical ontology and knowledge views
        |
        v
public concept ownership, names, and facades
        |
        v
theory-scoped declarations and proof implementations
        |
        v
derived implementation/import/dependency DAGs and closure sets
        |
        v
backend linear extension, loading plan, and physical shards
```

This is not a proposal to weaken formal verification. It is a proposal to
stop asking verification metadata to perform a task for which it contains
insufficient information.

In this document, *ontology* has a deliberately modest meaning: a curated and
revisable account of mathematical concepts, structures, properties,
relations, constructions, transformations, and their identities. It does not
mean that the project must adopt OWL, RDF, or a complete metaphysical theory
of mathematical objects. *Epistemic organization* means the organization of
the ways in which those objects are understood, explained, compared, and
used. Ontology-first organization is a rule for the public knowledge surface;
it does not replace the formal language, calculus, logic, and theory that
determine whether a term is well formed or a proof is valid.

The resulting architecture separates five questions:

| Plane | Primary question | Principal output | Shape |
|---|---|---|---|
| Ontological and epistemic | What is this about, and how is it understood? | Concepts, facets, explanations, alignments | Overlapping graph; cycles allowed |
| Public knowledge interface | Where is it named and discovered? | Stable IDs, namespaces, facades | Curated primary projection |
| Formal perspective | In which language, calculus, logic, theory, and Foundation Unit is it stated? | Perspective-indexed declarations | Exact composition of layer contracts |
| Proof implementation | What is required to establish it here? | Proof DAG, dependency closure, and trust closure | DAG plus explicit closure sets |
| Physical execution | How is it loaded, cached, and emitted? | Shards and a topological linear extension | Derived and replaceable |

To avoid equivocation, this essay uses *knowledge view* for a human-facing
ontological and explanatory perspective, *formal perspective* for an exact
composition of `LanguageSpec`, `CalculusSpec`, logic, theory, and selected
Foundation Unit, and *foundation* for the background commitments that define
the latter's ambient language and valid derivations. These are working
distinctions for this essay, not new frozen terminology.

Under this model, “partition” is too narrow a word for the primary artifact.
A partition places each item in one exclusive block. A knowledge organization
plan needs one stable primary owner for storage and public naming, but it also
needs non-exclusive semantic facets and relations.

---

## 1. Why a Proof DAG Cannot Be a Taxonomy

### 1.1 What a proof edge actually means

An edge in the current graph means that one emitted proof refers to another
assertion. That is valuable and exact information, but it is relative to:

- the chosen proof rather than every possible proof;
- the chosen primitive and derived rules;
- the current library snapshot;
- the current backend encoding and formation infrastructure;
- the granularity at which assertions and modules were emitted.

Change the proof, factor out a glue lemma, replace a derived rule, or move to a
different foundation, and many edges change while the theorem remains about
the same mathematical subject.

The graph does not directly contain:

- conceptual identity or similarity;
- the distinction between a structure and a property of that structure;
- explanatory importance;
- analogy, generalization, specialization, or duality;
- the difference between a proof technique and the subject of a theorem;
- the community vocabulary by which mathematicians find and communicate an
  idea;
- alternative proofs that reveal different mathematical mechanisms.

A graph cut can therefore optimize an engineering cost while producing an
unintelligible public taxonomy. That is not a poor optimum. It is an optimum
of the wrong objective.

### 1.2 The set.mm evidence

[Reference 015](015-setmm-linearization-empirics.md) measures the mismatch on
the actual set.mm corpus:

- only roughly 7–11% of dependency edges remain within authored blocks;
- 71.7% of section pairs are not ordered by dependency even though the source
  file gives them a total order;
- a small set of proof-plumbing hubs absorbs a very large share of references;
- surviving proofs rewire at a measurable yearly rate even inside the settled
  corpus.

These measurements do not imply that authored sections are perfect
categories. They show that proof locality is too weak and too hub-dominated
to be the generator of semantic boundaries. They also show why a
linearization is especially misleading: a total source order records hundreds
of thousands of precedence choices that proof dependency does not require.

[Reference 016](016-mathbox-community-practice.md) supplies the complementary
governance evidence. The durable organizational achievement of the mathbox
institution is not a graph cut or a physical file split. It is a declared
social and dependency membrane, together with ownership, review, promotion,
and migration practices.

### 1.3 Quotient cycles are not proof cycles

The assertion graph may be acyclic while a graph obtained by grouping
assertions into human topics has cycles. This happens when two conceptually
coherent topics are developed in interleaved stages. The quotient cycle says
that the chosen implementation modules are too coarse to form an executable
DAG. It does not prove that the concepts are wrongly related or that one topic
must be renamed as part of the other.

The first response should be to separate public facades from implementation
shards, split implementations by dependency stage, extract a genuine shared
interface theory, or introduce a bridge domain. Semantic reclassification
should be the last response, not the automatic one.

---

## 2. Proof, Understanding, and Mathematical Communication

William Thurston's
[“On Proof and Progress in Mathematics”](https://doi.org/10.1090/S0273-0979-1994-00502-6)
asks what changes when the objective of mathematics is framed not as theorem
production but as the effort to “advance human understanding of
mathematics.” His answer is not an argument against rigor. He explicitly
defends careful proof and formal investigation. His point is that proof is
one component of a larger practice of forming, communicating, testing, and
reorganizing mathematical understanding.

Thurston's example of the derivative is particularly relevant. A derivative
may be understood symbolically, geometrically, infinitesimally, dynamically,
as a rate, or as a best linear approximation. These are not merely rival
strings for one definition. They are different cognitive and explanatory
access routes that mathematicians reconcile and use in different situations.
He consequently asks mathematicians to value “different ways of thinking
about the same mathematical structure.”

This is cognitive and representational plurality around mathematics, not yet
an argument for plurality among incompatible logical foundations. The latter
is the further metamathematical problem taken up in Section 9.

A formal library has at least two distinct obligations:

1. **Justificatory obligation.** It must make derivability, assumptions,
   dependencies, and trust boundaries mechanically checkable.
2. **Epistemic obligation.** It should help people and agents discover what a
   result concerns, why it matters, how it relates to familiar structures,
   which transformations explain it, and which methods expose different
   aspects of it.

The proof DAG is indispensable for the first obligation and radically
incomplete for the second.

This incompleteness becomes worse when the formal trace is treated as the
public organization. A high-frequency syllogistic lemma can become
structurally central while carrying almost no topical meaning. Conversely, a
conceptual correspondence may be represented by a small number of low-frequency
theorems. A dependency-based classifier systematically promotes plumbing and
demotes explanation.

Thurston also anticipated the engineering difficulty. He observed that
large-scale formal completeness turns many locally reasonable formalization
choices into a vast compatibility problem. This is an argument for making
those choices explicit and modular, not for forcing one early choice to
govern every later representation.

Formal proof and human ontology should therefore be complementary records:

```text
proof dependency graph and trust closure
  establish that an assertion implementation is valid under explicit commitments

knowledge graph
  records what the assertion concerns and how it supports understanding
```

Neither should impersonate the other.

---

## 3. What Ontology-First Organization Means

### 3.1 Objects first; facets around them

The proposed starting vocabulary is:

- **concepts and structures** — the mathematical objects and organizing
  forms under discussion;
- **properties and invariants** — what may hold of those objects and what is
  preserved;
- **relations and correspondences** — how objects, properties, or theories
  are connected;
- **constructions and transformations** — how objects are produced, changed,
  transported, decomposed, or compared;
- **methods and explanations** — characteristic ways of proving, computing,
  or understanding.

These should not automatically become universal top-level directories named
`properties/`, `methods/`, or `transformations/`. Such directories would
be new catch-all bins. The primary path should normally be anchored in a
mathematical subject and its defining objects, with the other categories
represented as typed facets and, where coherent, local submodules.

For example:

```text
group_theory/
  groups/
  homomorphisms/
  subgroups/
  quotients/
  actions/
```

is usually more intelligible than a global split into
`structures/groups`, `relations/homomorphisms`,
`properties/normality`, and `methods/quotienting`. The latter relations
remain valuable as ontology edges and search facets.

### 3.2 Primary ownership and plural membership

Every public declaration should have:

- a stable identifier independent of file path;
- one canonical public owner for naming, storage, and migration;
- a one-sentence definingness criterion for that owner;
- zero or more non-exclusive `about`, `has_property`, `relates_to`,
  `constructs`, `transforms`, `generalizes`, `specializes`,
  `explained_by`, and `proved_by_method` relations.

Exact primary ownership remains important. Without it, two packages may
silently define competing canonical objects. But exclusive storage must not
be confused with exclusive meaning. A theorem about a correspondence between
groups and topological spaces belongs to one canonical public location while
remaining discoverable from both subjects and from the correspondence itself.

### 3.3 Curated semantics, derived evidence

Ontology claims should be curated and reviewable. Mechanical evidence may
challenge them:

- a claimed concept module may have no definable membership criterion;
- a purportedly general method may only occur in one narrow domain;
- a relation may hide an unacknowledged stronger theory;
- a public owner may impose a costly or cyclic implementation boundary.

The evidence should trigger review, not silently rename the knowledge. Graph
metrics are diagnostics for the ontology; they are not its source of truth.

---

## 4. Four Responsibilities That Must Not Be Collapsed

The language–calculus–logic–theory separation of
[Reference 011](011-language-as-first-class.en.md), the authoring discipline
of [Reference 012](012-defining-structures-axioms-and-proofs.en.md), and the
interface–implementation–verification separation of
[Reference 013](013-proof-api-for-verification-construction-search-and-exchange.en.md)
together imply four organizational responsibilities.

### 4.1 Knowledge ontology and navigation

This layer answers what a declaration is about and how a user finds it. It
owns stable concept IDs, public names, facets, explanatory links, and
community vocabulary. It does not certify proofs.

### 4.2 Public assertion and theory interfaces

This layer states the exact formal language, judgment, schema variables,
premises, conclusion, and theory requirements of an assertion. It is where
informal subject ownership becomes a precise, formal-perspective-scoped
declaration.

### 4.3 Proof implementations and verification closure

This layer supplies a concrete proof, exact assertion requirements,
transitive theorem dependencies, active variable conditions, trust policy,
and verification-protocol requirements. It determines what must be loaded and
checked; the verifier implementation and run outcome belong in a separate
verification report, certificate, or provenance record.

### 4.4 Physical sharding and backend order

This layer selects files, generated modules, caches, build batches, and a
topological linear extension for Metamath emission. It is replaceable without
changing the stable public identifier or formal assertion interface.

The distinction changes how difficult examples are handled. Suppose a
theorem whose statement concerns prime numbers is proved using complex
analysis. Its public discoverability remains under number theory, possibly in
an analytic-number-theory bridge domain. Its selected proof implementation
records the analysis dependency and the resulting trust closure. If the
statement is exposed through a weaker interface theory, that interface and
its presentation in the stronger theory must be explicit.

Semantic ownership must never be used to hide formal strength. A theorem
cannot be advertised as derivable in a weak theory merely because its
statement uses weak vocabulary. Conversely, a strong proof dependency need
not erase the subject of the theorem from the public knowledge organization.

This yields the proposed revision to Project 026 §1.2:

> Public declaration and knowledge ownership follow ontology; proof
> implementation and `requires` follow proof dependencies.

That sentence is a proposal, not current Project 026 policy.
Adopting it would require amending both Project 026 §1.2 and the frozen
`Module` row in Terminology Standard 000, then extending Project 025 and the
plan-v3 schema to distinguish a public declaration owner from an
implementation provider. Project 026's P3, P4, and P7 acyclicity,
completeness, and quotient-DAG requirements would continue to govern the
implementation/import projection.

---

## 5. Why Lazy Elaboration Changes What Is Feasible

[Project 025](../projects/025-semantic-source-surface.en.md) provides the
enabling mechanisms:

- assertions are module-level handles rather than string lookups;
- cross-module proof references use function-local imports;
- importing a package does not elaborate proofs;
- implementations are attached and cached lazily;
- manifests record ownership and interface digests;
- backend emission occurs after semantic registration.

Before these mechanisms, aligning public modules with build order reduced
import cost and avoided eager cycles. That engineering pressure made
dependency-shaped public organization understandable. It is no longer a good
first principle.

A future surface can instead use:

```text
ontology-shaped public facade
        |
        +-- assertion interfaces available immediately
        |
        +-- lazily attached implementation providers
                |
                +-- implementation-local imports
                +-- exact verification closure
                +-- backend emission data
```

This split is not fully represented by the current plan-v3 schema or generated
surface. In Project 025, partition ownership still determines module bindings,
and the import graph is designed to mirror proof dependency. Lazy elaboration
makes a follow-on design possible; it does not mean the follow-on design
already exists.

Lazy loading also does **not**:

- make a circular proof valid;
- remove the need for an acyclic verification closure;
- reconcile incompatible axioms;
- prove that two declarations in different foundations are identical;
- permit hidden dependencies or implicit trust roots.

It changes when implementation is loaded, not what the implementation means.

---

## 6. The Proper Role of the DAG

Once ontology and proof implementation are separated, the DAG regains a
clear and indispensable role.

From actual implementations the toolchain should derive or verify:

- direct assertion dependencies;
- transitive theorem closure;
- assumption and trust closure;
- implementation-local imports;
- build and elaboration order;
- cache invalidation;
- backend emission order;
- frontier-to-core membrane violations;
- unexpectedly expensive cross-concept dependencies.

The graph is therefore an executable contract and an audit instrument.

The ontology graph, by contrast, may overlap and cycle. “Dual to,”
“equivalent to,” “generalizes,” “represented by,” and “transforms into” are
not build edges. Even broader/narrower classification may coexist with
orthogonal facets. Requiring this graph to be a DAG would mistake a
navigational representation for a proof order.

Executable projections remain constrained:

1. a concrete proof graph is acyclic;
2. a selected verification closure is well founded relative to explicit
   trust roots;
3. generated implementation imports must be cycle-safe;
4. a Metamath artifact is emitted in a valid linear extension.

If an ontology-shaped public facade induces an implementation quotient cycle,
the preferred remedies are, in order:

1. split facade from implementation;
2. divide implementation into dependency stages behind the same facade;
3. factor a genuine common interface;
4. introduce a bridge domain;
5. only then revise semantic ownership.

The core/frontier membrane of Reference 016 remains valid. Maturity and
review policy are not generated by ontology alone. Ontology-first
organization changes the meaning of the public core; it does not abolish
governance or dependency discipline.

---

## 7. From a Partition Plan to a Knowledge-Organization Plan

The next artifact should extend rather than merely retune
`proof-partition-plan-v3`. In the provisional vocabulary below, a
*theory-scoped presentation* is a human concept presented within one exact
formal perspective. It is neither a backend `Binding` nor a proof
`Implementation`. A provisional shape is:

```json
{
  "schema": "knowledge-organization-plan-v1",
  "concepts": [
    {
      "id": "concept:word",
      "path": "combinatorics.words",
      "kind": "structure",
      "definingness": "finite ordered strings over an alphabet",
      "broader": ["concept:combinatorial-object"]
    }
  ],
  "formal_presentations": [
    {
      "id": "presentation:setmm:word",
      "concept": "concept:word",
      "formal_perspective": "formal-perspective:setmm-classical",
      "formal_symbol": "..."
    }
  ],
  "assertions": [
    {
      "id": "assertion:...",
      "primary_owner": "concept:word",
      "about": ["concept:concatenation", "concept:length"],
      "interface": "...",
      "implementation": "implementation:..."
    }
  ],
  "implementations": [
    {
      "id": "implementation:...",
      "requires": ["assertion:..."],
      "physical_shard": "...",
      "emission_order": "derived"
    }
  ],
  "alignments": []
}
```

`concept`, `theory-scoped presentation`, `formal perspective`, and
`alignment` are provisional terms in this essay. They are not additions to
Terminology Standard 000. If adopted as public architecture, they require a
separate terminology adjudication.

The plan should satisfy the following proposed invariants:

**K1. Stable concept identifier.** A concept ID is independent of its current
path and display name; it does not by itself assert a formal identity
relation.

**K2. Exact canonical ownership.** Every formal declaration has exactly one
canonical storage/public owner, while facet membership remains non-exclusive.

**K3. Ontology is curated.** The primary owner and semantic relations are not
generated from proof edges.

**K4. Formal entities are layer-scoped.** Sorts and constructors belong to an
explicit `LanguageSpec`; judgments and primitive rules to a `CalculusSpec`;
logical axioms to a logic; mathematical assertions to a theory; and notation
or backend spellings to their respective bindings. A formal perspective
composes these layer contracts without collapsing them.

**K5. Interface and implementation are separate.** Replacing a proof does
not move the public subject or change the assertion interface unless its
formal requirements change.

**K6. Dependencies are complete.** Every proof edge is reflected in the
implementation closure; no ontology relation grants proof authority.

**K7. Graph kinds are explicit.** Ontology relations may overlap or cycle;
proof-dependency and implementation-import graphs obey their acyclicity
rules, while dependency and trust closures remain explicit and complete.

**K8. Linearization is derived.** Source and emission order determine neither
semantic classification nor stable identifiers.

**K9. Evolution preserves references.** Rename, split, promotion, and
bridge-domain extraction retain stable IDs and machine-readable migration
records.

**K10. Structural metrics are reports.** Cut size, hub-filtered cohesion, and
module size may identify risks but do not assign concepts or names.

Project 026's definingness checks, stable migrations, bridge domains,
frontier/core promotion, and exact coverage remain useful. The proposed
change concerns what exact coverage means: it governs canonical declaration
and storage, not all semantic membership.

---

## 8. Operational Consequences and a Pilot

The principle should be tested on a difficult vertical slice before replacing
the existing full-corpus plan.

The best current canary is the cluster connecting words, cyclic shifts,
necklaces, finite counting, and prime-number arguments. It already exposes
the failure modes of section ownership, cross-domain dependency, and
bridge-domain classification.

### Phase A — curate without the DAG

Create a small concept graph for:

- words and alphabets;
- concatenation, subwords, prefixes, and cyclic shifts;
- necklaces and orbit-like equivalence;
- counting transformations;
- prime-dependent results and arithmetic-combinatorics bridge domains.

Write definingness criteria and typed relations before inspecting dependency
edges.

### Phase B — map theory-scoped presentations

Assign existing labels to canonical concept owners and additional facets.
Keep label identifiers and source order unchanged.

### Phase C — overlay implementation dependencies

Derive imports from the selected proofs. Record where the graph:

- agrees with the ontology;
- crosses a concept boundary for a genuine bridge-domain candidate;
- crosses because of a generic glue lemma;
- forms a quotient cycle that requires implementation splitting.

### Phase D — exercise the lazy facade

Generate ontology-shaped public modules with lazy proof providers. Resolve
implementation cycles behind facades without changing concept ownership.

### Phase E — emit and compare

Require deterministic generation, exact ownership, complete dependency
closure, valid Metamath emission, and independent verification. Compare the
old and new plans on:

- whether a reader can predict where a concept or theorem is found;
- whether every module has a clear membership sentence;
- whether bridge domains and cross-domain dependencies are explicit rather
  than hidden;
- whether proof changes leave public ownership stable;
- whether imports and verification remain complete;
- whether loading and generation regress materially.

Raw cut minimization should appear only as a diagnostic. The pilot succeeds
if the public organization becomes more intelligible without weakening the
formal closure.

[Project 027](../projects/027-prelude-boundary-rfc.en.md) remains orthogonal.
Ontological centrality, explanatory value, or high citation frequency does
not by itself place content in Prelude. Prelude is a foundation boundary with
separate axiomatic, closure, and stability costs.

---

## 9. The Metamathematical Limit: One Engineering Framework, Many Foundations

The ontology-first proposal exposes a harder problem. Once organization is no
longer dictated by one emitted DAG, whose ontology organizes the library?
Different logical foundations are not always alternate compilers for the same
pre-existing objects. They may be different mathematical perspectives on
objecthood, identity, existence, construction, and proof.

### 9.1 Foundations alter what is seen

Classical and constructive logics disagree about which existence claims carry
constructions and which principles may be used without evidence. Set theory
and type theory organize objecthood differently: membership, typing,
universes, equality, and quotient formation do not play interchangeable
roles. Proof relevance and proof irrelevance change what information a proof
contains.

The
[Homotopy Type Theory book](https://homotopytypetheory.org/book/)
is a concrete warning against backend reductionism. Univalent foundations
relate identity of types to equivalence through the univalence axiom; suitable
structure identity principles yield analogous consequences for structured
types. Higher identity structure and higher inductive types affect the
ontology expressed by the foundation. A translation into ordinary set-level
or 0-truncated semantics may preserve selected theorem-level facts while
forgetting path or higher structure intrinsic to the source formal
perspective. That
possible loss, rather than set-theoretic metamodeling as such, is the
architectural warning.

Thus a single prose concept such as “group,” “quotient,” “equality,” or
“finite set” cannot automatically serve as one formal object across all
foundations.

### 9.2 What foundation-independent engineering can mean

There is strong precedent for a shared infrastructure that does not impose
one object logic.

Goguen and Burstall's
[institution theory](https://doi.org/10.1145/147508.147524)
abstracts a logical system into signatures, sentences, models, and a
satisfaction relation stable under change of notation. It shows how theory
structuring can be studied without fixing one particular logic. But this
neutrality is achieved by parameterizing the syntax and semantics of each
logic. It does not manufacture a semantics above all foundations.

The
[LF logical framework](https://doi.org/10.1145/138027.138060)
shows how shared proof infrastructure can represent multiple object logics,
but an encoding has an adequacy obligation. Successful parsing into a common
term language is not enough; the representation must preserve the intended
judgments, binding, substitution, and proofs.

[MMT](https://uniformal.github.io/doc/philosophy/articles/mmt.pdf)
provides the closest architectural precedent. It represents foundations,
logics, and mathematical theories uniformly as theories related by
meta-theory links and theory morphisms. It also recommends weak interface
theories through which multiple stronger foundations can realize the same
problem. At the same time, MMT explicitly recognizes that importing and
aligning mature libraries is difficult, that translations may be partial,
and that the semantics of ultimate foundations is supplied externally.

These precedents suggest a precise interpretation:

> Foundation-independent infrastructure is a common protocol for declaring
> local semantics and justified cross-foundation relations, not a universal
> semantics that erases foundational difference.

### 9.3 A federated architecture

One engineering framework can host multiple foundations if it separates:

| Object | Role |
|---|---|
| Concept hub | Human-facing topic and cross-view navigation; no proof authority |
| Knowledge view | A named ontological and explanatory perspective |
| Theory-scoped presentation | A concept presented in one exact formal perspective; neither a backend binding nor a proof implementation |
| Assertion interface | A statement relative to one theory-scoped presentation |
| Proof implementation | A proof, dependency closure, and trust closure in one formal perspective |
| Cross-foundation alignment or translation | A typed, directional relation between theory-scoped presentations |
| Verification environment lock | Exact content and policy requirements for checking a proof; neither a run nor a result |
| Verification report, certificate, or provenance | The actual checking outcome and, when recorded, verifier/run information |

`Knowledge view`, `concept hub`, `theory-scoped presentation`, and
`cross-foundation alignment or translation` remain provisional names. The
last is distinct from the frozen packaging term `Bridge domain`. The existing
term `Profile` must not be reused because Terminology Standard 000 already
assigns it to an aggregation package.

A concept hub for natural numbers may connect several theory-scoped
presentations:

```text
concept:natural-number
  |
  +-- presentation:zfc:omega
  +-- presentation:peano:first-order
  +-- presentation:mltt:nat
  +-- presentation:hott:nat
```

The hub says that humans intentionally compare these presentations. It does
not say they are definitionally equal, interchangeable, or governed by one
global proof theory.

Each theory-scoped presentation requires digest-bound references to at least:

- its `LanguageSpec`;
- its `CalculusSpec`, judgment kinds, and primitive rules;
- its logic, theory, and logical and non-logical axioms;
- its selected Foundation Unit;
- universe and size commitments where relevant;

For a proof, `VerificationEnvironmentLock` additionally records exact
assertion interfaces, imports, assertion profile, trust policy, and
verification-protocol version. It does not state that checking occurred. A
separate `VerificationReport`, certificate, or provenance record reports the
outcome and the concrete verifier or run when that information is required.

The implementation digest must bind the exact assertion interface, proof
graph, replay context, and dependency requirements. The verification digest
then binds that implementation digest to the exact
`VerificationEnvironmentLock` digest, which covers the required layer
contracts and policies. A formal-perspective ID is navigation metadata, not a
substitute for those content digests. Identical printed formulas do not imply
identical assertions.

### 9.4 Cross-foundation relations make independent capability claims

A cross-foundation edge must state what it claims. The multiple translation
notions studied in Goguen and Roşu's
[institution morphisms](https://doi.org/10.1007/s001650200013)
are a warning that sentence translation, model reduction, and satisfaction
preservation have directions that depend on the selected notion of morphism.
There is no single untyped `translates_to` relation.

Candidate capability claims include:

1. **Editorial alignment:** two theory-scoped presentations concern the same
   human topic.
2. **Notation correspondence:** selected symbols are intended to display
   alike.
3. **Signature or syntax translation:** constructors, judgments, arities,
   and binding are mapped as specified.
4. **Satisfaction or validity preservation:** translated sentences retain a
   named semantic property under an explicit sentence/model translation.
5. **Derivability-preserving interpretation:** translated axioms and rules
   support translation of source consequences.
6. **Faithfulness, reflection, or conservativity:** the relation reflects a
   precisely named class of equalities, validities, or derivability claims;
   these properties must not be inferred merely from the word *embedding*.
7. **Mutual interpretation or a specified equivalence:** translations in
   both directions satisfy named coherence conditions; bi-interpretability,
   categorical equivalence, and other equivalence notions remain distinct.
8. **Proof transport:** proof objects or certificates can be transformed and
   independently checked.
9. **Computational preservation:** reduction or extracted computational
   behavior is preserved.

These capabilities are partly independent, not a linear scale. One relation
record may declare several. A satisfaction-preserving translation may forget
proof objects; a derivability-preserving interpretation need not preserve
definitional equality; a model may validate sentences while erasing
computational or higher-dimensional structure.

Every cross-foundation relation record therefore needs:

- source and target formal-perspective IDs;
- its exact capability claims and direction;
- the fragment on which it is defined;
- preservation and reflection claims;
- evidence or a declared trust status;
- the meta-theory in which those claims are checked;
- known losses and unmapped symbols.

An untyped `same_as` relation is inadequate.

### 9.5 Weak interfaces and the phrase “the same theorem”

The little-theories approach and MMT suggest stating reusable problems in the
weakest adequate interface theory, then realizing that interface in stronger
foundations. This can greatly reduce pairwise translation costs.

But “weakest” is not always unique, and not every formal perspective admits a
lossless common interface. The framework should distinguish at least three
senses of sameness:

1. the statements are editorially aligned as answers to the same human
   question;
2. one statement translates to another under a specified interpretation;
3. a proof transports across a verified cross-foundation relation with
   stated preservation guarantees.

Only the third directly supports independently checkable proof-object reuse.
The second may still support automatic theorem reuse when derivability
preservation and the applicable trust policy are explicit. In either case,
the target result is formal-perspective-relative, not a foundation-free global
`verified` flag.

When no honest common interface exists, the correct representation is partial
alignment, asymmetry, or explicit disagreement. A large framework must be
able to say “these formal perspectives cannot presently be identified”
without treating that result as an integration failure.

### 9.6 The meta-theory does not disappear

To verify an interpretation between two foundations, the system reasons in a
meta-theory. Mechanical verification remains relative to declared rules, a
kernel, or semantic assumptions; adding another formal layer does not by
itself remove that trust boundary. The architecture must expose where its
justification stops.

A cross-foundation certificate therefore needs a provisional meta-theory
manifest analogous to Reference 013's `VerificationEnvironmentLock`. It
records:

- the language and calculus in which the relation is expressed;
- the rules used to prove preservation;
- the trusted kernel or axioms at the stopping point;
- the exact source and target interface digests.

This is not a defect. An explicit stopping point is epistemically stronger
than an implicit claim of neutrality.

Reference 011's **L10 Unique foundation** constraint remains binding for the
current standard object-theory build closure: that closure has one Foundation
Unit. A future cross-foundation relation checker must make one of two designs
explicit. It can encode the source and target foundations as object theories
under one ambient Foundation Unit, or it can propose a revision to L10 and
specify the composite meta-theory's rules and trust boundary. Foundational
pluralism means that the larger platform may host many named closures and
explicit relations among them; it does not license silent mixing inside one
ambient closure.

### 9.7 What lazy loading contributes—and what it cannot contribute

Lazy loading lets a user browse one concept hub and load only the selected
theory-scoped presentation and proof implementation. It makes plural
knowledge views and formal perspectives practical at library scale and
prevents every application from paying for every foundation.

It cannot determine:

- whether two theory-scoped presentations express the same concept;
- whether a translation is sound or conservative;
- whether excluded middle, choice, univalence, or proof irrelevance is
  acceptable;
- whether information lost by translation matters to the user.

Those are mathematical and metamathematical judgments, not loading policy.

### 9.8 Direct answer and unresolved questions

One large engineering framework can contain different foundational
perspectives, but only by unifying **containers, naming, accountability,
verification protocols, and cross-foundation declarations** rather than by
decreeing one common semantics.

The ontology layer must therefore be thin enough to host disagreement and
rich enough to describe it. It may say that two theory-scoped presentations
concern the same human concept; it must not convert that editorial alignment
into a formal identity relation. Each theory-scoped presentation states what
the concept
means in its formal perspective. Each cross-foundation relation states what
can legitimately pass between perspectives.

The unresolved questions are substantive:

1. What evidence is sufficient to assign two theory-scoped presentations to
   one concept hub?
2. Which ontology relations are genuinely cross-foundational, and which are
   artifacts of one foundation's object language?
3. How should partial, lossy, or non-compositional translations be queried
   and displayed?
4. When do two proofs count as implementations of the same result rather than
   proofs of merely aligned statements?
5. Which cross-foundation relation properties must be mechanically certified
   before theorem transport is allowed?
6. How should trust be reported when source, target, and meta-theory use
   different kernels?
7. Can search move across perspectives without silently changing the
   admissible notion of proof or existence?
8. How should release packages version concept hubs, theory-scoped
   presentations, and cross-foundation evidence independently?
9. Who governs the shared ontology when communities disagree not only about
   names but about legitimate mathematical objects?

These questions should not be closed by inventing a lowest-common-denominator
logic. That would solve interoperability by deleting the very perspectives
the framework is meant to preserve.

The defensible conclusion is narrower:

> One framework can host plural foundations, but it cannot decree that their
> objects are “the same mathematics.” Sameness must be stated at a chosen
> level, in a named formal perspective or meta-theory, and supported by the
> appropriate evidence.

There is no view from nowhere in the formal system. A responsible engineering
framework does not hide that fact; it makes the viewpoints, passages, and
limits inspectable.

---

## Primary Sources

- William P. Thurston,
  [“On Proof and Progress in Mathematics”](https://doi.org/10.1090/S0273-0979-1994-00502-6),
  *Bulletin of the American Mathematical Society* 30(2), 1994, pp. 161–177;
  [arXiv:math/9404236](https://arxiv.org/abs/math/9404236).
- Joseph A. Goguen and Rod M. Burstall,
  [“Institutions: Abstract Model Theory for Specification and Programming”](https://doi.org/10.1145/147508.147524),
  *Journal of the ACM* 39(1), 1992, pp. 95–146.
- Joseph A. Goguen and Grigore Roşu,
  [“Institution Morphisms”](https://doi.org/10.1007/s001650200013),
  *Formal Aspects of Computing* 13(3–5), 2002, pp. 274–307.
- Robert Harper, Furio Honsell, and Gordon Plotkin,
  [“A Framework for Defining Logics”](https://doi.org/10.1145/138027.138060),
  *Journal of the ACM* 40(1), 1993, pp. 143–184.
- William M. Farmer, Joshua D. Guttman, and F. Javier Thayer,
  [“Little Theories”](https://doi.org/10.1007/3-540-55602-8_192),
  in *Automated Deduction—CADE-11*, LNCS 607, 1992, pp. 567–581.
- Florian Rabe and Michael Kohlhase,
  [“A Scalable Module System”](https://doi.org/10.1016/j.ic.2013.06.001),
  *Information and Computation* 230, 2013, pp. 1–54;
  see also Florian Rabe,
  [“MMT: A Foundation-Independent Approach to Formal Knowledge”](https://uniformal.github.io/doc/philosophy/articles/mmt.pdf),
  2016.
- The Univalent Foundations Program,
  [*Homotopy Type Theory: Univalent Foundations of Mathematics*](https://homotopytypetheory.org/book/),
  Institute for Advanced Study, 2013;
  [arXiv:1308.0729](https://arxiv.org/abs/1308.0729).
