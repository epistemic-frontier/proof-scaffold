# Empirics of set.mm: Linearized Organization versus the Dependency DAG

**Status: non-normative.** This is the empirical companion to
[Reference 014](014-module-partition-and-knowledge-classification.md). It
measures, on the actual set.mm corpus, the structural questions raised while
discussing a partition standard: how knowledge boundaries and dependencies
manifest in a linearized (threaded) source file, and how unfinished the
"finished" part of the corpus really is. Numbers here are evidence for the
future normative project (partition evolution standard), not decisions.

## 0. Summary of Findings

| # | Question | Finding |
|---|----------|---------|
| F1 | Do authored section headers track dependency structure? | Far above chance (z = 14–63 against a random-cut null), but absolutely weak: only 7–11% of edges stay inside any authored block. Boundaries are classification artifacts, not edge-density communities. |
| F2 | Is the section-level quotient DAG chain-like? | No. Only 28.3% of section pairs are dependency-comparable. The linear file order hard-codes ~592k pairwise orderings (71.7%) that the DAG does not force. |
| F3 | Are dependencies local in the linear order? | No. Median edge span is ~20k statements (~40% of the library). The graph is hub-dominated: 50 glue lemmas absorb 22% of all logical proof references; the top 500 absorb 54%. Topic locality exists but only underneath the hub layer (within-section fraction rises from 9% to 31.5% after removing the top 2000 hubs). |
| F4 | Does the mathbox membrane hold? | Perfectly. 35% of the corpus (17,737 statements, 51 user mathboxes) sits in the frontier region; main→mathbox edges = 0; cross-mathbox edges = 22 (~0). One-way maturity membranes are enforceable at scale. |
| F5 | How unfinished is the settled corpus? | Per year: +5.8% theorems added, −1.9% removed, 3.7% of surviving proofs rewired, ~0.9% of statements genuinely relocated to another section (plus 0.3% via section renames/merges). A static optimal layout decays measurably every year. |

## 1. Method

- **Corpus**: the working-tree `set.mm` (50,435 `$a`/`$p` statements, 47,437
  theorems, 870,924 lines). Old snapshot for F5: upstream commit
  `65860bc` (2025-07-18), exactly one year before the current snapshot,
  fetched from `github.com/metamath/set.mm`.
- **Edges**: direct proof references, extracted from compressed-proof label
  lists (1,502,518 edges). "Logical" edges restrict targets to statements
  with typecode `|-` (901,311 edges; the rest target syntax constructors
  such as `wcel`, `cfv`).
- **Boundaries**: the authored banner headers. In the current file each
  top-level block (`#*#*`) is a part (163 blocks, including one per user
  mathbox), `=-=-` a section (1,286 cumulative blocks), `-.-.` a subsection
  (1,894 cumulative blocks). Membership is by line ranges.
- **Tooling**: `scripts/setmm_linearization_empirics.py` at the workspace
  root (standard library only); machine-readable output at
  `build_out/setmm_empirics.json`. All numbers below are reproducible from
  the script with seed 42.
- **Cross-validation against mono**: the `mono` Source Plane service (the
  metamath-rs-based indexer, `mono/docs/mono.md`) serves the same file
  (source hash `131fe655…` matches) and exposes the global dependency graph
  via `GET /v1/deps/:label` for any label in the library. On 300 randomly
  sampled theorems, this document's edge extraction agrees *exactly* with
  mono's `direct_deps` restricted to assertion targets: the only difference
  is that mono additionally lists `Floating` (`$f` variable declaration)
  hypotheses, which this study deliberately excludes; there were zero edges
  present here and absent in mono.
- **Caveats**: edges omit mandatory `$f`/`$e` frame hypotheses of the citing
  theorem itself (they are implicit in compressed proofs); the one-year churn
  window is a single sample; label renames are counted as remove+add.

## 2. F1 — Authored boundaries are real but weak communities

Within-block edge fraction of the authored interval partition versus a null
model of random contiguous partitions with the same number of blocks
(100 trials):

| Level | Blocks | Authored | Null mean ± std | z |
|-------|-------:|---------:|----------------:|----:|
| Part | 163 | 11.19% | 8.49% ± 0.19% | 14.5 |
| Section | 1,286 | 7.23% | 4.55% ± 0.06% | 45.6 |
| Subsection | 1,894 | 6.89% | 3.94% ± 0.05% | 62.7 |

Two readings, both needed. The headers carry genuine structural signal —
they beat chance by tens of standard deviations, so the community-label
correlation tests of Reference 014 §1.4 are applicable, not vacuous. But in
absolute terms roughly 93% of edges cross section boundaries no matter what.
Optimizing an interval partition for cut minimization therefore operates on
a very weak signal, and its optimum is driven by where the *hub* references
fall (see F3), not by topic boundaries. This is the structural explanation
for the observed failure mode of the current cut-optimal DP tool
(`proof_partition_tool.py`): its boundaries are globally optimal for an
objective that topic structure barely influences, which is why its
suggestions read as arbitrary from a naming and classification standpoint.

## 3. F2 — The linearization over-specifies order by a factor of ~3.5

Taking the 1,286 authored sections as modules, the quotient graph has 50,160
distinct directed section pairs (6.1% of all ordered pairs). Under transitive
closure only **28.3%** of section pairs are comparable — for the remaining
71.7% (~592k pairs), the file's total order is an arbitrary choice that no
dependency forces. The transitive reduction has 1,724 edges against a chain
baseline of 1,285, i.e. the true module structure is a branching DAG about
34% "wider" than any chain can express.

This quantifies the earlier structural argument: an interval partition of a
topological order forces the module quotient to be a chain ("later block may
use everything earlier"), and in set.mm that chain encodes roughly 592k
pairwise ordering decisions with zero dependency content. A semantic source
surface with explicit imports can simply drop them; the .mm linearization
should be treated as one derived chain-extension of the real quotient DAG
(Reference 014 §0, layer L3).

## 4. F3 — Hub-dominated, not locality-dominated

Distribution of edge spans in statement-index distance: median 20,083,
p90 41,142 (of 50,435 statements). Dependencies are not local in the linear
order in any useful sense.

The cause is extreme reference concentration. For logical (`|-`) edges:

| Hubs removed (most-cited first) | Share of edges absorbed by hubs | Within-section fraction of remaining edges |
|---:|---:|---:|
| 0 | — | 8.99% |
| 50 | 22.1% | 11.47% |
| 500 | 53.6% | 18.76% |
| 2,000 | 74.5% | 31.51% |

The top hubs are proof plumbing, not topic knowledge: `syl` (15,043 direct
citations), `eqid`, `adantr`, `a1i`, `syl2anc`, `ax-mp`… Topic locality
exists — the residual within-section fraction more than triples once hubs
are removed — but it is visible only after the ubiquitous inference layer is
factored out.

Architectural implication for the standard: the corpus has a two-regime
structure, a small ubiquitous **core/prelude layer** (glue lemmas and syntax
constructors, on the order of 10²–10³ statements) plus moderately-local
topical modules. A partition objective that treats a `syl` citation and a
topical citation as the same kind of edge will always be dominated by hub
placement. The core layer should be explicitly designated, globally visible
(re-exported everywhere, like a language prelude), and exempt from cut
accounting; boundary quality metrics should be computed on hub-filtered
edges. This mirrors mathlib's foundational `Init`/tactic strata
(Reference 014 §2.1) and explains why import-cycle discipline alone is not
a sufficient boundary criterion.

## 5. F4 — The mathbox membrane works: governance evidence

- 17,737 statements (35.2% of the corpus) live in 51 user mathboxes.
- Edges mathbox→main: 540,073. Edges main→mathbox: **0**. Cross-mathbox: 22.
- The membrane is a social policy (plus review tooling), yet it holds
  exactly, at a scale of a third of the library, across decades.

This is an existence proof for the maturity-gradient design discussed for
the partition standard: a one-way dependency membrane between a frontier
region (relaxed layout rules, per-contributor namespaces) and a consolidated
core (strict boundaries) is enforceable in practice. Promotion out of a
mathbox is exactly the "diffusion from holding category to refined
category" workflow of Wikipedia governance (Reference 014 §5.5).

## 6. F5 — The settled corpus rewires ~4% per year

One-year window (2025-07-18 → 2026-07-18):

| Quantity | Value |
|----------|------:|
| Theorems (old → new) | 45,668 → 47,437 |
| Added | 2,640 (5.8% of old) |
| Removed (incl. renames) | 871 (1.9%) |
| Surviving theorems whose proof changed | 1,664 (**3.71%**) |
| Statements moved to a different section | 547 (1.15%), of which 413 (0.92%) genuine relocations and 134 via section renames/merges |

The relocation events are themselves instructive: the largest genuine moves
are coarse holding sections diffusing into refined ones ("Algebra" →
"Totally ordered monoids and groups" / "Two-sided ideals and quotient
rings"; "Real subtraction" → "Independence of ax-mulcom"), i.e. the corpus
already evolves by category diffusion, uncoordinated and without identity
protection.

Consequence: the objective function of any static optimal partition (its
edge set) drifts by roughly 4% per year *within the already-proved corpus*,
before counting growth. Unfinishedness is not confined to the frontier. A
partition standard must therefore specify the **evolution operations and
invariants** — create/split/diffuse/promote, stable module identity, rename
shims, re-evaluation cadence — rather than a layout. This confirms, with
set.mm's own history, the conclusion of Reference 014 §1.3/§3.3 that
stability under change is a governance property, not an optimization
property.

## 7. Inputs Carried Forward to the Normative Project

1. **Boundaries are declared, not discovered.** Edge-density objectives
   cannot recover semantic boundaries in this graph (F1, F3); classification
   (L1) must lead and edge metrics act as *validators* (e.g. hub-filtered
   within-fraction, quotient acyclicity), not as generators.
2. **Designate an explicit prelude/core layer** exempt from boundary
   accounting; size it empirically from citation concentration (F3).
3. **The module graph is a DAG, not a chain.** The semantic surface should
   record only true import edges; any .mm emission is one chain-extension
   chosen for rendering, and inter-module file order carries no normative
   content (F2). Intra-module order remains authored narrative metadata —
   unresolved, see the open question in the project discussion.
4. **Adopt a one-way maturity membrane** (frontier → core), proven
   enforceable by 25 years of mathbox practice (F4).
5. **Standardize operations, not layouts.** Budget for ~4%/yr edge rewiring
   and ~1%/yr relocation inside the settled corpus (F5); every operation
   needs identity stability and migration support (Reference 014 §4.3, §5.4).

## 8. Reproduction

```sh
python3 scripts/setmm_linearization_empirics.py set.mm/set.mm \
    --old-file /path/to/set.mm@65860bc --json build_out/setmm_empirics.json
```

The hub-decomposition and relocation-classification analyses are one-off
variants of the same parser; their exact invocations are recorded in the
project thread and are straightforward to re-derive from the script's
`build_model` API.

For future tooling (including the partition standard project), the
**canonical global dependency graph source is mono's DepIndex**
(`GET /v1/deps/:label`, `GET /v1/statement/:label?include=deps`,
`GET /v1/chapters`), which is backed by a real Metamath parser and covers
the whole library regardless of the loaded migration plan. The regex
extractor in this study is a dependency-free reproduction path, validated
against mono as described in §1; new analyses should prefer mono and fall
back to the script only when no service is available.
