# Project 027: Prelude Boundary RFC

> Status: RFC draft (2026-07-19, drafted from user adjudications);
> the prelude remains in its current minimal pre-logic state (three adjudications); this document raises the boundary
> question and freezes the decision framework and negative adjudications, while the candidate boundary awaits a future decision (§12).
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
- **Negative adjudications remain frozen**: the prelude must not absorb content upward along the disciplinary ladder of “logic—sets—numbers—linear algebra—
  calculus”; natural numbers (including the ω system), finiteness,
  induction, and finite recursion are excluded (second adjudication; see the note after §4.1); linear algebra
  enters the first-level standard library (through algebra), while calculus enters the analysis library;
- The prelude boundary criterion is **general theory-building capability**, not “commonly used mathematical
  content”; the migration unit is the capability slice (§3);
- Application scenarios such as learning and program verification are assembled through **profiles** (aggregation entry points)
  and must not exert reverse pressure on the foundation layer.

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
stuffed into the global prelude.

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
- Having the prelude own ω while the numbers domain owns ℕ—the “two natural numbers” arrangement—is not fully consistent with mathematical
  tradition;
- set.mm's practical infrastructure (`seq`/`fz`/`word`) is already ℕ-based,
  while the ω-based `seqom` has only 95 transitive dependents, leaving no corpus with which to stress-test a self-built thin version.

Therefore all three rows move down: ω, finiteness, induction, and finite recursion belong to the **set-theory domain**;
practical versions of finite sequences, indexed families, and fold belong to the **numbers domain** (route B).
Summation, matrix multiplication, and program-state updates are built on finite indexed families + fold from the numbers domain
and obtained through normal domain dependencies, not through the prelude.

### 4.2 Retained in Domain Packages

| Content | Location |
| --- | --- |
| ω, finiteness, induction, finite recursion (`rdg`/`seqom`) | `metamath-set` |
| Finite sequences, indexed families, fold (`seq`/`fz`/`word`) | numbers domain |
| Natural numbers ℕ and arithmetic (`df-nn`, including the `om2uz` bridge) | numbers domain |
| Integers and negative-number operations | `metamath-discrete` |
| Rational numbers and exact ratios | `metamath-discrete` or `metamath-algebra` |
| Divisibility, congruence, primes, gcd | `metamath-number-theory` |
| Full theory of groups, rings, fields, and modules | `metamath-algebra` |
| Lattices, partial orders, and fixed-point theory | `metamath-order` |
| Finite graphs and combinatorial objects | `metamath-combinatorics` |

## 5. Linear Algebra and Calculus

**Linear algebra** is closer to infrastructure than calculus, but still introduces an entire suite of domain structures
(scalar fields, vector spaces/modules, linear maps, matrix representations, bases/dimension/rank, inner-product
norms, and the finite/infinite-dimensional split). The underlying mechanisms that make the linear-algebra package **thin** are provided in two layers:
the prelude supplies function and relation basics, while the set-theory/numbers domains supply finite indexed families and
finite fold; the prelude MUST NOT directly contain vector-space and matrix theory. Location:
`prelude → set/numbers → algebra → linear-algebra`.

**Calculus** is even less suitable: it is not a lightweight additional layer and would quickly introduce construction of the real numbers,
sequences and limits, completeness, topology, continuity, derivatives and integrals, and even metric spaces,
measure, and choice principles. Once linear algebra and calculus are included to “express learning,”
probability, measure, optimization, convex analysis, tensors, and numerical error soon follow—the prelude then
becomes a mathematics curriculum catalog rather than a foundation layer.

Learning-related capabilities are organized as a profile:

```text
metamath-learning-profile
├── metamath-linear-algebra
├── metamath-analysis
├── metamath-probability
├── metamath-optimization
└── metamath-finite-computation
```

There are also lightweight learning branches that do not require calculus (symbolic learning, finite-model learning,
and combinatorial search).

## 6. The Actual Foundation for Formal Methods in Software

Hoare logic, operational semantics, and separation logic do not require linear algebra or calculus. Their common
foundation consists of syntax trees and finite sequences; variables, environments, and states; functions, relations, and relation
composition; natural numbers and induction; partial functions/finite maps; disjoint union and local update; transition
systems and reachability relations; and (for separation logic) partial commutative monoids / separation algebras.

Division of responsibility: the prelude provides **mechanisms** such as relations, functions, and local updates; finite sequences,
natural numbers, and induction come from the set-theory/numbers domains (normal domain dependencies; see §1—“depends only on the
prelude” is not the goal); `metamath-program-foundation` defines **subject matter** such as states,
heaps, transition systems, and separation algebras. Dependencies remain shallow, and
program-logic-specific subject matter is not frozen into every mathematical package.

**Note**: this section only specifies “what program methods need and do not need”;
**how** program foundation and program profile enter the package structure
(as release packages or domains, which members they aggregate, and their dependency
shape with the set-theory/numbers domains) remains an open question (§12) and is not settled by this RFC.

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
remains in its domain package. The migration unit is the capability slice after dependency closure, not the top N
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

## 9. Initial Package Structure (Target Form)

```text
metamath-prelude
├── logic-base
├── equality-and-substitution
├── set-and-class-base
└── relation-and-function
    (equivalence-and-quotient to be added after adjudication;
     finite families/sequences and natural numbers/finite recursion have moved down to domain packages)

metamath-logic          metamath-set          metamath-discrete
metamath-number-theory  metamath-algebra      metamath-linear-algebra
metamath-order          metamath-analysis     metamath-probability
metamath-program-foundation
metamath-hoare-logic    metamath-separation-logic

metamath-program-profile
metamath-learning-profile
```

**A profile contains only stable aggregate dependencies and MUST NOT own underlying definitions.** It provides
an out-of-the-box experience without breaking theory boundaries.

How the program-methods branch (`program-foundation` / `hoare-logic` /
`separation-logic` / `program-profile`) enters remains an open question
(§12); it is shown here only for illustration.

## 10. Empirical Plan (MUST Be Completed Before Quantitatively Adjudicating the Boundary)

On the full-corpus graph in the partition repository (and subsequently expanded corpora):

1. **Delimit capability slices**: using the §4.1 table as a guide, manually identify each slice's seed-label
   set, then mechanically compute its rule closure (formation/equality/introduction-elimination/induction);
2. **Compute the five metrics**: frequency (direct + transitive indegree), domain-distribution entropy (normalized entropy across five regions),
   closure cost (size of the transitive prerequisite closure), axiom cost (occurrences of
   `ax-inf`/`ax-ac`/`ax-rep`, etc. in the closure), and interface stability (manual
   rating);
3. Produce a **ranked table of candidate slices** and cross-check it against the qualitative adjudications in §4.1: report for individual adjudication any
   qualitatively included item with weak metrics, or strongly scoring item that is qualitatively excluded;
4. Analyze the set difference between the current empirical 215-label prelude and the capability-slice boundary (which glue
   lemmas belong to a capability slice, and which are merely high-frequency theorems that should fall back to domain packages).

## 11. Relationship to Existing Work

- This RFC adjudicates the suspended question in **026 §2.1**: the prelude's role = construction
  toolkit (at capability-slice granularity), neither “constructors only” nor a “high-frequency foundation layer”;
  the `--prelude-floor` absorption-rate calibration mechanism is **retained but demoted** to a stress-test
  baseline tool and no longer determines prelude content.
- The terminology in **026 P7 / 000 §13** applies directly: the prelude is a special
  layer within a release package; a profile is a release package containing only aggregate dependencies; intermediate foundations such as `metamath-program-foundation`
  are ordinary release packages.
- The current five-region corpus's `prelude.core` (215 labels) remains a stress-test
  baseline until the §10 empirical work is complete and the capability-slice prelude is implemented.

## 12. Pending Adjudication

- **Whether and when the prelude should expand from minimal pre-logic to the candidate boundary**
  (set/class basics + relations and functions, §0)—three adjudications maintain the status quo;
  expansion requires a new adjudication trigger; until then, the §4.1 table is a candidate list, not an effective boundary;
- Whether equivalence relations and quotient constructions should be included in the first batch (“may include” in the table);
- Ownership of rational numbers between `metamath-discrete` and `metamath-algebra`;
- An operational definition for interface-stability ratings;
- Profile versioning policy (pinned member versions vs floating);
- The “vocabulary for defining algebraic structures” slice (the `df-struct` family) lies outside the current corpus's
  `[0, cstr)` range, so empirical evidence awaits corpus expansion; note that set.mm's extensible structures
  use ℕ-indexed slots (`df-ndx`/`df-slot`), so the slice will likely also depend on the
  numbers domain and be unable to enter the prelude, in which case an alternative structure-definition mechanism must be
  adjudicated at the same time;
- Whether `df-map` (function spaces) enters with the relation/function slice: inclusion adds the axiomatic commitments
  `ax-un`/`ax-pow` (closure 1,370→1,632 nodes and 18→20 axioms; see the
  pilot-report postscript);
- **How program foundation / program profile enters** (explicitly
  retained by the user as an open question): whether `metamath-program-foundation` is an independent
  release package or a domain within a release package, the shape of its dependencies on the set-theory/numbers domains, and
  which members and versioning policy `metamath-program-profile` aggregates—the relevant entries in §6/§9
  are illustrative sketches only and do not constitute an adjudication.

Adjudicated (second adjudication, 2026-07-19; formerly two §12 items): **natural numbers do not enter the
prelude**—both the ω system and arithmetic ℕ move down (§4.1 postscript); finite sequences/fold
take route B (move down to the numbers domain; no self-built thin ω-based version).

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
