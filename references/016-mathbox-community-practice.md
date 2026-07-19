# The Mathbox Institution: Community Practice, Discussions, and Empirics

**Status: non-normative.** This reference collects primary sources, community
discussion, and empirical measurements about set.mm's *mathbox* mechanism —
the longest-running production example of a frontier/core boundary in a
formal mathematics corpus. It complements
[Reference 014](014-module-partition-and-knowledge-classification.md)
(governance survey, esp. §5 on Wikipedia categories) and
[Reference 015](015-setmm-linearization-empirics.md) (F4: membrane
integrity). The mathbox is direct prior art for the maturity-gradient and
promotion machinery that the partition standard project will need.

## 1. What a Mathbox Is

A mathbox is "a user-contributed section that is maintained by its
contributor independently from the main part of set.mm". The definition and
rules live *inside the corpus itself*, as the comment of a dummy placeholder
theorem labeled `mathbox` (hard-coded into metamath-exe to mark where the
mathbox region starts for web-page generation). Source: the `mathbox`
statement in set.mm (Contributed by NM, 20-Feb-2007; revised by the Metamath
team, 9-Sep-2023); rendered at
<https://us.metamath.org/mpeuni/mathbox.html>.

Ownership is real but bounded. The guidelines state that "even though in a
sense your mathbox belongs to you, it is still part of the shared body of
knowledge", and others may make maintenance edits for synchronization, proof
shortening, typo fixes, and "moving your theorems to the main part of set.mm
when needed". Contributors wanting to preserve their exact text are told to
keep a local copy or a commit hash — i.e. the shared artifact is not an
archive of authorial intent.

## 2. The Rules (Primary Sources)

From the in-corpus guidelines (paraphrased; original wording at the source
above):

1. General style conventions apply inside mathboxes too, and are machine
   checked (`verify markup *`).
2. New definitions should use only nullary class constants where possible.
3. Every `$a`/`$p` must carry the comment that becomes its web description.
4. Mathbox content is on public display and should reflect site quality.
5. **Mathboxes must be independent from one another** (machine checked). If
   you need a theorem from another mathbox, "typically it is moved to the
   main part of set.mm".
6. Inactive contributors' mathboxes keep receiving maintenance edits; over
   time theorems "will be moved to main or removed in favor of similar
   replacements", but the community is "also willing to maintain mathboxes
   in place, as work by others from years ago may form the foundation of
   future work".
7. Theorems of importance (e.g. Metamath 100 theorems or their
   dependencies) are preferred to move out of mathboxes eventually.

From `CONTRIBUTING.md` (metamath/set.mm): changes to one's own mathbox go
through **cursory** review ("we generally just want to ensure that those
changes do not interfere with other parts of the database"), while still
passing all verifiers; mathboxes "should normally only be changed by the
owner" except for database-wide improvements. The repo has a general bias
toward "merge this now" with follow-up fixes for minor issues such as
suboptimal names.

From the MPE conventions page (<https://us.metamath.org/mpeuni/conventions.html>):
incomplete work "will generally only be accepted in a mathbox"; the `ALTV`
suffix for alternate variants "is reserved to statements in mathboxes and is
typically used temporarily, when it is not clear yet which variant to use";
on promotion to main, theorems are given their default general form (e.g.
dropping a `g` suffix).

Two further governance mechanisms interact with mathboxes:

- **Discouragement markers.** "(New usage is discouraged.)" and "(Proof
  modification is discouraged.)" tags freeze parts of the ABI; the repo
  tracks every usage of discouraged statements in a 20k-line `discouraged`
  file, so changes to the frozen surface are regression-controlled diffs.
- **Mass-rename protocol.** Historical notes (`mmnotes.txt`) document the
  procedure for library-wide renames: old names kept as `*OLD` for about a
  year, plus maintainer-run scripts that mechanically upgrade contributors'
  mathboxes ("If you have made changes to your mathbox that aren't in
  set.mm, I can update your mathbox for you").

## 3. Lifecycle and Promotion Practice

The observable lifecycle of mathbox content:

- **Entry.** Work in progress, experimental definitions, and alternate
  variants land in the contributor's mathbox first. The Metamath 100 page
  describes the norm: contributors keep work in mathboxes "to prevent
  interfering with others' work … and will later be moved to the main part
  of set.mm as appropriate."
- **Promotion is demand-driven (pull, not push).** The trigger in practice
  is that someone *else* needs the result: guideline 5 makes cross-mathbox
  use the canonical promotion trigger, and the mailing list confirms the
  routine ("Yes, we routinely move to main theorems from other people's
  mathbox when we need" — Thierry Arnoux, "Prime Ideals" thread, Jun 2026).
  `mmnotes.txt` records many such events ("bezout: imported from my
  mathbox"; "df-pc: imported prime count function from my mathbox").
- **Identity may change at the membrane.** Renaming is deliberately deferred
  to promotion time: "For structures that exist only in mathboxes, I won't
  do any renaming, but I may rename them if they are moved to the main
  set.mm" (mmnotes). Promotion can leave temporary duplicates behind,
  marked "Moved to <name> in main set.mm and may be deleted by mathbox
  owner" (observed by Ribeiro et al., see §5).
- **Exit without an owner.** Inactive contributors' boxes are absorbed
  gradually (moved to main, deduplicated, or deleted in favor of
  replacements) but may also persist for years as-is.

## 4. The 2017–18 Physical Modularization Episode

In Dec-2017/Jan-2018 Norman Megill shipped `write source … /split` in
metamath-exe 0.157-ALPHA: seamless reading/writing of a .mm database as
multiple included files, with three markup comments for "virtual includes"
(`$( Begin $[ file.mm $] $)`, `$( End $[ … $] $)`, `$( Skip $[ … $] $)`) so
the single-file and split forms round-trip losslessly. He published an
initial modularization with semantically named shards (`set-header.mm`,
`set-pred.mm`, `set-class.mm`, `set-main.mm`, `set-deprec.mm`,
`set-typeset.mm`, `set-hilsp.mm`, `set-mbox.mm`, per-user `set-mbox-*.mm`)
and demonstrated a mathbox being developed as a standalone file whose only
declared dependency is `$[ set-main.mm $]`. Source: "'write source…/split'
preliminary release", Metamath mailing list, Jan-2018
(<https://groups.google.com/g/metamath/c/4B85VKSg4j4>).

What happened since is instructive:

- The *collaboration format stayed monolithic*: "GitHub pull requests should
  be made with set.mm … written as single files."
- The *virtual module markup survives*: the current file still carries 262
  Begin/End/Skip markers, including one `Skip $[ set-main.mm $]` per user
  mathbox (54 of them) and topic shards such as `set-zf.mm`, `set-zfc.mm`,
  `set-top.mm`, `set-tarskigeom.mm`, `set-surreals.mm`, `set-struct.mm`.
- Reading: physical sharding without an import ABI did not change how the
  community collaborates; but the *declared* module structure — every
  mathbox depending on exactly `set-main` — is a one-import module ABI in
  embryo, and it is the piece that stuck. This supports the L2/L3
  separation of Reference 014: the durable artifact is the declared
  dependency surface, not the file layout.

## 5. Empirical Measurements

From [Reference 015](015-setmm-linearization-empirics.md) (current snapshot,
cross-validated against mono):

- **Scale**: 17,737 statements (35.2% of the corpus) across 51 user
  mathboxes.
- **Membrane integrity**: main→mathbox edges **0**; cross-mathbox edges 22
  (~0% of 540k mathbox-originated references). Guideline 5 holds exactly,
  enforced by `verify markup *`.

One-year flow measurements (2025-07-18 → 2026-07-18 snapshots, `$a`+`$p`):

| Flow | Count |
|------|------:|
| Promoted mathbox → main | **295** |
| Demoted main → mathbox | **0** |
| New statements entering via a mathbox | 1,951 (71% of 2,731 additions) |
| New statements entering main directly | 780 |
| Removals from mathboxes / from main | 137 / 746 (renames counted as remove+add) |

The promotion sources are concentrated (162 from Thierry Arnoux's box, 56
from Steven Nguyen's, 23 from Glauco Siliprandi's …), consistent with
demand-driven promotion out of active research areas. The direction of flow
is strictly one-way at the statement level, matching the edge-level result.

Independent academic measurement: Ribeiro, Barbosa & Gonzaga, *Graph based
analysis of mathematical knowledge structure on Metamath* (UNIFAL-MG,
2022; <https://www.unifal-mg.edu.br/dcc/wp-content/uploads/sites/221/2022/01/TCC_ReuelRRibeiro.pdf>)
build the set.mm dependency DAG (17,538 nodes at the time, mathboxes
excluded — then 8 axioms + 8,258 theorems), and find: total degree
lognormal; out-degree (usage) approximately power-law; the same usage hubs
we measure in 015 (`syl`, `eqid`, `syl2anc`, `adantr` …); source-layer
decomposition and max-flow analysis ranking predicate-calculus axioms as
the network's dominant flow source. Their remark that in-degree (proof
length) can be deliberately reduced by shortening one proof while
out-degree (usage) cannot be reduced locally is a clean statement of why
usage edges, not proof-length edges, are the churn-relevant quantity. Their
methodological choice to exclude mathboxes wholesale — because promotion
duplicates made main+mathbox double-counting hard — is itself evidence that
the frontier/core distinction is analytically load-bearing.

## 6. Lessons for the Partition Standard

1. **A one-way membrane is socially enforceable at 1/3-of-corpus scale**,
   given (a) a machine check (`verify markup`), (b) a crisp rule ("boxes
   are independent; needing someone's theorem means promoting it"), and
   (c) an owner per frontier namespace. (§2 rule 5, §5.)
2. **Promotion should be demand-driven.** The community's trigger — a
   second consumer appears — is a cheap, local, incontestable test, and it
   doubles as the *definingness* evidence of Reference 014 §5.2: content
   earns a place in the shared taxonomy when someone else depends on it.
3. **Identity changes at the membrane must be first-class.** set.mm defers
   renaming to promotion time and tolerates temporary duplicates with
   pointer comments. A standard should make this an explicit operation
   (promote = move + optional rename + shim/alias + deprecation window),
   not folklore. The `*OLD`-for-a-year protocol and the `discouraged`
   allowlist file are working precedents for deprecation windows and
   ABI-freeze bookkeeping. (§2, §3.)
4. **Review bandwidth is allocated by region, not uniformly**: cursory
   review inside a mathbox, full review at the membrane. A partition
   standard can generalize this: the stricter the layer (core vs frontier),
   the stronger the review and stability guarantees. (§2.)
5. **Physical sharding is not the hard part and not the point.** The 2017
   split feature worked technically and still did not change the
   collaboration model; what persisted is the declared dependency markup.
   Standardize the import ABI (L2) and treat file layout (L3) as derived.
   (§4.)
6. **The frontier is where growth happens**: 71% of new statements enter
   via mathboxes. Any partition plan that only models the consolidated
   core misses the region where most authorship — and most churn —
   actually occurs. (§5.)

## 7. Source Index

- In-corpus mathbox guidelines: `mathbox` statement in set.mm;
  <https://us.metamath.org/mpeuni/mathbox.html>
- Contribution/review policy: metamath/set.mm `CONTRIBUTING.md`
- Conventions (ALTV, incomplete work, promotion form):
  <https://us.metamath.org/mpeuni/conventions.html>
- Split-file release thread: Metamath mailing list, Jan-2018,
  <https://groups.google.com/g/metamath/c/4B85VKSg4j4>
- Promotion practice thread: "Prime Ideals", Metamath mailing list,
  Jun-2026, <https://groups.google.com/g/metamath>
- Maintenance history: metamath/set.mm `mmnotes.txt` (mass renames, mathbox
  sync scripts, promotion log entries)
- Deprecation bookkeeping: metamath/set.mm `discouraged` file
- Academic empirics: Ribeiro, Barbosa & Gonzaga 2022 (UNIFAL-MG TCC), incl.
  its reference Gonzaga, Barbosa & Xexéo, "The network structure of
  mathematical knowledge according to the Wikipedia, MathWorld, and DLMF
  online libraries", *Network Science* 2(3), 2014
- Local measurements: [Reference 015](015-setmm-linearization-empirics.md)
  and `scripts/setmm_linearization_empirics.py` (promotion-flow variant in
  the project thread)
