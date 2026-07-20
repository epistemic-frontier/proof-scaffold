# Project 028: Top-Level Knowledge Packages as Release Units

> Status: normative V1 package-root adjudication (2026-07-20).
>
> Decision: the set.mm V1 public knowledge surface has sixteen bare
> top-level mathematical Python packages. Each package is the public root of
> exactly one mathematical domain and the release unit of exactly one
> mathematical distribution.
>
> Normative basis: [Reference 017](../references/017-ontology-first-knowledge-organization.md),
> [Terminology Standard 000](../references/000-terminology.en.md),
> [Project 025](025-semantic-source-surface.en.md),
> [Project 026](026-package-evolution-standard.en.md), and
> [Project 027](027-prelude-boundary-rfc.en.md).
>
> Explicit exclusion: mathbox organization, ownership, review, maturity,
> promotion, and statement placement are not adjudicated here. Mathboxes are
> not a seventeenth mathematical package.
>
> In this document, “MUST,” “MUST NOT,” and “SHOULD” have normative meanings.

---

## 0. Decision

The V1 public import-root allowlist is:

```text
logic
set_theory
number_systems
order_theory
category_theory
algebra
linear_algebra
topology
geometry
analysis
measure_theory
probability
number_theory
combinatorics
graph_theory
computer_science
```

The order above is presentational. It is not a dependency order.

For V1:

1. each name is a bare top-level Python import root;
2. each root represents one mathematical domain;
3. each root is owned by exactly one mathematical release package;
4. each mathematical release package owns exactly one root;
5. no `metamath_knowledge` or other project-wide content wrapper appears in
   the public import path;
6. adding, removing, or renaming a root requires a new adjudication and a
   migration plan.

This is a closed V1 list, not a claim that these are the only mathematical
disciplines that can ever exist.

---

## 1. Release Matrix

Three names that were previously conflated are now distinct:

| Field | Example | Meaning |
|---|---|---|
| `release_unit_id` | `combinatorics` | Stable ecosystem identifier for the mathematical release unit |
| `python_root` | `combinatorics` | Bare public Python import root |
| `distribution_name` | `metamath-combinatorics` | Installation and publication name |

V1 deliberately keeps `release_unit_id` and `python_root` textually equal,
while keeping the distribution name separately namespaced.

Each row is one mathematical release unit. The following four roles form a
bijection in V1:

```text
top-level mathematical domain
    ↔ mathematical release unit/package (`release_unit_id`)
    ↔ bare public Python root (`python_root`)
    ↔ published distribution (`distribution_name`)
```

The names identify different architectural roles even when two fields have
the same spelling.

The textual equality `release_unit_id == python_root` is only the initial V1
assignment. A later root rename follows an explicit migration and does not
automatically rename the stable `release_unit_id`.

| Release unit | Python root | Distribution | Defining mathematical scope |
|---|---|---|---|
| `logic` | `logic` | `metamath-logic` | Propositional and predicate logic, equality, alternative calculi, natural deduction, modal and provability logic, metamathematics, and quantum logic |
| `set_theory` | `set_theory` | `metamath-set-theory` | Classes, sets, relations, functions, ZF/ZFC/TG, ordinals, cardinals, choice, universes, set recursion, and set-theoretic models |
| `number_systems` | `number_systems` | `metamath-number-systems` | Natural, integer, rational, real, complex, extended-real, and surreal number systems and their basic operations |
| `order_theory` | `order_theory` | `metamath-order-theory` | Preorders, partial and total orders, well-orders, chains, lattices, directed sets, and closure systems |
| `category_theory` | `category_theory` | `metamath-category-theory` | Categories, functors, natural transformations, universal constructions, and Kan extensions |
| `algebra` | `algebra` | `metamath-algebra` | Magmas, monoids, groups, rings, fields, modules, ideals, polynomials, and field extensions |
| `linear_algebra` | `linear_algebra` | `metamath-linear-algebra` | Vector spaces, free modules, linear maps, matrices, determinants, characteristic polynomials, and inner-product structures |
| `topology` | `topology` | `metamath-topology` | General topology, filters, uniform and metric spaces, compactness, connectedness, and algebraic topology |
| `geometry` | `geometry` | `metamath-geometry` | Tarskian, Euclidean, affine, projective, plane, and Hilbert-space geometry |
| `analysis` | `analysis` | `metamath-analysis` | Limits, continuity, differentiation, series, real and complex analysis, special functions, Fourier analysis, and functional analysis |
| `measure_theory` | `measure_theory` | `metamath-measure-theory` | Sigma-algebras, measures, outer measures, measurable functions, and measure-theoretic integration |
| `probability` | `probability` | `metamath-probability` | Probability spaces, random variables, distributions, expectation, variance, and discrete probability |
| `number_theory` | `number_theory` | `metamath-number-theory` | Divisibility, congruences, primes, Diophantine equations, algebraic number theory, and analytic number theory |
| `combinatorics` | `combinatorics` | `metamath-combinatorics` | Finite counting, words, cyclic shifts, permutations, partitions, Ramsey theory, and Van der Waerden theory |
| `graph_theory` | `graph_theory` | `metamath-graph-theory` | Graphs and hypergraphs, subgraphs, walks, paths, cycles, connectivity, Eulerian paths, and special graphs |
| `computer_science` | `computer_science` | `metamath-computer-science` | Algorithms, digit and bit representations, recursive functions, computability, and complexity theory |

The table fixes primary public ownership criteria. It does not deny secondary
facets. A theorem may be discoverable through several concepts while having
one canonical release owner.

### 1.1 Infrastructure exceptions

`metamath-prelude` is a separate infrastructure release and Foundation Unit,
not a seventeenth mathematical root. Its symbols may be implicitly available
inside a compatible object-theory surface, but its installation dependency,
version, content digest, and verification lock MUST remain explicit.

Definition-free profiles and implementation-provider releases are also
infrastructure releases. They MUST NOT claim one of the sixteen roots or add
another mathematical root implicitly.

---

## 2. Evidence from the Current set.mm

The inventory used for this adjudication is upstream `metamath/set.mm`
`origin/develop` commit `4b2cea80` (2026-07-20):

- 873,122 source lines;
- 3,000 `$a` assertions;
- 47,543 `$p` assertions;
- 50,543 formal assertions in total;
- 17,780 assertions in the mathbox region, about 35.2% of the corpus.

The physical source regions are valuable evidence but are not the package
taxonomy:

- `set-num.mm` mixes number systems, finite counting, words, limits, series,
  and trigonometry;
- `set-numth.mm` mixes elementary number theory with words, necklaces,
  Ramsey theory, and Van der Waerden theory;
- `set-numfunc.mm` mixes analysis, number theory, probability examples, and
  geometry;
- `set-hilsp.mm` mixes inner-product and Banach-space mathematics with
  Hilbert lattices and quantum logic;
- extensible structures are a formal encoding mechanism, not evidence for a
  public catch-all package named `structures`.

Therefore the transpiler MUST NOT obtain the sixteen roots by renaming source
intervals. Statement ownership requires a curated, noncontiguous
classification plan.

### 2.1 Explicit source scope

Every classification and release plan MUST declare the exact source snapshot
and included regions. “Complete coverage” means complete coverage of that
declared target, not silently complete coverage of all concatenated set.mm.

This project freezes roots and release units. It does not yet adjudicate the
publication status of guides, humor, deprecated material, typesetting
material, or the legacy Hilbert-space region. Those regions require explicit
lifecycle decisions before a release plan includes or excludes them.

### 2.2 Bootstrap mapping of authored regions

The following table generates review candidates only. Mixed regions require
statement-level classification and MUST NOT be moved as indivisible blocks.

| Authored region | Candidate mathematical roots |
|---|---|
| `set-pred.mm` | `logic` |
| `set-class.mm` | `set_theory`, with residual logical interfaces reviewed for `logic` |
| `set-zf.mm` | `set_theory`, with finite-set and pigeonhole/Hall material reviewed for `combinatorics` |
| `set-zfc.mm`, `set-tg.mm` | `set_theory` |
| `set-num.mm` | `number_systems`, `combinatorics`, `analysis` |
| `set-numth.mm` | `number_theory`, `combinatorics`, `computer_science` |
| `set-struct.mm` | internal encoding support plus subject-owned declarations, including `order_theory` candidates; no `structures` root |
| `set-cat.mm` | `category_theory` |
| `set-order.mm` | `order_theory` |
| `set-algstr.mm` | `algebra`, with linear/normed structures reviewed for `linear_algebra` and `analysis` |
| `set-linalg.mm` | `linear_algebra`, with general algebra retained in `algebra` |
| `set-top.mm` | `topology`, with normed, Hilbert, and linear material reviewed for `analysis` and `linear_algebra` |
| `set-numanal.mm` | `analysis`, `measure_theory` |
| `set-numfunc.mm` | `analysis`, `algebra`, `number_theory`, `probability`, `geometry` |
| `set-surreals.mm` | `number_systems` |
| `set-tarskigeom.mm` | `geometry` |
| `set-graphth.mm` | `graph_theory` |
| `set-hilsp.mm` | `linear_algebra`, `analysis`, `logic`, subject to its lifecycle status |
| `set-guidesetc.mm`, `set-typeset.mm` | presentation or example metadata, not mathematical roots |
| `set-deprec.mm` | subject owner plus deprecated status; never a `deprecated` root |

`computer_science` has non-mathbox candidates in the bit-sequence and
algorithm regions of `set-numth.mm`, but its first release may remain small.
Those candidates still require statement-level review. No root may be padded
with misclassified material merely to make every distribution nonempty.

---

## 3. Mathbox Is a Separate Governance Problem

The mathbox region combines at least four concerns:

1. mathematical subject classification;
2. contributor and community ownership;
3. review, maturity, and trust status;
4. promotion, migration, archival history, and maintenance authority.

This project decides none of them.

For every Project 028 V1 plan:

- `mathbox` MUST be an explicit excluded source scope;
- mathbox statements MUST NOT be counted as unclassified failures;
- contributor names MUST NOT become mathematical Python roots;
- mathbox MUST NOT be modeled automatically as a generic `frontier` package;
- no automatic promotion or assignment into the sixteen release units is
  authorized by this document.

A later governance project may decide how reviewed mathbox content is aligned
with or promoted into the sixteen roots, how community namespaces coexist
with mathematical ownership, and whether additional release kinds are
needed. Reference 016 remains evidence for that future work, not a normative
mathbox policy for V1.

---

## 4. Ontological Ownership and Implementation Dependencies

The public release owner of a declaration follows mathematical ontology: what
the declaration states and which concept it primarily defines, characterizes,
constructs, or transforms.

The selected proof implementation separately records:

- direct assertion requirements;
- transitive theorem closure;
- assumption and trust closure;
- implementation-local imports;
- build, verification, and backend-emission order.

A proof dependency does not transfer public ownership. For example, a
number-theoretic statement proved by complex analysis remains publicly owned
by `number_theory`; its implementation records the `analysis` requirement.

The concrete implementation dependency graph among mathematical release
units MUST be acyclic. Ontology relations and discovery facets may overlap or
cycle. If ontology-shaped ownership induces an implementation quotient
cycle, the response is to split facade from provider, stage the
implementation, or factor a genuine common interface. The implementation
MUST NOT silently reclassify the public declaration merely to break the
cycle.

Every selected implementation-provider release and physical provider shard
MUST appear in the complete implementation DAG and in the verification lock.
Calling a provider "infrastructure" MUST NOT let it escape dependency,
acyclicity, digest, or trust-closure checks.

Project 025 does not yet represent this facade/provider separation fully.
Full noncontiguous rollout is blocked wherever the current schema cannot
represent an honest acyclic implementation projection.

---

## 5. Python Surface and Lazy Loading

The ordinary public surface is:

```python
from logic.propositional import modus_ponens
from combinatorics.words import cyclic_shift
from number_theory.primes import fermat_little_theorem
```

It is not:

```python
from metamath_knowledge.combinatorics.words import cyclic_shift
```

Each mathematical distribution MUST:

- own one regular top-level Python package;
- expose stable, lightweight assertion handles;
- avoid importing sibling mathematical roots from its top-level
  `__init__.py` merely for aggregation;
- avoid elaborating proofs during package or leaf-module import;
- load implementations and verification closures only on demand;
- ship a manifest and type information sufficient for catalog lookup and IDE
  discovery without importing the whole corpus.

Cross-domain search belongs to a catalog/runtime service. It MUST NOT require
or recreate a project-wide content wrapper.

---

## 6. Plan Contract

The next plan schema MUST make release ownership explicit. A minimal record is:

```json
{
  "schema": "knowledge-release-plan-v1",
  "source": {
    "repository": "https://github.com/metamath/set.mm.git",
    "commit": "4b2cea80cdab6cd1855d7da39d4f6e89ed3fc6f6",
    "scope": {
      "include_manifests": [{"region": "main", "digest": "..."}],
      "exclude_manifests": [
        {"region": "mathbox", "digest": "...", "reason": "governance-deferred"}
      ]
    }
  },
  "release_units": [
    {
      "release_unit_id": "logic",
      "python_root": "logic",
      "distribution_name": "metamath-logic",
      "kind": "mathematical",
      "prelude_lock": "...",
      "modules": []
    }
  ]
}
```

The schema MUST distinguish:

- stable declaration and concept identifiers;
- public root and canonical public owner;
- physical module and shard;
- assertion interface and proof implementation;
- implementation requirements and ontology relations;
- mathematical releases versus infrastructure releases, and profile/provider
  roles within infrastructure releases;
- snapshot-anchored, digest-verified include/exclude manifests that enumerate
  exact source or statement boundaries; a boolean `mathbox: excluded` flag is
  not sufficient.

Python paths are versioned public references, but they are not the stable
mathematical identifiers.

---

## 7. Name Ownership and Collision Safety

V1 uses regular packages, not a multi-owner PEP 420 assembly. One
distribution exclusively owns each root.

Before building or installing a release, tooling MUST reject:

- a root owned by another installed distribution;
- a root colliding with the Python standard library;
- a distribution whose manifest claims a different root owner;
- two release manifests claiming the same root.

`numbers` is forbidden because it is a Python standard-library module;
`number_systems` replaces it. Other standard-library names, including
`math`, `statistics`, `decimal`, `fractions`, `operator`, `types`, `typing`,
`collections`, and `graphlib`, MUST NOT be claimed as mathematical roots.

---

## 8. Normative Invariants

| ID | Invariant |
|---|---|
| R1 | The mathematical-root allowlist is exactly the sixteen names in §0. |
| R2 | Top-level mathematical domains, mathematical release units/packages, public roots, and distribution names form a four-way bijection; every member has exactly one counterpart in each other role. |
| R3 | Public imports begin at the mathematical root; no common content wrapper is generated. |
| R4 | Every in-scope declaration has one canonical public owner; semantic facets remain non-exclusive. |
| R5 | Public ownership is curated from mathematical meaning, not generated from proof dependencies or source intervals. |
| R6 | Implementation requirements are complete, explicit, and separate from ontology relations. |
| R7 | Module, provider/shard, and mathematical-release implementation dependency graphs are complete and acyclic under the verification lock; ontology graphs need not be. |
| R8 | Imports do not elaborate proofs; proof implementations and verification closures load lazily. |
| R9 | Stable identifiers do not derive from Python paths, file locations, or source order. |
| R10 | Mathbox is explicitly outside V1 target coverage and is not represented as a package or classification failure. |
| R11 | `structures`, `miscellaneous`, contributor names, lifecycle states, and source-layout names are not mathematical roots. |
| R12 | Prelude and profiles are explicit infrastructure releases and do not alter the sixteen-root allowlist. |

---

## 9. Acceptance Gates

1. **G0 — terminology:** Terminology Standard 000 and Projects 026–027 agree
   with the one-root/one-release model and the Prelude exception.
2. **G1 — schema:** a validator enforces R1–R12, source scope, root ownership,
   and distribution-name separation.
3. **G2 — vertical slice:** words, cyclic shifts, necklaces, primes, and their
   proof dependencies compile through `combinatorics` and `number_theory`
   without a common wrapper or eager proof loading.
4. **G3 — release smoke test:** all sixteen distributions can be built and
   installed in an isolated environment; each root resolves to its declared
   owner and collides with neither the standard library nor another release.
5. **G4 — semantic and backend verification:** selected proofs elaborate,
   emit deterministically, and pass an independent Metamath verifier under
   exact release and Prelude locks.
6. **G5 — migration:** existing prefixed generated imports have explicit
   mappings, compatibility policy, and diagnostics; no silent aliasing is
   introduced.

Full mathbox classification is not an acceptance gate for Project 028.

---

## 10. Relationship to Projects 026 and 027

This project supersedes these parts of Project 026:

- a release package may contain multiple first-level mathematical domains;
- the first path segment denotes a domain inside one generated wrapper;
- P7 applies only to a domain quotient inside one release package;
- mathbox is automatically a mechanized frontier of the V1 release plan;
- physical proof placement determines public statement ownership.

Project 026 remains authoritative for definingness, stable migrations,
module/import completeness, deterministic generation, and evolution
operations that do not depend on the superseded topology.

Project 027 remains authoritative for the minimal Prelude content boundary
and capability-slice principle. Project 028 changes only its packaging
topology: Prelude is a separate, explicitly locked infrastructure release,
not a layer regenerated inside each mathematical release.

---

## 11. Deferred Decisions

The following are deliberately not decided here:

- mathbox community and knowledge governance;
- statement-by-statement classification across the full corpus;
- the publication status of deprecated, guide, humor, typesetting, and legacy
  regions;
- whether a named bridge topic eventually deserves a new top-level release;
- multi-foundation concept alignment and proof transport;
- repository creation, version numbers, and release cadence for distributions
  not yet implemented.

Until separately adjudicated, a bridge topic such as arithmetic
combinatorics is a subdomain with one canonical root owner and plural
discovery facets, not an implicit seventeenth root.

---

## 12. Implementation Sequence

1. Amend terminology and mark the superseded Project 026/027 topology.
2. Add `knowledge-release-plan-v1` and its root/source-scope validator.
3. Change existing generated roots to bare imports; rename `numbers` to
   `number_systems`.
4. Validate the combinatorics/number-theory vertical slice.
5. Add the remaining mathematical release manifests and classify the selected
   non-mathbox target corpus incrementally.
6. Build the catalog over stable identifiers without adding a content
   wrapper.
7. Begin mathbox work only under a separately adjudicated governance project.
