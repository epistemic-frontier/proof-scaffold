# Project 026: Package Evolution Standard

> Renamed 2026-07-19: formerly "Partition Evolution
> Standard." After terminology was frozen in 000 §13, the normative subject of this document is the evolution of **release packages**
> and their domain/module structures, rather than a one-time "partition"; the filename was changed accordingly to
> `026-package-evolution-standard.en.md`.

> Status: Phase 0 in progress (initiated 2026-07-19).
>
> **Topology supersession (2026-07-20):**
> [Project 028](028-top-level-knowledge-release-units.en.md) supersedes this
> document wherever it assumes one generated release wrapper containing
> multiple mathematical domains, derives public ownership from proof
> placement, or treats mathbox/frontier governance as part of V1. The
> historical plan-v3 record remains reproducibility evidence. For current V1
> semantics, each of sixteen bare mathematical roots is one mathematical
> release unit; Prelude is a separate infrastructure release; mathbox is an
> explicitly excluded governance scope.
>
> **Toolchain-boundary update ([Project 029](029-catalog-compiler-boundaries.en.md),
> 2026-07-21):** the former partition repository becomes the historical
> compatibility layer of the generic `catalog-compiler`; partition plans and
> reports below remain reproducibility evidence. Transpiler moves with its
> complete original SHA history into the compiler as an injected backend.
>
> Normative basis: [Reference 014](../references/014-module-partition-and-knowledge-classification.md)
> (cross-domain governance research), [Reference 015](../references/015-setmm-linearization-empirics.md)
> (empirical study of set.mm linearization), [Reference 016](../references/016-mathbox-community-practice.md)
> (mathbox community practice), and [Terminology Standard 000](../references/000-terminology.en.md).
>
> Upstream project: [Project 025](025-semantic-source-surface.en.md) (semantic source surface; all gates passed).
> Historical plan-v3 handoff targets: the partition repository (plan
> production and validation) and the transpiler repository (plan consumption).
> The current compiler/backend handoff is governed by Project 029.
>
> In this document, "MUST," "MUST NOT," and "SHOULD" have normative meanings.
> **If implementers encounter a decision point not covered by this document, they MUST stop and report it; they MUST NOT invent a decision themselves.**

---

## 0. Goals and Motivation

The partition repository delivers partition plans to the transpiler. The old deliverable (`proof-partition-result-v2`)
was a cut-optimal DP solution over intervals of a topological order; its naming and knowledge-classification quality have been rejected.
Reference 015 provides the structural explanation:

- **F1**: on this graph, the cut objective carries almost no topical signal (only 7–11% of edges at curated boundaries are internal),
  and cut-optimal boundaries are driven by hub positions rather than knowledge classification;
- **F3**: references are highly concentrated in a few glue lemmas (the top 500 absorb 54% of logic references),
  so any objective that gives hub edges and topical edges equal weight will be dominated by hubs;
- **F5**: the settled corpus undergoes about 4% proof rewiring and about 1% statement migration each year, so a static optimum continually drifts.

This project therefore specifies not "a partition result" but **the representation of partitions, the invariants they MUST satisfy,
and the operations by which they evolve as knowledge grows**. Under the
Project 028 topology, it has two current pillars:

1. **Classification-led**: module boundaries and names are declared by knowledge classification (L1); structural metrics serve only as validators;
2. **One root, one mathematical release**: the sixteen bare roots and their
   distribution owners are fixed by Project 028; implementation dependencies
   remain complete and acyclic without determining public ownership.

The five-zone plan-v3 stress test remains a historical milestone. Current
success criteria are Project 028 G0–G5. Mathbox work resumes only under a
separately adjudicated governance project.

## 1. Normative Model

### 1.1 A Discipline Is a Namespace; a Layer Is a Snapshot (2026-07-19 Adjudication)

In mature mathematics, the discipline quotient graph **contains cycles**: numbers, combinatorics, and number theory each have bidirectional
knowledge flows with the others (necklace counting in the direction that proves Fermat's little theorem, generating functions using analysis,
and constructive lower bounds for Ramsey numbers using number theory). The mathematical community recognizes this by giving bridge subdomains
distinct names: *arithmetic combinatorics*, *combinatorial number theory*,
*analytic number theory*, and *additive combinatorics*. Only the
statement graph and, when partitioned well, the module graph are acyclic. Therefore:

Terminology is frozen in
[000 §13 (Layer Nine: Knowledge Organization and Release)](../references/000-terminology.en.md)
as revised by Project 028. A mathematical domain, bare public Python root, and
mathematical release package are one-to-one in set.mm V1. Infrastructure
releases and definition-free profiles own no mathematical root. Consequently:

- **mathematical domain = public knowledge-ownership scope**, not a dependency
  layer;
- **dependencies among mathematical release implementations MUST form a DAG**
  (P7; see §3), while a concrete layering order remains a snapshot property
  and MUST NOT be hard-coded as ontology;
- a **bridge subdomain** has one canonical owner under an adjudicated root and
  plural discovery facets; it does not create another top-level root without
  separate adjudication;
- the same implementation acyclicity and completeness constraints apply
  recursively to module and subpackage projections.

Design responsibility (revised by user adjudication, 2026-07-20): public roots
honor mathematical knowledge tradition; explicit implementation and release
dependencies honor engineering constraints. When the two projections differ,
the toolchain separates public facade from proof provider rather than moving a
declaration to a different subject merely to repair a quotient graph.

Two empirical anchors (2026-07-19, set.mm `e514bf2`):

1. **Leaves become infrastructure**. In the corpus through `cstr`, the word-theory cluster (16 modules,
   ~300 statements) has no consumers and no number_theory dependency, making it a pure leaf; in the complete
   set.mm, however, graph theory defines closed walks directly as words (600+ occurrences in the `clwwlk` family),
   and the necklace lemma `cshwshash` is consumed by `hashecclwwlkn1` (counting equivalence classes of
   closed walks), with the chain leading to the friendship theorem. A "layer" is a function of the corpus cutoff.
2. **One discipline name spans multiple layers**. Complete set.mm already contains `pnt` (prime number theorem),
   `dirith` (Dirichlet), and `bpos` (Bertrand)—analytic number theory lies after
   complex analysis, a full analysis stack away from elementary number theory (divides/gcd/primes, adjacent to numbers).
   number_theory must therefore branch into two first-level subpackages, `elementary` and
   `analytic`, with P7 ensuring that they are acyclic.

No static optimal layout exists; the architectural optimization target is to
**make relayering cheap**: sufficiently fine implementation granularity,
explicit bridge subdomains and provider dependencies, and low-cost
subject-preserving split/rename operations.

### 1.2 Two Editing Rules for Ownership and Implementation

1. **Public ownership follows ontology; implementations follow proof
   dependencies.** Metamath dependencies are proof dependencies, and some
   theorems have an “elementary statement, analytic proof” (`bpos` is one).
   Such a theorem remains publicly owned by its mathematical subject while
   its provider records the analytic `requires` closure. If the current schema
   cannot express the resulting acyclic provider projection, rollout is
   blocked pending facade/provider separation; public ownership MUST NOT be
   silently changed.
2. **Bridge subdomains are explicit but do not invent roots.** A⊗B content
   receives one canonical owner under one of the sixteen roots and additional
   cross-domain facets. A separately released bridge root requires a future
   adjudication. Mathbox promotion is outside this project's V1 scope.

Case adjudications (2026-07-19; edge counts are statement-level measurements):

- In the `number_theory` zone, the reopened `decimal_arithmetic` section **MUST NOT**
  be merged into the same-named module in `number_systems`: 14 of its edges depend on gcd/divides/the division algorithm/
  prime properties, and its consumers are `specific_prime_numbers` (20 edges) and
  `very_large_primes` (37 edges)—it is a decimal lemma library for large-prime certification and is
  **the same name but different knowledge** from the same-named section in `number_systems`. Keep it in `number_theory` and
  rename it by definingness (for example, `primes.decimal_certificates`).
- For `cyclical_shifts_of_words` (a reopened section in the nt zone), pure shift lemmas belong in
  `combinatorics.words.shifts`; necklace lemmas (the `cshwshash` family,
  with 9 edges depending on the prime predicate) are bridge content in arithmetic combinatorics.
- Ramsey / van der Waerden: consumerless leaves that belong in combinatorics. Ramsey's only
  dependency on nt, `ramcl → sumhash`, is a misclassification (`sumhash` is a general
  finite-sum lemma classified under the prime-counting section); after reclassification, there are no dependencies.
- Extract the entire word-theory cluster into the `combinatorics` package; in the current corpus, the layering
  `number_systems → combinatorics → number_theory` holds cleanly.

### 1.3 Three-Layer Decoupling (Inherited from Reference 014 §0)

- **L1 classification skeleton**: the classification tree supplies module **paths and names** (for example,
  `logic.implication`). The classification tree is a namespace, not a dependency graph.
- **L2 module ABI**: dependencies between modules are an explicitly declared **import DAG**.
  The L1 tree and L2 DAG are independent; one MUST NOT be derived from the other (015 F2:
  72% of section pairs have no dependency ordering, and file order is L3 rendering).
- **L3 physical sharding**: file layout and .mm linearization order are derived and contain no normative content.

The former “two zones and one layer” plan-v3 model is retained only for
historical artifact interpretation. Under Project 028:

- **Prelude** is a separate, explicitly locked infrastructure release;
- **core mathematical content** is classified under one of the sixteen roots;
- **mathbox/frontier content** is outside the V1 target source scope pending a
  separate governance adjudication.

## 2. Historical Deliverable: `proof-partition-plan-v3`

This was the handoff artifact from partition to the transpiler for the
2026-07-19 stress test. Project 028 replaces it for current V1 work with
`knowledge-release-plan-v1`. The form below remains normative only when
reproducing historical plan-v3 artifacts:

```json
{
  "schema": "proof-partition-plan-v3",
  "domain": "logic",
  "source_hash": "…",
  "graph_schema": "proof-partition-metadata-v2",
  "draft": true,
  "prelude": {"path": "logic.prelude", "labels": ["idi", "…"]},
  "modules": [
    {
      "path": "logic.implication",
      "title": "Logical implication",
      "definingness": "one-sentence membership criterion",
      "kind": "core",
      "sections": [3],
      "labels": [],
      "imports": ["logic.negation"]
    }
  ]
}
```

- `path`: a lowercase dot-separated path, namely the subpackage path in the generated package (the L1 projection).
- `definingness`: a one-sentence membership criterion (the existence test in Reference 014 §5.2).
  Placeholder text is allowed when `draft: true`; a formal plan MUST pass manual audit.
- `kind`: `core` or `frontier`; the prelude is listed separately.
- Membership: the union of `sections` (section IDs in the reference-graph artifact) and `labels` (explicit labels).
- `imports`: the L2 declaration; **the prelude does not appear in imports** (it is globally, implicitly visible).

### 2.1 Prelude Content Standard (Position Adjudicated: Keep Pre-Logic; Expansion Is an Open Question)

For the decision framework and negative adjudications, see
[Project 027: Prelude Boundary RFC](027-prelude-boundary-rfc.en.md):

- **the prelude remains in its current minimal pre-logic state and will not be expanded for now**
  (three adjudications on 2026-07-19); whether and when to expand to the candidate boundary (set/class
  basics + relations and functions, with an empirical baseline of 1370 nodes / 18 axioms) is the leading open question in 027 §12
  on the list;
- the boundary criterion (if expansion occurs) is **general theory-building capability** (representational primitives and composition
  mechanisms), not "commonly used mathematical content"—**natural numbers (including ω), finiteness,
  induction, finite recursion, and finite sequences/fold all remain outside the prelude**, in set theory and the
  `number_systems` domain (second adjudication; see the postscript to 027 §4.1 for the empirical basis);
- the migration unit is the **capability slice** (a construction together with the minimal usable closure of its formation/equality/
  introduction/elimination/induction rules), not a single label and not the top N entries
  in a frequency ranking—this **supersedes** the original statement in this section that the prelude should "contain constructors only, not
  theorems": the criterion is capability, not syntactic category;
- "depending only on the prelude" is not an architectural metric; application scenarios are assembled through **profiles** (release packages
  containing only aggregate dependencies);
- the object-theory prelude is separate from the Python authoring layer: semantic foundations belong to the prelude,
  while authoring economy belongs to the Python layer;
- `--prelude-floor` absorption-rate calibration is retained but **downgraded** to a stress-test baseline
  tool; quantitative boundaries await completion of the empirical study in 027 §10 (capability slices × five metrics).

The current five-zone corpus's `prelude.core` (215 labels) remains the stress-test baseline
until a capability-slice prelude is implemented.

## 3. Invariants (The Validator MUST Enforce All of Them)

| # | Invariant | Basis |
|---|--------|------|
| P1 | Complete, nonoverlapping coverage: every target node belongs to exactly one module (or the prelude) | Definition of a partition |
| P2 | Paths are valid and unique; `title` and `definingness` are nonempty | L1 naming |
| P3 | Declared imports form a DAG; every referenced path exists | L2 acyclicity |
| P4 | For every dependency edge u→v: same module, or v∈prelude, or module(u) directly declares an import of module(v) | L2 completeness |
| P5 | Legacy membrane check, applicable only to a separately governed frontier scope; Project 028 V1 excludes mathbox/frontier and does not invoke P5 | 016 §6.1; 028 §3 |
| P6 | (Report item) module size, prelude absorption rate, and proportion of within-module edges after hub filtering | 015 F3 |
| P7 | Mathematical-release DAG: the implementation dependency graph among the sixteen mathematical release units MUST be a DAG; the same constraint applies recursively to module/subpackage projections inside each root | §1.1 as revised by 028; 000 §13 |

P6 is a nonblocking report item: capacity constraints are handled by L3 sharding (split-only within the same
classification node), and modules MUST NOT be merged across topics to meet a size target.

Notes on P7 under the Project 028 topology:

- **The DAG property is an invariant; the concrete layering order is not**: a snapshot of release ordering (for example,
  `number_systems → combinatorics → number_theory`) is emitted only as a report for
  audit reference; hard-coding an order would be broken by content such as analytic number theory (§1.1);
- structural guarantee: the mm source is linear and statement dependencies always point physically backward, so **as long as
  membership assignments are intervals, every quotient graph is automatically acyclic**—the current interval-based five-zone draft
  trivially satisfies P7. P7 gains real force after the introduction of **noncontiguous classification-based placement**
  (for example, extracting word theory from the historical `numbers` interval into `combinatorics`): classification may
  diverge from physical order, and at every divergence the validator reports whether a cycle exists at the correct level;
- P7 MUST NOT be satisfied by semantic regrouping alone. A release-level cycle
  requires facade/provider separation, staged implementation shards, or a
  genuine common interface while preserving the curated public owner;
- validator implementation: historical plan-v3 detects quotient cycles by
  path segment; `knowledge-release-plan-v1` MUST instead validate explicit
  release-unit ownership and release dependencies as required by Project 028.

Membership-model upgrade (pending implementation): interval declarations for zones are downgraded to **bootstrap
defaults**; formal placement is supplied by classification declarations (an explicit module → package-path mapping),
and may be noncontiguous. The combinatorics package (word-theory cluster + Ramsey/vdW + bridge content) is
the first noncontiguous-placement use case.

## 4. Historical plan-v3 Evolution Operations

The `create`, `promote`, and `sync` operations involving frontier/mathbox
below are deferred and have no Project 028 V1 authority. Subject-preserving
`split` and `rename` operations remain relevant when expressed through the
new release plan.

Every operation MUST preserve invariants P1–P5 and P7 and leave an auditable record in the plan artifact:

- **create**: create a new frontier module (in an author/agent namespace).
- **promote**: frontier → core. Triggered by demand pull (the appearance of a second consumer,
  016 §6.2). Operation = move + rename according to the naming standard + leave a shim/alias at the old path
  for the deprecation window (the equivalent of the `*OLD` protocol in 016 §6.3).
- **split**: refine a core module by classification (diffusion). Split only; do not merge;
  child-module paths refine the parent path, and the old path retains a re-export shim.
- **rename**: renaming a path MUST be accompanied by a shim and deprecation window; module identity is decoupled from path.
- **sync**: mechanically update all frontier modules after a core rename/refactor.

Downstream reference rule: **statements in frontier MUST NOT be referenced formally by other modules before
promotion** (copied directly from the set.mm rule; the tooling MUST make promotion sufficiently low-friction).

## 5. Naming Standard (Phase 1 Audit Criteria)

- **Leaf names converge to a single noun** (or the shortest noun phrase); **shared prefixes map to
  subpackages**. Current draft paths are automatically generated slugs of section titles and are placeholders only;
  formal paths are curated outputs, while authored titles remain in `title` metadata. Examples
  (2026-07-19, from review of the five-zone draft):
  - `logic.axiom_scheme_ax_4_quantified_implication` … `ax_13`
    (10 modules) → `logic.axiom_schemes.ax04` … `ax13`;
  - `logic.derive_the_lukasiewicz_axioms_from_*` (9 historical-narrative
    modules) → `logic.derivations.*`;
  - `logic.logical_*` → `logic.connectives.{implication, negation,
    conjunction, …}`;
  - `set_theory.introduce_the_axiom_of_*` (7 modules) →
    `set_theory.axioms.{extensionality, replacement, …}`;
  - 16 word-theory modules → `combinatorics.words.{concatenation, subwords,
    prefixes, shifts, …}`.
- Path uniqueness (P2) is checked within the parent-package scope; same-named
  leaves across packages are valid. As the cases in §1.2 show, same-named
  sections are not necessarily the same knowledge unit: public ownership
  follows ontology, while dependency evidence determines provider imports.
- A module name MUST be a **defining characteristic** of its members: one can write a sentence of the form "everything satisfying X belongs here."
- Antipatterns (rejected): non-defining aggregates ("misc," "other," "additional");
  multi-topic catch-all baskets (unless they have independent definingness); capacity-driven semantic fragments
  (inventing nonexistent subdisciplines to meet a size target).
- When names conflict or are ambiguous, follow the process in [Terminology Standard 000](../references/000-terminology.en.md)
  to record the adjudication.

## 6. Historical plan-v3 Phases and Acceptance Gates

The phases below record the superseded 2026-07-19 execution plan. They are
retained for reproducibility and do not authorize frontier/mathbox work under
Project 028. Current acceptance gates are Project 028 G0–G5.

- **Phase 0 (this round)**: implement the `plan-v3` schema + draft generator + validator in the
  partition repository; generate a draft plan for the logic domain.
  - G0a: the validator gives the logic draft plan a clean P1–P5 result;
  - G0b: ruff / mypy strict / pytest are all green in the partition repository.
- **Phase 1**: manually audit definingness in the logic domain (in collaboration with the user),
  producing a formal `draft: false` plan and a comparison report against the DP baseline
  (naming interpretability + P6 metrics).
  - G1: the audited plan is entirely green, and every module's definingness is manually confirmed.
- **Phase 2**: frontier mechanism and authoring tools (scaffold / verify).
  - G2: membrane validation (P5) has positive and negative cases; a frontier package generated by the scaffold can be verified locally.
- **Phase 3**: promote / split / rename / sync operations and shim registration.
  - G3: every operation has before-and-after plan pairs + regression cases showing invariant preservation.
- **Phase 4**: stress-validate the five zones (prelude + logic + set-theory + numbers +
  number-theory) on the unified whole-corpus graph.
  - G4: the unified five-zone plan is entirely green (including cross-zone P4 and a P6 report for each zone); discovered
    specification gaps are written back into this document.

## 7. Interface with the Transpiler

Historical plan-v3 replaced naming-profile's `module_paths` and treated the
first path segment as a domain inside one wrapper output. Project 028
supersedes that mapping.

For current V1, one release emission owns one declared `python_root`; all
`modules[].path` entries lie below that root. The plan separately records
`release_unit_id`, `python_root`, and `distribution_name`, and the transpiler
emits no project-wide content wrapper. Prelude is resolved as an explicit
infrastructure-release dependency and verification lock, not regenerated as a
subpackage of every mathematical release. The next schema is
`knowledge-release-plan-v1` (028 §6).

## 8. Implementation Progress

- 2026-07-19: Project initiated. The two pillars were established from 014/015/016; the plan-v3 schema,
  invariants P1–P6, evolution operations, and naming standard were finalized as above.
- 2026-07-19: Phase 0 completed. `mm_partition.planv3` implemented (draft generator +
  validator + CLI `plan-draft` / `plan-validate`); the logic-domain draft plan was
  generated and passed P1–P5 (G0a); ruff / mypy strict / pytest were all
  green in the partition repository (G0b). The draft plan's prelude took the top 48 references across the domain; its 49 section
  modules used placeholder definingness text pending a Phase 1 manual audit.
- 2026-07-19: Phase 0 empirical results (logic domain, partition repository commit
  `1ca0897`, based on the latest set.mm snapshot after the user's `21060ff` four-domain organization
  (2740 nodes), regenerated and revalidated after the rebase; artifact
  `domains/logic/artifacts/classification-plan-v3.draft.json`):
  - P6 metrics: among 13380 dependency edges, the prelude (48 labels) absorbs **49.5%**;
    after filtering out the prelude, **51.0%** of edges are within-module, versus the cut-optimal baseline in 015 F1, whose
    interval range is 7–11%, supporting the two pillars of "classification-led + hubs listed separately";
  - prelude content automatically selected glue lemmas (`syl`, `ax-mp`, `a1i`, `adantr`,
    `bitri`, …) and syntax constructors (`wi`, `wn`, `wa`, `wal`, …), without manual seeds;
  - module sizes were min 2 / median 19 / max 452, with 294 import declarations and an
    acyclic DAG; the two 2-node modules and the giant 452-node module were the first targets of the Phase 1 audit
    (the former to examine classification-tree consolidation, the latter to be handled by L3 split-only);
  - names directly projected section titles; the "derive_the_*_axioms_from_*"
    family (alternative axiom systems) suggested classification under the `logic.systems.*` subtree in Phase 1
    or possible frontier placement (provisional, pending adjudication).
- 2026-07-19: Four-domain stress test (Phase 4 executed early, partition repository commit
  `5924a1b`). The base was updated to set.mm develop `e514bf2` (2026-07-18,
  source hash `ed3a34ef`), the four domain graphs were re-exported, the v2 pipeline was fully refreshed, and the
  plan-v3 drafts for all four domains passed P1–P5 **cleanly**. Findings and fixes:
  - **The snapshot diff is itself a promotion record**: the only substantive difference between the old and new snapshots was the top set.mm commit
    "Copy bj-zfauscl to Main as sepg" (mathbox→Main promotion +
    `zfausclOLD` deprecation shim), so the protocol in Reference 016 §6.2/6.3 was
    directly observed in a routine update; the curated boundaries were restored by a +2 shift after label remapping,
    validating the drift-resistant design of "labels as identity, ordinals as derived."
  - **Three generator hardenings** (defects exposed by the stress test): slugs must decode HTML entities
    and strip diacritics (B&eacute;zout→bezout), and domain roots must be slugified
    (set-theory→set_theory); an "X (cont.)" section is merged back into the base section of the same chapter
    (a linearization trace is not a classification node, and set.mm has an instance of **same-named
    sections placed in two locations**); section-granularity dependency cycles are condensed by Tarjan SCC into
    merged modules whose definingness marks them for Phase 1 statement-level redistribution.
  - **Cycle census**: logic has 0; set-theory has 2 2-way cycles (equinumerosity +
    Schröder–Bernstein, finite sets + the pigeonhole principle); number-theory has 1
    2-way cycle (coprimality/Euclid's lemma + congruence cancellation); numbers has a **25-section
    large SCC** (mutual dependency between the extended reals and restatements of order axioms, 1874/5475 nodes)—
    set.mm's real-number layer cannot be layered at section granularity and is the highest-priority Phase 1 target.
  - **P6 four-domain profile** (prelude=48, absorption rate / proportion of within-module edges after hub filtering):
    logic 49.5%/51.0%, set-theory 37.1%/26.9%, numbers 47.0%/49.0%,
    number-theory 52.9%/72.8%. Both low figures for set-theory show that one globally uniform
    prelude is too small and that the prelude should be calibrated by domain (pending Phase 1 adjudication).
  - The G4 criterion "names pass a definingness audit" was not met (definingness in all four domains
    remained placeholder text); the draft marker can be removed only after the Phase 1 manual audit.
- 2026-07-19: The stress-test scope was recast as a **unified five-zone model** (partition repository commit
  `fb73bf3`, criteria correction `5565fe9`): the prelude was promoted to a global fifth zone alongside logic / set_theory /
  numbers / number_theory, with unified validation over the whole corpus [0, cstr) (17207 nodes,
  353810 edges, `domains/corpus`) and cross-zone dependency edges included in P4.
  - **Prelude calibration criterion** (provisional): the minimum size giving each zone a reference absorption rate ≥ 50%.
    The absorption rate uses the same accounting as P6 (edges emitted by prelude nodes themselves are excluded from
    both numerator and denominator; the selector initially included these edges, making logic report 49.7%, and was fixed with an incremental
    exact scan and a regression test), yielding an exact solution of **215 labels** (logic 99,
    set_theory 88, numbers 27, number_theory 1; 90 syntax constructors/axioms
    + 125 glue lemmas—prelude ≈ whole-corpus vocabulary + inference glue). The absorption-rate
    curve has a power-law tail and no clear elbow (approximately 48→34%, 256→59%, 1024→78%),
    so a floor criterion is used rather than an elbow criterion.
  - **Unified five-zone validation entirely green**: 274 modules (logic 48 + set_theory 125 +
    numbers 70 + number_theory 31), 7065 import declarations, no cross-zone cycles,
    and no cross-zone sections; per-zone absorption rates were logic 50.0%, set_theory 55.8%,
    numbers 58.6%, and number_theory 53.2%.
  - **Cross-zone profile** (invisible from a single-domain view): among non-prelude references, the proportions pointing within the same zone were
    logic 100%, set_theory 57.7%, numbers 40.3%, and number_theory
    only 8.5% (among 41726 edges, 3546); number_theory is a heavy consumer of numbers/set_theory.
    Per-zone within-module proportions were logic 51.0%, numbers
    26.7%, set_theory 21.0%, and number_theory 9.3% (the latter three are diluted by cross-zone edges,
    so module cohesion should be evaluated using within-domain edges).
  - Artifact: `domains/corpus/artifacts/classification-plan-v3.draft.json`
    (five zones); the four single-domain drafts were retained for comparison. Zones are declared by domain config's
    `zones` field, and `--prelude-floor` triggers calibration.
  - Measured pipeline times: mono cold start ~2.6s; full-graph export 2.9s;
    plan-draft (including calibration scan) 0.31s; plan-validate 0.18s—under a persistent
    mono process the full path takes ~3.5s, so "every set.mm update → re-export → recalibrate →
    revalidate" can be a cheap routine CI operation without caching or incrementalization.
- 2026-07-19 (second round): manual review of the five-package draft + whole-library analysis;
  normative text updated (§1.1/§1.2/§2.1/§3-P7/§5):
  - Review finding: numbers had a **giant 1883-node module** (the product of section-level SCC
    condensation, covering 35% of that package, with a path concatenating ~20 titles), requiring statement-level
    empirical study of whether it can be layered; 61/274 modules had ≤10 statements (long-tail micro-modules pending audit adjudication);
    the word-theory cluster hung under numbers, and two same-named sections occurred across packages (see the §1.2 cases).
  - **P7 local layering invariant finalized** (global package-level acyclicity rejected); the discipline=namespace,
    layer=snapshot model and empirical anchors were written into §1.1, and the two editing rules—placement follows proof dependencies and
    bridge subpackages are first-class citizens—together with four case adjudications were written into §1.2.
  - Naming standard expanded: single-noun leaves + shared prefixes→subpackages + curated paths override
    slugs (§5, including five sets of example mappings).
  - Prelude content standard initiated for adjudication (§2.1): the user's direction was constructors only,
    excluding theorems, with axioms in doubt; this affects P6 accounting and whether `--prelude-floor` survives.
  - Pending implementation (next round in the partition repository): P7 validator, classification-based noncontiguous placement
    (intervals downgraded to bootstrap), and the combinatorics-package extraction use case.
- 2026-07-19 (third round): **knowledge-organization terminology frozen** (user adjudication): release package
  / mathematical domain / bridge domain / module / prelude (provisional) were registered in 000 §13
  (Layer Nine, bilingual, version v0.2). P7 wording was standardized as "a DAG of domain-to-domain
  dependencies within one release package, applied recursively within domains"; the invariant is the DAG property,
  while the concrete layering order was downgraded to a report item. §7 added the transpiler terminology mapping (output
  = release package, first path segment = domain).
- 2026-07-19 (fourth round): **prelude boundary adjudication**; the open questions in §2.1 were settled and
  the specification was refined into [Project 027: Prelude Boundary RFC](027-prelude-boundary-rfc.en.md):
  prelude = general theory-building capability (through natural numbers/finite constructions/relations and functions/general
  theory-definition mechanisms); migration unit = capability slice; application scenarios are assembled through profiles;
  linear algebra goes in the first-level standard library, and calculus in the analysis library; the object-theory prelude
  is separated from the Python authoring layer. Capability slice / profile were added to 000 §13, and the prelude entry's
  "provisional" marker was removed in favor of the boundary principle. `--prelude-floor` was downgraded to a stress-test baseline tool.
  The quantitative boundary awaited the empirical study in 027 §10 (capability slices × five metrics, next round in the
  partition repository).
- 2026-07-19 (fifth round): **second prelude boundary adjudication (reversal)**. The first pilot in 027
  §10 (the natural-numbers capability slice, in the partition repository at
  `reports/corpus/prelude-naturals-pilot.md`) showed that the ω-system closure reached
  2479 nodes / 14.4% of the corpus, and that "the prelude owns ω, the numbers domain owns ℕ" did not fully align with mathematical
  tradition; the user adjudicated that natural numbers (including ω) stay outside the prelude, and the boundary in §2.1
  was revised to "through set/class basics, relations, and functions." Finite sequences/fold
  moved down into the numbers domain. The empirical baseline after reversal was 1370 nodes / 18 axioms. The prelude entry in 000
  was revised accordingly (v0.4).
- 2026-07-19 (sixth round): **prelude positioning converged (third adjudication)**: keep
  the current minimal pre-logic state and do not expand it for now; the candidate boundary (sets/classes + relations/
  functions) and empirical baseline were preserved in 027, with "whether/when to expand" as the leading open question in 027 §12.
  How program foundation / profile would enter was retained in the same round as an
  open question. The prelude entry in 000 was revised to record the current position (v0.5).
- 2026-07-19 (seventh round): **standard five-domain classification plan implemented** (partition repository
  commit `21432bf`, artifact
  `domains/corpus/artifacts/classification-plan-v3.standard.json`),
  for the next-stage compilation stress test. The generation mechanisms and adjudications were all encoded in executable configuration
  (the `domains/corpus/domain.json` configuration's `plan_v3` block):
  - **Explicit prelude**: `prelude_labels: [wn, wi]` (the current actual metamath-prelude
    output), replacing frequency top-N; the 215-label plan was downgraded to a historical stress-test
    baseline. The frequency mechanism remains as a fallback.
  - **P7 validator implemented**: the module import graph is quotiented by the first path segment into a domain graph for
    DAG checking (module-level acyclicity does not imply domain-level acyclicity), and `domain_imports`
    was added to the P6 report.
  - **Combinatorics-domain extraction (empirical adjudication)**: word-theory sections 230–245,
    inclusion-exclusion 260, van der Waerden 299, and Ramsey 300 moved through section-level
    noncontiguous placement; `sumhash` (a fiber-counting lemma misclassified in a prime-counting section and
    needed by the Ramsey closure) was extracted through a **label-level override**,
    with the mechanism explicitly recorded on both sides of the plan (curated-module `labels` + source-module
    `exclude_labels`), while the validator maintained strict P1. After empirically comparing both directions,
    **logic → set_theory → numbers → combinatorics →
    number_theory** was selected (consistent with the knowledge tradition that "number theory uses combinatorial tools," at the cost of moving only
    the single label sumhash; the alternative placed nt before comb and moved no labels but reversed the
    direction, so it was rejected); the binomial
    theorem (259) remained in numbers because of 3 backward references from the numbers side,
    and necklace-prime section 304 stayed in number_theory under the bridge adjudication in §1.2
    by default (its dependency on the word-theory machinery in 243 is the legal nt→comb direction).
  - **Five-domain profile**: 276 modules, with a strict DAG of domain dependencies (comb does not depend on
    nt); logic 49 modules/2738 nodes, set_theory 125/8090, numbers
    53/5013, combinatorics 20/529, number_theory 29/835;
    ruff / mypy strict / pytest (34 tests) all green; plan-draft 0.22s,
    plan-validate 0.19s.
  - **Release-package mapping metadata**: prelude→metamath-prelude, logic→
    metamath-logic, set_theory→metamath-set-theory, numbers→
    metamath-numbers, combinatorics→**metamath-combinatorics
    (repository pending)**, number_theory→metamath-number-theory, recorded in
    `plan_v3.packages`.
  - Known remaining work: the giant 1895-node SCC module in numbers (the highest-priority Phase 1 statement-level
    redistribution target); definingness remained placeholder text, and the draft marker
    had not been removed; curated naming (such as `primes.decimal_certificates`) awaited
    Phase 1.
- 2026-07-19 (eighth round): **the plan-v3 whole-corpus compilation stress test passed**
  (transpiler commit `60331e1`, branch `semantic-api-v2`; partition
  hotfix `607e20e` truncated condensed-SCC module-path leaves to 100 characters).
  - **Cause of the giant SCC module established**: the set.mm statement dependency graph is itself a DAG; cycles appeared
    after quotienting by authored sections—definitions, closure theorems, operations, and number-system
    embeddings reference one another across adjacent sections, condensing 23 sections (184–194, 198–206,
    208–210, 212–213; extended reals, elementary properties of complex numbers, arithmetic operations, completeness,
    positive integers/induction, Archimedean properties, and so on) into
    `numbers.infinity_and_the_extended_real_number_system__scc_23`
    (1895 labels). This is not a proof cycle but a knowledge-boundary cycle caused by overly coarse
    section granularity; the solution is Phase 1 statement-level capability-slice splitting
    (`labels` + `exclude_labels` overrides), not moving an entire section.
  - **Transpiler reads plan-v3 directly**: `--plan` mode replaced contiguous-boundary partitioning,
    supporting noncontiguous module placement, an explicit prelude first module, exact ownership validation
    (17,207 labels with neither duplicates nor omissions), and module-path conflict checks; `--partition`
    compatibility mode was retained.
  - **Surface-rendering defect fixed (first exposed by the whole corpus)**: set.mm structure variables
    (dot-bearing variable names such as `.x.` and `.+.`) could not round-trip through notation text
    (the tokenizer split the dots), triggering an untested façade fallback path
    that crashed. The fix renders explicit `Judgment`/`App`/`Var` expressions
    (proof `subst` values likewise fall back individually after round-trip checks), with variable references
    matching the structure of generated `Theory` minting rules. Only 13/16,899 signatures in the whole corpus
    (0.08%) use the fallback; all register and elaborate correctly. A regression test
    uses monkeypatch to force fallback generation everywhere and elaborate the entire result.
  - **GC cliff**: the first whole-corpus attempt did not finish generation in 16 minutes; `sample` showed
    ~85% of the time in `_PyGC_Collect`/`mark_stacks` (an approximately 3 GB resident object graph
    was repeatedly marked in full by generational GC). Calling `gc.freeze()` +
    `gc.disable()` after the database scan restored linear behavior. This is a fixed operating requirement for the whole-corpus toolchain.
  - **Timing** (Apple M4, one single-process run): scan 1.78s; generation
    277.69s; lazy import 7.96s; validation 0.03s; benchmark total 287.46s.
    A separate run elaborated all 16,542 proofs through a live `Theory` registry in 50.70s
    (import 2.84s). Against the 07-18 four-domain chained baseline (generation 324.34s +
    eager-replay import 91.01s ≈ 415.36s), one package with five domains and full
    elaboration took about 336.4s (note: GC was disabled in this round and the renderer had changed,
    so conditions were not strictly identical).
  - **SCC module load behavior**: the 1895-label module generated 3.84 MB of Python source,
    with no anomalies in generation/import/elaboration—at the current scale, it is a readability and boundary
    hygiene problem, not a performance hotspot.
  - Artifacts: `transpiler/benchmarks/benchmark_plan_v3.py` and
    `benchmarks/setmm-five-domains-plan-v3-20260719.{json,md}`;
    82 tests, ruff, and mypy strict all green.
  - Next steps: Phase 1 statement-level splitting of the giant SCC module and curated naming;
    create the metamath-combinatorics repository; wire release-package metadata into consumers.
- 2026-07-20 (ninth round): **release topology superseded by Project 028**.
  Sixteen bare mathematical Python roots were frozen as sixteen one-to-one
  mathematical release units; `numbers` became `number_systems`; Prelude
  became a separate infrastructure release; public ownership became
  ontology-led while proof dependencies remained implementation constraints;
  and mathbox/frontier classification was removed from V1 pending a separate
  governance adjudication. Historical plan-v3 artifacts and measurements are
  preserved, but new implementation work targets `knowledge-release-plan-v1`.
