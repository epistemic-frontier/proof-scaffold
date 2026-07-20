# Module Partitioning and Knowledge Classification: A Cross-Domain Survey

> Status: literature survey and design reference (2026-07-19), for long-term citation.
>
> Scope: evidence base for the upcoming standard on "naming, knowledge
> classification, and evolution of proof-library module partitions". The
> motivation follows the partition normalization discussion after
> [Project 025](../projects/025-semantic-source-surface.en.md): in the semantic
> package surface the import graph *is* the dependency graph, so module paths
> (such as `metamath_logic.prop.equivalence`) become downstream ABI; yet the
> current partition scheme is produced by graph-cut optimization with names
> retrofitted by hand — unfaithful to knowledge classification and without any
> evolution-stability contract.
>
> This document is **not normative**. Normative adjudications (plan schema,
> governance process, acceptance gates) belong to the future partition
> standard project; this document supplies its evidence and sources. The
> "implications" at the end of each section condense the survey findings for
> that project to cite.
>
> Five survey strands: community detection and DAG partitioning; module
> organization practice in formal mathematics libraries; knowledge
> organization systems and taxonomy evolution; software modularization and
> API evolution; Wikipedia category governance.

---

## 0. Core Synthesis

All five strands converge on the same diagnosis: **knowledge classification
(naming), public import paths (ABI), and physical partitioning
(graph-cut/capacity) are three things with different rates of change, and
every mature system layers them apart**. Letting a single graph cut decide
all three at once is the root cause of the current scheme's problems.

```text
L1 Knowledge taxonomy   curated controlled vocabulary; versioned; near-frozen
                        (MSC top level: zero changes across a decade)
L2 Public module ABI    topic-package facades; may only grow or split
                        (refinement constraint)
L3 Physical shards      graph-cut/capacity driven; private; free to change
                        (NumPy _core precedent)
```

Five pillar conclusions consistent across domains:

1. **Graph-cut results are candidate boundaries, not knowledge boundaries.**
   Giving conceptual names to graph-cut slices is a wrong abstraction, not
   merely poor naming (Peel et al. 2017; Bunch 1999 itself advocates
   human-locked clusters with the optimizer deciding only internal placement).
2. **The formalization of "natural knowledge growth and differentiation" is a
   refinement constraint**: the new partition restricted to old nodes must be
   a refinement of the old partition — existing modules may only persist or
   split; merges and cross-module reshuffles are allowed only in explicit
   major restructuring releases, and must ship an old-to-new mapping table.
   The literature offers no off-the-shelf split-only algorithm, but
   evolutionary clustering, orphan adoption, and Leiden refinement provide
   all the building blocks.
3. **Separate identifiers from display names** (SKOS/OBO/Wikidata practice):
   what stays stable is the identity ID; paths and display names may evolve
   with migrations; old IDs are never deleted and never reused.
4. **Module path changes require hard compatibility layers**: re-export shims
   plus `DeprecationWarning` plus a window of at least two releases (mathlib
   six months, MathComp two years, Django/NumPy two releases). Wikipedia's
   soft redirects are tolerable only because categories are navigation
   metadata; an ABI cannot copy that.
5. **No mature system splits mechanically by size.** Split criteria are
   topical cohesion, dependency cut points, and evidence of independent
   reuse; "capacity-driven semantic fragmentation" should be listed as an
   anti-pattern (a project-local term — the literature has no unified name
   for it).

---

## 1. Community Detection and DAG Partitioning

### 1.1 Hierarchical community detection

- **Peixoto 2014, Hierarchical Block Structures (nested SBM)**, Phys. Rev. X.
  <https://doi.org/10.1103/PhysRevX.4.011047>
  Recursive block aggregation with Bayesian/MDL model selection inferring
  both depth and block counts; avoids modularity's resolution limit and
  spurious communities. The statistically best-grounded candidate for a
  hierarchy skeleton.
- **Blondel et al. 2008, Louvain**.
  <https://doi.org/10.1088/1742-5468/2008/10/P10008>
  Local moves plus aggregation yield a multi-level trajectory; fast, but its
  "hierarchy" is a by-product of optimization, not a knowledge ontology.
- **Traag/Waltman/van Eck 2019, Leiden**.
  <https://doi.org/10.1038/s41598-019-41695-z>
  Adds a refinement phase splitting coarse communities into well-connected
  subcommunities — close in spirit to "split-first", but the full algorithm
  still allows recombination at the aggregation level, so it does not
  guarantee split-only behavior across versions.
- **Paris (hierarchical clustering by node pair sampling)**.
  <https://arxiv.org/abs/1806.01664>
  A single run produces a complete dendrogram, convenient for choosing
  stable cut levels and naming parents and children separately.

**Implication**: hierarchical partitioning is a better foundation for naming
and stability than a flat K-partition — parent nodes carry stable domain
names while children only express specialization relative to their parent;
a persistent module tree should be maintained instead of an independent flat
partition per version.

### 1.2 Acyclic DAG partitioning

- **Herrmann/Uçar/Kaya/Çatalyürek 2017/2019, acyclic partitioning and dagP**.
  <https://doi.org/10.1137/18M1176865>; <http://tda.gatech.edu/software/dagP/>
  Multilevel partitioning adapted to keep the quotient graph acyclic
  throughout; blocks can be numbered so all cross-block edges point one way.
  Demonstrates that "cut contiguous intervals along one topological order"
  is only one strong restriction guaranteeing acyclicity; the optimization
  space can be larger.
- **Moreira/Popp/Schulz 2018/2020, evolutionary multi-level acyclic
  partitioning**; **Popp et al. 2021, acyclic hypergraph partitioning**.
  <https://arxiv.org/abs/2002.02962>
  Multi-objective fitness and hyperedge modeling (one theorem co-cited by
  many downstream theorems) are worth borrowing; implementation complexity
  is high.

**Implication**: acyclic partitioning solves "how to cut structurally while
keeping module dependencies acyclic" — it provides no knowledge semantics.
If dropping the interval restriction greatly reduces the cut while visibly
harming semantic coherence, that is precisely the proof that semantics must
be an independent objective rather than something cut quality can speak for.

### 1.3 Dynamic/incremental partitioning and stability measures

- **Chakrabarti/Kumar/Tomkins 2006, Evolutionary Clustering**.
  <https://doi.org/10.1145/1150402.1150467>
  cost = α·snapshot-quality + (1−α)·temporal-smoothness; the trade-off
  between structural improvement and classification stability becomes an
  explicit parameter.
- **Lin et al. 2008, FacetNet**. <https://doi.org/10.1145/1367497.1367590>
  Soft membership with smoothness of membership distributions across
  consecutive snapshots; suits foundational theorems that straddle domains.
- **Yang et al. 2011, dynamic Bayesian community models**.
  <https://doi.org/10.1007/s10994-010-5214-7>
  The previous community state serves as the prior for the current one — the
  principled form of "old module identity as prior; change only under
  sufficient evidence".
- **Meilă 2007, Variation of Information**.
  <https://doi.org/10.1016/j.jmva.2006.11.013>
  A true metric on partition space; additive over refinements — when coarse
  levels agree, total distance decomposes into per-parent-block terms,
  making it easy to locate where evolution happened. Caveat: VI charges
  "legitimate splits" and "arbitrary reshuffles" equally, so it cannot by
  itself express split-preference.
- **Lancichinetti/Fortunato 2012, Consensus Clustering**.
  <https://doi.org/10.1038/srep00336>
  Run the algorithm many times per version and build a consensus first,
  eliminating algorithmic randomness before discussing cross-version
  stability.

**Key finding**: no widely adopted standard algorithm strictly guarantees
"old blocks may only persist or split". Dynamic-community literature detects
split/merge events, but detection is not the same as optimizing under a
split-only constraint. The cleanest formalization is to impose the
refinement constraint as a hard constraint —
`C_t restricted to old nodes ⪯ C_{t-1}` — with asymmetric costs
`λ_split ≪ λ_move ≪ λ_merge`; this part the project must specify itself.

### 1.4 Aligning partitions with semantic labels

- **Treeratpituk/Callan 2006, Automatically Labeling Hierarchical Clusters**.
  <https://www.cs.cmu.edu/~callan/Papers/dgo06-puck.pdf>
  Hierarchical labels must be discriminative relative to parent and sibling
  clusters — if the parent module is "topology", a child should be named
  "compactness", not "topology" again.
- **Mei/Shen/Zhai 2007** (topic labeling,
  <https://doi.org/10.1145/1281192.1281246>) and **Lau et al. 2011**
  (<https://aclanthology.org/P11-1154/>): rank controlled candidate phrases
  by coherence and discriminativeness; general-purpose encyclopedias
  overgeneralize, so prefer domain-controlled vocabularies plus human
  confirmation.
- **Peel/Larremore/Clauset 2017, The Ground Truth About Metadata**.
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC5415338/>
  Human metadata is not automatically the ground truth of topological
  communities; statistically test whether they correlate (BESTest) and allow
  legitimate disagreement.

**Implication**: structural quality, temporal stability, and semantic
interpretability are three objectives — measure them separately and trade
them off explicitly, ideally reporting a Pareto frontier rather than one
uncalibrated weighted sum. Before adopting set.mm's own section structure as
the taxonomy skeleton, first test its correlation with the dependency
structure.

---

## 2. Module Organization Practice in Formal Mathematics Libraries

### 2.1 Lean 4 mathlib

- Import names map dot-wise to paths (`Mathlib.Order.Lattice`); **file paths
  are decoupled from declaration namespaces** — the API of one mathematical
  object may spread across dependency layers while declarations stay in one
  logical namespace.
  <https://leanprover-community.github.io/contribute/naming.html>
- Directories follow mathematical domains; inside a domain, files split by
  dependency layer into `Defs`/`Basic`/`Lemmas`/`Instances` — layer names
  are an explicit "dependency layer" vocabulary and do not masquerade as
  knowledge boundaries.
- Deprecation policy: `@[deprecated] alias` with a date, removable after
  about **six months**; moved modules keep a thin file at the old path
  re-exporting the new one, with linter hints.
  <https://leanprover-community.github.io/contribute/style.html>;
  maintenance practice in *Growing Mathlib*
  (<https://arxiv.org/html/2508.21593v1>).
- Roughly 1.9 M lines; files typically a few hundred lines with no hard line
  threshold; depth usually 2–4 levels.

### 2.2 Isabelle/HOL and the AFP

- Two abstractions: theory (file) and session (build/dependency unit defined
  in ROOT); references are usually two-level `Session.Theory`, with the
  complexity living in the session graph rather than directory depth.
  <https://isabelle.in.tum.de/website-Isabelle2021-1/dist/library/Doc/System/Sessions.html>
- The AFP is organized as paper-like entries (one entry, one session), about
  926 entries / 4.86 M lines; the conflict between continuous maintenance
  and archival preservation is resolved by "freeze in sync with Isabelle
  releases + continuous migration on the development branch".
  <https://www.isa-afp.org/submission/>
- No uniform theory-rename deprecation policy; downstream protection relies
  on whole-library migration and pinning to releases.

### 2.3 Mizar MML (the cautionary tale)

- Flat 8-character article names (`XBOOLE_0`), no namespaces; the project's
  own tutorial describes the library as "not systematically classified but
  chronological". <https://mizar.uwb.edu.pl/project/mizman.pdf>
- Consequences: cryptic abbreviations at scale, same-topic content scattered,
  poor searchability, `ARTICLE:n` references drifting after refactors;
  modern research has to bolt on external MSC classification to compensate.
  <https://ceur-ws.org/Vol-3377/fmm10.pdf>
- The only recorded granularity policy: an old submission guideline
  suggesting articles of at least ~1,000 lines (historical rule of thumb,
  not a current hard gate).
- No alias mechanism, no permanent theorem IDs; compatibility is maintained
  by the Library Committee centrally rewriting the whole library.

### 2.4 Rocq (Coq) standard library and Mathematical Components

- Stdlib directories follow knowledge/function classification; `*-base`
  versus aggregation modules separate foundations from user entry points;
  `Require Export` wrappers serve as compatibility layers.
  <https://rocq-prover.org/doc/v9.0/stdlib/index.html>
- MathComp has the clearest compatibility policy in this survey: renames
  first ship
  `#[deprecated(since=..., use=...)] Notation old := new (only parsing)`,
  kept for at least one release with a **two-year target**; changelog
  entries are mandatory.
  <https://github.com/math-comp/math-comp/blob/master/CONTRIBUTING.md>

### 2.5 Cross-library conclusions

- Module boundaries are universally a hybrid: **knowledge classification on
  the surface, dependency layering underneath**; on conflict, directories
  keep the knowledge classification, topics split internally by dependency
  layer, and aggregation entry points are separated from implementation
  files.
- Nobody splits mechanically by lines or theorem counts; split criteria are
  topical cohesion (one-sentence description plus module docstring),
  dependency direction, and build cost.
- Depth convention: 3–4 meaningful path components at most; Mizar
  demonstrates the long-term cost of excessive flatness.
- The combination most worth copying for an ABI: long-lived thin shims at
  old paths + explicit `deprecated_since` and removal version + generated
  migration tables/scripts + CI testing that old imports still work.

---

## 3. Knowledge Organization Systems and Taxonomy Evolution

### 3.1 MSC 2020

- Three-level mixed coding (`03` / `03B` / `03B10`) with 63 / 529 / 6,022
  entries; branching around ten per level but very unevenly distributed.
  <https://msc2020.org/>
- Revised roughly every decade; the MSC2020 revision changed **zero**
  two-digit top-level classes — the upper structure is treated as an
  expensive public interface, with growth absorbed by the lower levels.
- Publishes **bidirectional conversion tables** (2010↔2020) expressing
  retained/renamed/retired/split mappings; MathSciNet keeps historical
  classes with their validity years ("Show Historical Classes").
  <https://mathscinet.ams.org/msc/msc2020.html>
- One primary plus several secondary classifications per paper, with heavy
  cross-referencing: not a pure tree demanding unique leaf membership.

### 3.2 Faceted versus enumerative; SKOS

- Faceted classification (Ranganathan's Colon Classification and its
  hospitality devices) is friendlier to natural knowledge growth: new
  subjects arise as combinations of existing facets without prior
  enumeration; the cost is harder design and use.
  <https://www.isko.org/cyclo/colon_classification>
  The practical optimum is usually a **hybrid**: a stable shallow
  enumerative skeleton plus independent facet metadata.
- SKOS conventions: `skos:Concept` (URI identity) separated from
  `prefLabel` (display name) and `notation` (code); `changeNote`,
  `exactMatch`, etc. express evolution and mappings. SKOS is only an
  expression layer — deprecation cycles and migration policy must be
  supplied by project governance. <https://www.w3.org/TR/skos-reference/>

### 3.3 Ontology evolution: OBO Foundry and Wikidata

- OBO identifier policy: terms carry persistent IDs; **deprecation never
  deletes, IDs are never reused**; mark `owl:deprecated`, use
  `term replaced by` for exact replacements and `consider` for non-exact
  candidates; obsolescence reasons explicitly include **term split**.
  <http://obofoundry.org/id-policy.html>;
  <https://oboacademy.github.io/obook/howto/obsolete-term/>
- Key principle: **identifier stability does not license silent meaning
  change** — quietly repointing an old ID at a narrower new subclass makes
  old data misread; a genuine split must mint new IDs and deprecate the old
  one.
- Wikidata: Q-IDs are persistent identifiers; after merges the old ID
  redirects and is never reused. <https://www.wikidata.org/wiki/Help:Merge>
- COnto-Diff
  (<https://www.sciencedirect.com/science/article/pii/S1532046412000627>):
  recognizing add/delete diffs as composite split/merge operations markedly
  improves human review and downstream migration; mapping-migration
  experiments report F-measures of 90–94%
  (<https://pmc.ncbi.nlm.nih.gov/articles/PMC5018063/>).

### 3.4 Controlled vocabulary governance

- ANSI/NISO Z39.19 process: candidate-term proposal (with rationale) →
  editorial review (coverage overlap, form, hierarchical relations) →
  expert review → approval → record date and responsibility → keep history
  notes → assess impact on retrieval of historical data.
  <https://www.niso.org/publications/ansiniso-z3919-2005-r2010>
- Role separation: owner / steward / editor / editorial board / domain
  experts.
- Naming rules: one preferred name per concept per language; old names kept
  as entry points; **machine IDs are not derived from display names**, or at
  least never change when display names do.

---

## 4. Software Modularization and API Evolution

### 4.1 Software clustering and stability

- **Bunch** (Mancoridis/Mitchell, ICSM 1999,
  <https://www.cs.drexel.edu/~bmitchell/pubs/icsm99.pdf>): modularization as
  optimization of MQ (high cohesion, low coupling); the paper itself admits
  small changes can upend the partition, hence supports user-directed
  clustering (locking human-confirmed subsystems) and **orphan adoption**
  (freeze the old structure; choose placements only for new or significantly
  changed modules) — the precedent for a dual-track regime of "incremental
  adoption by default, global re-clustering only as proposals".
- **MoJo / MoJoFM** (Tzerpos/Holt 1999; Wen/Tzerpos 2003): move+join
  operation distance between partitions, the standard stability measure in
  software clustering; the evaluation convention compares MoJo sequences
  across consecutive versions (survey:
  <https://onlinelibrary.wiley.com/doi/10.1155/2012/792024>).

### 4.2 Package design principles (Robert Martin)

<https://staff.cs.utu.fi/~jounsmed/doos_06/material/DesignPrinciplesAndPatterns.pdf>

- **CCP** (Common Closure): elements that change for the same reason belong
  in one component — when one topic is cut in two by a capacity budget and
  knowledge growth keeps touching both halves, they are still logically one
  topic boundary.
- **CRP** (Common Reuse): only when a subtopic has independent downstream
  users and its own evolution cadence is there a solid reason to promote it
  to a public submodule.
- **REP** (Reuse/Release Equivalence), **SDP/SAP** (Stable Dependencies /
  Stable Abstractions), **ADP** (Acyclic Dependencies): stable topic entry
  points should sit downstream in the dependency graph and stay abstract;
  volatile shards depend on stable interfaces.
- "Splitting one topic by size" has **no unified anti-pattern name** in the
  literature; this project's local term is "capacity-driven semantic
  fragmentation" and must not be presented as an established term.

### 4.3 Module-rename protection in the Python ecosystem

- **PEP 594**: deprecate → keep for two feature releases → remove; widely
  used modules get postponed or exempted. <https://peps.python.org/pep-0594/>
- **Django**: deprecations kept at least two feature releases; old modules
  keep compatibility shims.
  <https://docs.djangoproject.com/en/dev/internals/release-process/>
- **NumPy NEP 23/52**: decisions driven by measured downstream usage; even
  the NumPy 2.0 cleanup kept a `numpy.core` stub importing the new location
  with a warning (essential once paths leak into serialized data); the
  public API is frozen via machine-checkable allow-list tests.
  <https://numpy.org/neps/nep-0023-backwards-compatibility.html>;
  <https://numpy.org/neps/nep-0052-python-api-cleanup.html>
- Technical toolkit: an old module file as re-export shim (the only reliable
  protection for `import pkg.old`), PEP 562 module `__getattr__` (for
  attribute-level deprecation warnings), `DeprecationWarning` with correct
  `stacklevel`, CI testing both old and new paths.
- Precedent for **stable top + volatile subdivisions**: NumPy's stable main
  namespace over private `_core`/`*_impl` implementation layers — the
  Facade pattern: the public layer is named by knowledge ontology, the
  private layer by implementation shards, and optimizer output is never
  promoted to a public concept.

---

## 5. Wikipedia Category Governance

### 5.1 Structural facts

- About 2.6 M category pages (2026); a multi-inheritance directed graph
  whose normative goal is "approximately a DAG" but which actually contains
  cycles patrolled by bots; the research literature calls it a noisy
  pseudo-hierarchy — long paths unreliable, cleaning required before use as
  a taxonomy (Aghaebrahimian et al. 2022,
  <https://journals.sagepub.com/doi/10.1177/0165551520977438>;
  Ponzetto/Strube 2007, <https://cdn.aaai.org/AAAI/2007/AAAI07-228.pdf>).
- Its purpose is **navigation, not a knowledge ontology** (Voß:
  a collaborative thesaurus, <https://arxiv.org/abs/cs/0604036>); the top
  level is mostly stable but undergoes occasional costly mass
  reorganizations (Suchecki et al., <https://arxiv.org/abs/1203.0788>).

### 5.2 Existence criterion for a category: definingness

<https://en.wikipedia.org/wiki/Wikipedia:Categorization>

Whether a category should exist depends not on "how many members it has
right now" but on:

1. whether reliable sources **commonly and consistently** describe members
   by that concept (defining characteristic);
2. whether reviewable inclusion/exclusion criteria can be written down;
3. whether it genuinely improves navigation and has growth potential;
4. whether the name is neutral, recognizable, and not a duplicate of an
   existing category.

"Verifiable" is far weaker than "deserves a category"; verifiable but
non-defining attributes belong in lists, not categories.

### 5.3 Overcategorization anti-patterns (WP:OVERCAT)

<https://en.wikipedia.org/wiki/Wikipedia:Overcategorization>

The four most relevant to this project:

- **Arbitrary thresholds** ("places with income over $30,000") — the
  isomorph of "cut every 300 assertions"; a cutoff without domain
  justification does not deserve to be an ontological boundary;
- **misc/other/unknown catch-all categories** — the only shared property of
  members is "classification failed"; the correct move is letting members
  stay in the parent (the shape of our `alternative_systems` module);
- **Trivial intersections**: the existence of A and B does not entitle A∩B
  to exist independently;
- **Subjective adjective names** (famous/important/large): no stable,
  reviewable boundary.

### 5.4 Change governance (CfD)

<https://en.wikipedia.org/wiki/Wikipedia:Categories_for_discussion>

- Any editor may nominate; discussions run at least 7 days and close on
  rough consensus;
- **Two tracks**: C2 speedy (typos, alignment with established naming
  conventions, matching the eponymous main article, etc., 48 hours without
  objection) versus full discussion (creation/split/merge/boundary changes);
- **Semantic decisions separated from mechanical migration**: humans decide
  the outcome, bots rewrite the members in bulk;
- **Renames strictly distinguished from boundary changes**: only when
  semantics are entirely unchanged is it a rename (mechanically migratable);
  when members require case-by-case placement it is a split/merge and needs
  per-member mappings;
- Category soft redirects are not transparent (members of the old category
  do not automatically appear in the new one; bots clean up over time) —
  officially acknowledged as costly. **The ABI lesson**: module paths need
  genuinely resolvable, testable hard shims; soft redirection does not
  transfer.

### 5.5 Non-diffusing subcategories: a pragmatic facet patch

Cross-cutting subsets (such as "women novelists") do not remove members from
the main class ("novelists") — the primary axis stays complete, cross-cutting
dimensions remain independently browsable, and othering is avoided. Mapped to
module systems: **the path encodes exactly one stable primary axis**; other
dimensions (syntactic/semantic level, classical/constructive, etc.) go
through metadata channels, not the path; a cross-cutting dimension is
promoted to a path level only when it forms an independent API boundary with
a stable dependency direction.

### 5.6 Governance forms compared

- CfD (open consensus): broad coverage, fast response, auditable; but
  case-by-case accretion breeds global inconsistency, backlogs, and uneven
  expertise.
- MSC-style committee (centralized): strong global orthogonality and
  notation stability; but slow updates and limited throughput.
- **Synthesis for a small team: open proposals, centralized approval,
  automated migration** — structured RFCs (required fields: definingness,
  inclusion/exclusion criteria, parent placement, overlap analysis, growth
  expectation, migration plan) → centralized maintainer adjudication →
  two-track triage → resolutions recorded in-repo together with
  machine-readable old-to-new mappings → shims/codemods/lints execute the
  migration.

---

## 6. Input Checklist for the Partition Standard Project

Adjudication candidates the future normative project should draw from this
document (each backed by the sources above):

1. **Three-layer decoupled architecture** (§0): knowledge tree / public
   module ABI / private physical shards; K values and graph cuts act only on
   L3, and L1/L2 do not drift with them.
2. **Refinement constraint** as a hard gate for regular releases (§1.3);
   merges/reshuffles restricted to major versions with bidirectional mapping
   tables (§3.1 MSC, §3.3 OBO precedents).
3. **Topic existence test**: the three definingness questions (§5.2) go into
   the plan schema; a new topic must pass before receiving a public path.
4. **Anti-pattern list** (fail-closed validation or review checklist):
   capacity-driven semantic fragmentation (§4.2), arbitrary threshold
   boundaries, catch-all modules, subjective naming, trivial intersections
   (§5.3).
5. **Four change classes**: rename / split / merge / boundary-change (§5.4),
   each with its own approval and migration obligations.
6. **Identifier separated from display name** (§3.2/§3.3): stable module ID
   + current canonical path + zh/en display names + MSC alignment code
   (metadata, not identity).
7. **ABI protection**: hard shims at old paths + `DeprecationWarning` + a
   window of at least two releases + CI testing old imports + a public
   manifest diff gate (§4.3).
8. **Stability metrics**: VI (§1.3) or MoJoFM (§4.1) distance to the
   previous version, cross-parent migration counts, old-import success rate
   — all entering the release acceptance gates.
9. **Name generation**: labels discriminative relative to parents and
   siblings (§1.4); before using set.mm's section structure as the skeleton
   seed, test its structural correlation first (Peel et al.).
10. **Governance**: RFC template + two tracks + resolutions and mappings
    recorded in-repo + automated migration toolchain (§5.6).

---

## 7. Relationship to Existing References

- This document is the third track alongside
  [Reference 011](011-language-as-first-class.en.md) (language as first-class)
  and [Reference 013](013-proof-api-for-verification-construction-search-and-exchange.en.md)
  (the proof API): the **knowledge organization track**. Module paths are
  where the semantic package's public authoring surface
  ([Project 025](../projects/025-semantic-source-surface.en.md)'s generated
  source surface) meets the downstream import ABI.
- Terms such as "capacity-driven semantic fragmentation", "refinement
  constraint", and "definingness test" must be registered through the
  [terminology standard 000](000-terminology.zh.md) process when the
  normative project lands them.
