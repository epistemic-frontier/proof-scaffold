# Project 027: Prelude Boundary RFC

> Status: RFC draft (2026-07-19, drafted from user adjudications);
> the prelude remains in its current minimal pre-logic state (three adjudications); this document raises the boundary
> question and freezes the decision framework and negative adjudications, while the candidate boundary awaits a future decision (§12).
>
> Packaging-topology update ([Project 028](028-top-level-knowledge-release-units.en.md),
> 2026-07-20): this RFC remains authoritative for Prelude content and the capability-slice principle,
> but its earlier package-topology sketches are superseded. `metamath-prelude` is a separate,
> explicitly locked infrastructure release outside the sixteen mathematical roots. Mathbox knowledge,
> community, and governance organization is outside this project's scope.
>
> Upstream: [Project 026 §2.1](026-package-evolution-standard.en.md) (commissioning the prelude
> content standard), [Terminology Standard 000 §13](../references/000-terminology.en.md).
> Handoff targets: the metamath-prelude repository (boundary implementation) and the partition repository (empirical statistics).
>
> In this document, “MUST,” “MUST NOT,” and “SHOULD” have normative meanings.

---

## 0. Adjudication Summary

**Current position (three adjudications on 2026-07-19): the prelude remains in its current minimal
pre-logic state and will not be expanded for now.** This RFC's role is to **raise**
the boundary question and freeze the decision framework for future adjudication:

- **Candidate boundary** (if expanded in the future): through set/class basics, relations, and functions
  (equivalence and quotients remain to be adjudicated), close to set.mm's native layering; empirical baseline: 1,370
  nodes / 18 axioms (pilot-report postscript); **whether and when to expand remains
  an open question** (the first item in §12);
- **Negative adjudications remain frozen**: the prelude MUST NOT absorb content upward along the disciplinary ladder of “logic—sets—numbers—linear algebra—
  calculus”; natural numbers (including the ω system), finiteness,
  induction, and finite recursion are excluded (second adjudication; see the note after §4.1); linear algebra
  belongs to the `linear_algebra` root (through `algebra`), while calculus belongs to the `analysis` root;
- The prelude boundary criterion is **general theory-building capability**, not “commonly used mathematical
  content”; the migration unit is the capability slice (§3);
- Application scenarios such as learning and program verification are assembled through **profiles** (aggregation entry points)
  and MUST NOT exert reverse pressure on the foundation layer;
- The Prelude is an infrastructure release rather than a mathematical package root. Its compatible symbols may be
  implicit in an object-theory surface, but its installation dependency, version, content digest, and verification lock
  MUST be explicit. It does not alter Project 028's closed list of sixteen mathematical roots;
- Mathbox material is not classified, released, promoted, or governed by this RFC.

## 1. Correcting the Goal: “Depends Only on the Prelude” Is Not a Good Metric

“Future Hoare logic and separation logic depend only on the prelude” sounds clean, but if the
prelude keeps expanding, “depends only on the prelude” merely hides complex dependencies inside one
large package. The metrics genuinely worth pursuing are:

- A small transitive dependency closure;
- Explicit axiomatic commitments;
- Controlled verification and loading costs;
- Stable public interfaces;
- No forced imports of unrelated domains.

Accordingly, an intermediate foundation such as `metamath-program-foundation`, or a
`metamath-program-profile` aggregation entry point, is allowed; everything needed by software semantics need not be
stuffed into the global prelude. A profile is an infrastructure-release role, not a third release kind; the detailed
role of the program foundation remains open. Neither may claim one of Project 028's sixteen mathematical roots or
introduce another mathematical root without a new adjudication.

## 2. Boundary Principle: A Construction Toolkit, Not a Mathematics Catalog

> The prelude provides the **representational primitives, composition mechanisms, and finite constructions** needed to define new theories;
> it does not directly carry the principal objects and substantive theory of any specific mathematical domain.

## 3. Migration Unit: Capability Slice

For Metamath, migrating an individual label is usually meaningless. A construction must at least
bring with it:

- Formation/well-formedness rules;
- Closure rules;
- Equality and substitution rules;
- Introduction, elimination, or evaluation rules;
- Any necessary recursion or induction principles.

The migration unit MUST be a **capability slice**: the minimal usable capability closure. For example, “function” does not
mean only the definition of a function; it also includes function values, domain, range, restriction, composition, image, and
inverse image, together with the corresponding equality rules.

(This standard **replaces** the original wording in 026 §2.1, “include constructors only, not theorems”:
a capability slice necessarily contains theorem/axiom-level rules and principles; the boundary criterion is **capability**
rather than a statement's syntactic category.)

## 4. Inclusion/Exclusion Boundary Table

### 4.1 Suitable for the Prelude

| Capability | Adjudication |
| --- | --- |
| Basic formation and inference for propositional and first-order logic | Include |
| Equality, substitution, variable constraints, and binding mechanisms | Include |
| Basic expression of sets, classes, and membership | Include |
| Ordered pairs, Cartesian products, relations, and functions | Include |
| Function composition, restriction, image, and inverse image | Include |
| Infrastructure for equivalence relations and quotient constructions | May include (pending adjudication) |
| General operations such as disjoint union, restriction, and local update | Include |
| General vocabulary needed to define algebraic structures | Pending empirical evidence (outside the corpus, and set.mm structure slots are indexed by ℕ; see §12) |

**Postscript (second adjudication, 2026-07-19)**: the initial draft listed three rows as included:
“finite tuples/sequences/indexed families,” “natural numbers, finiteness, induction, and finite recursion,” and “general finite iteration/fold,”
on the grounds of the metalanguage role of natural numbers (length, indexing, recursion depth,
and finiteness proofs). After the pilot evidence (partition repository,
`reports/corpus/prelude-naturals-pilot.md`), the user adjudication **reversed** that decision:

- Although the ω system is technically safe (a closure of 19 axioms, without `ax-inf`), 2,479 nodes
  / 14.4% of the corpus is too much to include;
- Having the prelude own ω while the `number_systems` root owns ℕ—the “two natural numbers” arrangement—is not fully consistent with mathematical
  tradition;
- set.mm's practical infrastructure (`seq`/`fz`/`word`) is already ℕ-based,
  while the ω-based `seqom` has only 95 transitive dependents, leaving no corpus with which to stress-test a self-built thin version.

Therefore all three rows move out of the Prelude: ω, finiteness, induction,
and finite recursion belong to the **`set_theory` root**. The historical
“route B” decision fixed exclusion from Prelude, not proof-dependency-shaped
public ownership under Project 028. Finite-sequence and word concepts are
publicly owned by `combinatorics`; numerically indexed provider implementations
may require `number_systems`. Exact `seq`/`fz`/`word` label allocation remains a
statement-level review. Summation, matrix multiplication, and program-state
updates obtain those providers through explicit mathematical-release
dependencies, not through the Prelude.

### 4.2 Retained in Mathematical Roots

| Content | Location |
| --- | --- |
| ω, finiteness, induction, finite recursion (`rdg`/`seqom`) | `set_theory` |
| Finite sequences and words; indexed-family/fold machinery (`seq`/`fz`/`word`) | Public subject in `combinatorics`; numeric providers may require `number_systems`; exact label ownership pending |
| Natural numbers ℕ and arithmetic (`df-nn`, including the `om2uz` bridge) | `number_systems` |
| Integers and negative-number operations | `number_systems` |
| Rational numbers and exact ratios | `number_systems` or `algebra` (pending ownership adjudication) |
| Divisibility, congruence, primes, gcd | `number_theory` |
| Full theory of groups, rings, fields, and modules | `algebra` |
| Lattices, partial orders, and fixed-point theory | `order_theory` |
| Finite counting and combinatorial objects | `combinatorics` |
| Finite graphs and hypergraphs | `graph_theory` |

## 5. Linear Algebra and Calculus

**Linear algebra** is closer to infrastructure than calculus, but still introduces an entire suite of domain structures
(scalar fields, vector spaces/modules, linear maps, matrix representations, bases/dimension/rank, inner-product
norms, and the finite/infinite-dimensional split). The mechanisms that make
the linear-algebra package **thin** are provided in several roles: Prelude
supplies function and relation basics, `set_theory` supplies set-level
foundations, `number_systems` supplies numeric indexing providers, and
`combinatorics` owns finite-sequence/fold facades. Prelude MUST NOT directly
contain vector-space and matrix theory. An illustrative provider ordering is
`metamath-prelude → metamath-set-theory / metamath-number-systems →
metamath-combinatorics / metamath-algebra → metamath-linear-algebra`; the
exact release DAG is validated from the selected snapshot rather than frozen
by this RFC.

**Calculus** is even less suitable: it is not a lightweight additional layer and would quickly introduce construction of the real numbers,
sequences and limits, completeness, topology, continuity, derivatives and integrals, and even metric spaces,
measure, and choice principles. Once linear algebra and calculus are included to “express learning,”
probability, measure, optimization, convex analysis, tensors, and numerical error soon follow—the prelude then
becomes a mathematics curriculum catalog rather than a foundation layer.

Learning-related capabilities are organized as a profile:

```text
metamath-learning-profile                 (infrastructure profile; no mathematical root)
├── metamath-linear-algebra              → linear_algebra
├── metamath-analysis                    → analysis
├── metamath-probability                 → probability
└── optional infrastructure providers/views (infrastructure roles; no mathematical root)
```

Optimization and finite-computation views may be supplied by later infrastructure providers, but this example does not
authorize `optimization` or `finite_computation` as additional mathematical roots.

There are also lightweight learning branches that do not require calculus (symbolic learning, finite-model learning,
and combinatorial search).

## 6. The Actual Foundation for Formal Methods in Software

Hoare logic, operational semantics, and separation logic do not require linear algebra or calculus. Their common
foundation consists of syntax trees and finite sequences; variables, environments, and states; functions, relations, and relation
composition; natural numbers and induction; partial functions/finite maps; disjoint union and local update; transition
systems and reachability relations; and (for separation logic) partial commutative monoids / separation algebras.

Division of responsibility: the prelude provides **mechanisms** such as
relations, functions, and local updates; finite-sequence subjects come from
`combinatorics`, while natural numbers, numeric providers, and induction come
from `set_theory` and `number_systems` (explicit release dependencies; see
§1—“depends only on the prelude” is not the goal);
`metamath-program-foundation` defines **subject matter** such as states,
heaps, transition systems, and separation algebras. Dependencies remain shallow, and
program-logic-specific subject matter is not frozen into every mathematical package.

**Note**: this section only specifies “what program methods need and do not need”;
**how** program foundation and program profile enter the release ecosystem
(the program foundation's release role and dependency shape with `set_theory`,
`number_systems`, and `combinatorics`, plus the
infrastructure profile's members and versioning policy) remains an open question (§12) and is not settled by this RFC.
Whatever that later decision is, these releases MUST NOT claim or modify any of Project 028's sixteen mathematical roots.

## 7. Candidate Generation and Selection Metrics

set.mm dependency frequency **may only generate candidates; it MUST NOT directly determine the prelude**.
High frequency has three causes:

1. Genuine cross-domain foundational status;
2. Hubs created by set.mm's current encoding style;
3. Large unified structures carrying many smaller structures, artificially inflating frequency (especially number systems, class expressions,
   and unified arithmetic structures).

Five metrics must be calculated for every candidate capability slice:

| Metric | Meaning | Direction |
| --- | --- | --- |
| Usage frequency | Number of proofs using it directly/indirectly | + |
| Domain-distribution entropy | Whether use is dispersed across many domains | + |
| Closure cost | Size of prerequisites that must move with it | − |
| Axiom cost | Whether it introduces commitments such as infinity/choice/completeness | − |
| Interface stability | Likelihood that a better representation will emerge | − (volatility) |

Selection objective (illustrative):

```text
PreludeValue = (frequency × cross-domain-breadth × reconstruction-cost)
             / (closure-size × axiom-cost × API-volatility)
```

Only **high frequency combined with broad domain distribution** makes a strong candidate; a high-frequency construction concentrated in one domain
remains in its owning mathematical root. The migration unit is the capability slice after dependency closure, not the top N
labels in a ranking (the absorption-rate calibration of the prelude in 026 §2.1 is therefore formally demoted to a stress-test
baseline; see §11).

## 8. Two-Layer Prelude: Separating Semantic Foundations from Authoring Economy

ProofScaffold has Python as its host language and must distinguish:

1. **Object-theory prelude**: the normative subject of this RFC;
2. **Python API / elaboration-layer prelude**: authoring conveniences.

Matrix literals, tensor-index syntax, bounded summation, record/structure definitions,
program-state update syntax, and convenient constructors for finite lists and maps are expanded by the Python layer
into smaller object-theory primitives; they MUST NOT be implemented by expanding the object theory.

> The prelude is responsible for semantic foundations; the Python layer is responsible for authoring economy.

This substantially reduces the pressure to put linear algebra, program data structures, or even machine-learning notation into the
Metamath prelude.

Neither layer is a seventeenth mathematical root. `metamath-prelude` is installed and versioned as a separate
infrastructure release; its version, content digest, and verification environment MUST be explicitly locked even when
compatible Prelude symbols are implicitly available inside the object theory.

## 9. Release Topology Under Project 028

[Project 028](028-top-level-knowledge-release-units.en.md) supersedes the earlier package-structure sketch in this section.
The effective V1 topology is:

```text
infrastructure release
└── metamath-prelude    (no mathematical Python root; explicitly installed and locked)

mathematical release roots
├── logic               ├── set_theory          ├── number_systems
├── order_theory        ├── category_theory     ├── algebra
├── linear_algebra      ├── topology            ├── geometry
├── analysis            ├── measure_theory      ├── probability
├── number_theory       ├── combinatorics       ├── graph_theory
└── computer_science

additional infrastructure-release roles
├── aggregation profile         (for example, metamath-program-profile)
└── implementation provider
    (roles/subtypes of infrastructure release; neither owns or adds a mathematical root)
```

Each mathematical root is owned by exactly one mathematical release, and each mathematical release owns exactly one root.
There is no `metamath_knowledge` wrapper. Distribution names remain separately namespaced as specified by Project 028.

**A profile contains only stable aggregate dependencies and MUST NOT own underlying definitions or a mathematical root.**
It provides an out-of-the-box experience without breaking theory boundaries.

How the program-methods branch (`program-foundation` / `hoare-logic` /
`separation-logic` / `program-profile`) enters remains an open question (§12). It may not change the frozen sixteen-root
allowlist or introduce a root implicitly.

Mathbox organization is not part of this topology. This RFC does not classify, release, promote, or govern mathbox
statements, and it does not model mathbox as a generic frontier package.

## 10. Empirical Plan (MUST Be Completed Before Quantitatively Adjudicating the Boundary)

On the graph of the exactly declared, non-mathbox target in the partition repository (and subsequently expanded,
explicitly scoped non-mathbox corpora):

1. **Delimit capability slices**: using the §4.1 table as a guide, manually identify each slice's seed-label
   set, then mechanically compute its rule closure (formation/equality/introduction-elimination/induction);
2. **Compute the five metrics**: frequency (direct + transitive indegree), domain-distribution entropy (normalized entropy across included
   mathematical roots; the historical pilot used five regions),
   closure cost (size of the transitive prerequisite closure), axiom cost (occurrences of
   `ax-inf`/`ax-ac`/`ax-rep`, etc. in the closure), and interface stability (manual
   rating);
3. Produce a **ranked table of candidate slices** and cross-check it against the qualitative adjudications in §4.1: report for individual adjudication any
   qualitatively included item with weak metrics, or strongly scoring item that is qualitatively excluded;
4. Analyze the set difference between the current empirical 215-label prelude and the capability-slice boundary (which glue
   lemmas belong to a capability slice, and which are merely high-frequency theorems that should fall back to their mathematical roots).

## 11. Relationship to Existing Work

- This RFC adjudicates the suspended question in **026 §2.1**: the prelude's role = construction
  toolkit (at capability-slice granularity), neither “constructors only” nor a “high-frequency foundation layer”;
  the `--prelude-floor` absorption-rate calibration mechanism is **retained but demoted** to a stress-test
  baseline tool and no longer determines prelude content.
- [Project 028](028-top-level-knowledge-release-units.en.md) supersedes the old packaging topology: the Prelude is a separate
  infrastructure release and Foundation Unit outside the sixteen mathematical roots. Its object-theory symbols may be implicit only
  under an explicit installation dependency, version, content digest, and verification lock.
- A profile is a definition-free infrastructure-release role containing only aggregate dependencies. Program foundations and profiles may
  not claim or modify the sixteen mathematical roots; the program foundation's release role and the profile's membership/version policy
  remain open in §12.
- The historical five-zone corpus's `prelude.core` (215 labels) remains a stress-test
  baseline until the §10 empirical work is complete and the capability-slice prelude is implemented.
- Mathbox is outside this RFC's source scope and governance authority; it is neither a Prelude candidate pool nor an automatic frontier.

## 12. Pending Adjudication

- **Whether and when the prelude should expand from minimal pre-logic to the candidate boundary**
  (set/class basics + relations and functions, §0)—three adjudications maintain the status quo;
  expansion requires a new adjudication trigger; until then, the §4.1 table is a candidate list, not an effective boundary;
- Whether equivalence relations and quotient constructions should be included in the first batch (“may include” in the table);
- Ownership of rational numbers between `number_systems` and `algebra`;
- An operational definition for interface-stability ratings;
- Profile versioning policy (pinned member versions vs floating);
- The “vocabulary for defining algebraic structures” slice (the `df-struct` family) lies outside the current corpus's
  `[0, cstr)` range, so empirical evidence awaits corpus expansion; note that set.mm's extensible structures
  use ℕ-indexed slots (`df-ndx`/`df-slot`), so the slice will likely also depend on the
  `number_systems` and be unable to enter the prelude, in which case an alternative structure-definition mechanism must be
  adjudicated at the same time;
- Whether `df-map` (function spaces) enters with the relation/function slice: inclusion adds the axiomatic commitments
  `ax-un`/`ax-pow` (closure 1,370→1,632 nodes and 18→20 axioms; see the
  pilot-report postscript);
- **How program foundation / program profile enters** (explicitly retained by the user as an open question): the program
  foundation's release role and dependency shape with `set_theory`,
  `number_systems`, and `combinatorics`, and which members and versioning
  policy the infrastructure profile `metamath-program-profile` aggregates. A profile remains an infrastructure-release
  role/subtype, not a third release kind. Neither release may become a domain inside, claim, or modify the frozen sixteen
  mathematical roots; the relevant entries in §6/§9 are illustrative sketches only and do not constitute an adjudication.

Mathbox knowledge, community, and governance organization is explicitly not a pending Prelude-boundary question and is
not handled by this project.

Adjudicated (second adjudication, 2026-07-19; formerly two §12 items): **natural numbers do not enter the
prelude**—both the ω system and arithmetic ℕ move down (§4.1 postscript);
finite sequences/fold take route B (remain outside Prelude; Project 028
separates `combinatorics` public ownership from `number_systems`-based numeric
providers; no self-built thin ω-based version).

## 13. Implementation History

- 2026-07-19: RFC drafted from user adjudications; qualitative boundary (§0–§9) settled,
  with the empirical plan (§10) scheduled for the partition repository's next round.
- 2026-07-19: the first §10 pilot was completed (natural-number capability slice, partition repository,
  `reports/corpus/prelude-naturals-pilot.md`). It answered the user's adjudication
  question, “Can natural numbers safely be put in the prelude while keeping compilation output aligned with the beginning of set.mm?”:
  **the ω system can** (19 axioms, no `ax-inf`, emitted as an order-preserving subsequence of the beginning of set.mm,
  with prefix density 32.6%—alignment holds only in the subsequence sense,
  consistent with the judgment that “mm is a linearization of a DAG”); **arithmetic ℕ cannot**
  (its closure pulls in the complete ℂ axiomatization and ch4 material). By-product: the 215-label frequency-based
  prelude leaked 28 ch4–5 labels (`cc`/`cr`/`cn`/`ax-1cn`…),
  so the axiom-cost metric vetoes frequency calibration and validates the causes 2/3 predicted in §7.
  Three pending adjudications were added (§12).
- 2026-07-19: **second adjudication (boundary rollback)**. Because the ω-system closure of 2,479
  nodes / 14.4% was too much to include, and the “two natural numbers” arrangement was not
  fully consistent with mathematical tradition, the user adjudicated that natural numbers (including ω) do not enter the prelude, rolling the boundary back to
  set/class basics + relations and functions, close to set.mm's native layering; finite sequences/
  fold take route B and move down. Revised §0/§4/§5/§6/§9/§12. Post-rollback prelude
  empirical baseline: 1,370 nodes (8.0%), 18 axioms (without `ax-un`/`ax-pow`/
  `ax-inf`); the variant including `df-map` has 1,632 nodes and 20 axioms (data in the
  partition repository pilot-report postscript).
- 2026-07-19: How program foundation / program profile enters was
  explicitly **retained as an open question** by the user (§12); the relevant §6/§9 entries were demoted to
  illustrative sketches.
- 2026-07-19: **third adjudication (position converged)**. The prelude remains in its current minimal
  pre-logic state and will not be expanded for now; “whether/when to expand to the candidate boundary (sets/
  classes + relations and functions)” was promoted to the first open question in §12. This RFC's position changed from
  “boundary settled” to “raise the question + freeze the decision framework + preserve the empirical baseline”;
  the negative adjudications (ban on the disciplinary ladder, exclusion of natural numbers, frequency veto, capability-slice
  unit, and profile mechanism) remain frozen.
- 2026-07-20: [Project 028](028-top-level-knowledge-release-units.en.md) superseded this RFC's package-topology sketches without
  changing its Prelude content boundary. Prelude became a separate, explicitly locked infrastructure release outside the frozen
  sixteen mathematical roots; examples were remapped to the new roots, program releases were barred from changing the allowlist,
  and mathbox was recorded as outside this project's scope.
