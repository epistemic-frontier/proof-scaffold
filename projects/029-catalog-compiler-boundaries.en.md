# Project 029: Catalog Compiler Boundaries

> Status: normative toolchain-boundary adjudication (2026-07-21).
>
> Decision: the canonical repository name is **`catalog-compiler`**, without
> `setmm` in the repository name. Its compiler core has zero hard binding to
> any source format, foundation, theory family, public projection, or backend.
> Those dimensions enter only as versioned data parameters or injected,
> versioned capability protocols. Set.mm is one adapter, not the definition of
> the compiler.
>
> Migration fact: GitHub repository ID `1299890868` was renamed on 2026-07-21
> from `epistemic-frontier/partition` to
> `epistemic-frontier/catalog-compiler`. The old name currently redirects to
> the canonical repository; the rename did not rewrite Git history.
>
> Normative basis: [Reference 017](../references/017-ontology-first-knowledge-organization.md),
> [Terminology Standard 000](../references/000-terminology.en.md),
> [Project 025](025-semantic-source-surface.en.md),
> [Project 026](026-package-evolution-standard.en.md),
> [Project 027](027-prelude-boundary-rfc.en.md), and
> [Project 028](028-top-level-knowledge-release-units.en.md).
>
> In this document, “MUST,” “MUST NOT,” and “SHOULD” have normative meanings.

---

## 0. Decision

The repository is named `catalog-compiler`. The name denotes an engine that
compiles governed knowledge catalogs; it does not name one source corpus, one
foundation, or one output ecosystem.

The compiler core MUST NOT contain source-, foundation-, theory-, projection-,
or backend-specific policy. In particular, it MUST NOT hard-code:

- Metamath or Set.mm syntax, labels, source regions, or assertion kinds;
- a classical, constructive, set-theoretic, type-theoretic, or other
  foundation;
- Project 028's sixteen Set.mm release units or any other ontology;
- Python module paths, package names, release topology, or publication policy;
- the historical Transpiler implementation or any concrete emitter.

Every such choice MUST arrive through one of two explicit mechanisms:

1. **versioned data parameters**, whose schemas, identities, and digests are
   recorded in the compilation result; or
2. **injected capability protocols**, whose implementation identity, protocol
   version, declared capabilities, and configuration digest are recorded in
   the compilation result.

Missing versions or capabilities cause rejection. The core MUST NOT guess a
default source, foundation, theory, projection, or backend.

---

## 1. Authority and Data Flow

The generic flow is:

```text
source bytes + source adapter
             |
             v
      versioned source inventory
             |
catalog + foundation data + theory graph + projection data
             |
             v
        catalog-compiler core
          |             |
          |             `-- injected analysis passes
          v
compiled catalog / release locks / analysis results
             |
             v
       injected backend capability
             |
             v
generated source, packages, verification artifacts, or other projections
```

The compiler computes and validates projections; it does not acquire the
authority to invent their mathematical content.

- Source adapters own faithful source decoding and snapshot binding.
- Catalog data owns accepted identities, ontology, placement, lifecycle, and
  projection decisions.
- Foundation and theory data own the formal assumptions and relationships
  under which declarations are interpreted.
- Analysis passes derive evidence from the same compilation state.
- Backend capabilities realize compiled outputs without changing catalog or
  theory meaning.

Normative data repositories remain separate from the compiler repository. A
compiler implementation is not itself an adjudication authority.

---

## 2. Core Boundary and Capability Injection

The core MAY provide generic facilities such as schema dispatch, canonical
encoding, digest verification, graph traversal, constraint solving,
deterministic scheduling, diagnostics, and provenance recording. These
facilities MUST be parameterized by data or protocols rather than recognize a
specific corpus or output by name.

An injected capability protocol MUST declare at least:

- a stable capability identifier and protocol version;
- accepted input contract versions and emitted output contract versions;
- deterministic configuration and its digest;
- required companion capabilities;
- failure and diagnostic behavior;
- whether it is observational, validating, transforming, or emitting.

The core MUST validate compatibility before execution. Capability discovery
MUST NOT become ambient plugin loading: the complete selected capability set is
an explicit, ordered compilation input and appears in the result provenance.

Foundation, theory, and projection specifications are data even when helper
libraries provide typed constructors for them. Convenience APIs MUST NOT turn
those values into process-global policy.

---

## 3. Set.mm Is an Adapter

Set.mm support is implemented by a versioned adapter. The adapter MAY know:

- Metamath scanning, scopes, frames, compressed proofs, and replay semantics;
- the exact Set.mm snapshot and included/excluded source regions;
- Set.mm-specific section extraction and source-inventory encodings;
- the mapping from Set.mm declarations to stable catalog identities.

Those facts MUST NOT leak into generic core branches or default values. The
Set.mm adapter produces generic compiler inputs and, where necessary,
versioned Set.mm-specific companion records.

Project 028's sixteen mathematical release units, Project 027's Prelude
boundary, and the Set.mm V1 scope are adapter/catalog data. They are not core
constants. The existing `setmm-catalog-compiler-v1` contract remains a
Set.mm-specific interchange contract; its name does not rename or specialize
the `catalog-compiler` repository or core.

Mono may remain the producer and validator of Set.mm source facts. The generic
core depends on the source-adapter contract, not on Mono as a concrete process
or Rust crate.

---

## 4. Theory Graph and Reverse-Mathematics Analysis

A compilation MAY carry a versioned theory graph whose nodes identify
foundations or theories and whose typed edges record relationships such as
extension, interpretation, translation, conservative projection, or selected
implementation support. The exact edge vocabulary belongs to the graph's data
contract, not to hard-coded core enums unless supplied by that contract.

Reverse-mathematics support MUST be an analysis pass over the theory graph and
the same canonical compilation state. It MUST NOT require a second compiler, a
forked catalog, or a source-specific code path. One compilation may therefore:

1. validate declarations and their selected implementations;
2. construct the theory graph for the pinned inputs;
3. run reverse-mathematics or proof-strength analyses over that graph; and
4. emit both the compiled projection and provenance-bound analysis results.

An analysis result is derived evidence, not a silent ownership or foundation
mutation. It MUST identify the input digests, theory-graph version, analysis
capability/version, assumptions, and any unresolved or non-comparable cases.
Analysis failure MUST NOT be disguised as a negative mathematical result.

---

## 5. Transpiler Becomes a Backend

The current Transpiler implementation is migrated into `catalog-compiler` as
an injected backend capability. Its existing repository history is part of the
provenance of that backend and MUST be preserved in full.

Migration MUST preserve every original commit SHA. Therefore migration MUST
NOT use:

- squash merges;
- rebasing or cherry-picking as a substitute for importing the original
  history;
- `git filter-repo`, `filter-branch`, or another history-rewriting relocation;
- a fresh snapshot commit that discards ancestry.

An unrelated-history merge or another non-rewriting Git construction MAY place
the original history in the destination while adding the backend integration
in later commits. Moving files after the history becomes reachable is a new,
ordinary commit; it does not authorize rewriting earlier objects.

The backend consumes explicit compiled inputs through its capability protocol.
It MUST NOT reach back into catalog internals, infer public ownership from proof
order, or cause backend defaults to become compiler-core policy. Existing
`mm-transpiler` distribution, import, CLI, manifest, and policy names remain
compatibility contracts until separately versioned migrations replace them.

---

## 6. Partition Artifacts Are a Historical Compatibility Layer

The former partition repository established useful empirical evidence,
proof-graph formats, plan-v3 stress tests, generators, reports, and APIs. These
artifacts remain reproducible history and compatibility inputs. They do not
name the new compiler's normative abstraction.

Within `catalog-compiler`:

- historical reports and generated artifacts retain their original names;
- `proof-partition-*`, `mm-partition-domain-v1`, `mm_partition`, and the
  `mm-partition` CLI are not mechanically renamed;
- compatibility commands MAY remain while downstream consumers migrate;
- partition metrics MAY serve analysis passes or diagnostics;
- partition output MUST NOT determine public mathematical ownership or become
  an implicit core default.

Any eventual removal of a compatibility surface requires an explicit consumer
inventory, replacement path, deprecation interval, and reproducibility plan.

---

## 7. Names and Repository Mapping

The frozen repository/component mapping is:

| Name | Role |
| --- | --- |
| `catalog-compiler` | Generic compiler repository and component; no source, foundation, theory, projection, or backend hard binding |
| `setmm-catalog` | Normative Set.mm catalog data and schemas |
| `setmm-review` | Non-normative Set.mm review campaigns and adjudication workspace |
| Mono | Set.mm source-plane implementation and source-adapter producer/validator |
| Transpiler backend | Full-history backend capability migrated into `catalog-compiler` |
| partition compatibility layer | Historical research, artifacts, schemas, and temporary downstream compatibility APIs |

Repository names, software distribution names, Python import roots, CLI entry
points, and machine contract identifiers are distinct. Renaming the repository
does not by itself rename any of the other four. Documentation MUST state their
mapping explicitly during migration.

GitHub repository ID `1299890868` is now canonically named
`epistemic-frontier/catalog-compiler`. The former
`epistemic-frontier/partition` name is a redirect, not the canonical URL.
Active documentation MUST use the canonical URL. Historical evidence links
SHOULD name the canonical repository and pin the original commit SHA rather
than rely indefinitely on the redirect.

---

## 8. Archive-Last Migration Gates

The old Transpiler repository MUST be archived last. It remains available and
unarchived until every gate below passes:

1. **Ref inventory:** record all branches, tags, default-branch HEAD, and their
   SHAs from the old repository.
2. **Object preservation:** every inventoried original commit SHA is reachable
   in `catalog-compiler`; full object-integrity checks pass.
3. **Tree mapping:** the old default-branch source tree has an explicit,
   reviewable mapping to the imported backend tree, with no unexplained file
   loss.
4. **Build and test equivalence:** the imported backend passes its complete
   original test, lint, type, and build gates in the destination.
5. **Behavioral equivalence:** pinned fixtures produce equivalent generated
   source, manifests, digests, and verification outcomes, except for explicitly
   adjudicated path/provenance changes.
6. **Capability integration:** the generic core invokes the backend only
   through the declared protocol, and negative tests prove that missing or
   incompatible capabilities are rejected.
7. **Operational cutover:** CI, issue/PR references, release instructions,
   security ownership, and canonical documentation point to the destination;
   a rollback route remains documented.
8. **Independent audit:** a reviewer confirms the ref manifest, reachability,
   gates, and destination URLs.

Only after G1–G8 pass may the old repository be made read-only and archived.
Archiving is never a prerequisite for migration and MUST NOT be used to force
cutover. The archived repository's notice points to the destination and states
the preserved-history boundary.

The completed partition-to-`catalog-compiler` rename is not archival. The same
archive-last principle applies if its historical compatibility surfaces are
later retired: compatibility changes occur before retirement, and historical
evidence remains reachable by original commit SHA.

---

## 9. Acceptance Gates

Project 029 is satisfied only when:

| Gate | Requirement |
| --- | --- |
| C1 | Core tests prove there is no Set.mm/source, foundation, theory, projection, or backend default in generic compilation |
| C2 | Every selected data contract and capability/version is present in deterministic provenance |
| C3 | The Set.mm vertical slice runs solely through the adapter boundary and reproduces the frozen inventory/catalog lock contracts |
| C4 | One compilation constructs a theory graph and runs a provenance-bound reverse-mathematics analysis pass |
| C5 | The Transpiler history passes all archive-last gates with every original commit SHA preserved |
| C6 | The imported Transpiler backend is behaviorally equivalent on pinned fixtures and isolated behind its capability protocol |
| C7 | Legacy partition artifacts remain reproducible but cannot determine public ownership or generic defaults |
| C8 | Active bilingual documentation agrees on repository, component, contract, compatibility, and archive status |

Passing a feature test while losing Git history fails C5. Preserving Git
objects while bypassing the backend protocol fails C6. A Set.mm-only core that
can be wrapped in a nominal generic API fails C1.

---

## 10. Implementation Sequence

1. Freeze this terminology and boundary in Project 029 and Terminology 000.
2. Inventory active consumers of the partition and Transpiler repositories,
   distributions, imports, CLIs, schemas, and URLs.
3. Record and verify the completed non-rewriting GitHub rename: repository ID
   `1299890868` is `epistemic-frontier/catalog-compiler`, the old name
   redirects, and partition compatibility surfaces remain available.
4. Introduce generic versioned inputs and capability protocols, then move
   Set.mm-specific behavior behind an adapter.
5. Add theory-graph construction and an analysis-pass interface; demonstrate a
   reverse-mathematics pass in the same compilation.
6. Inventory and import the complete Transpiler Git history without squash,
   rebase, filtering, or SHA replacement.
7. Integrate Transpiler as a backend and pass equivalence, capability, and
   provenance gates.
8. Cut active documentation and CI over to the destination while the old
   repository remains unarchived.
9. Obtain an independent archive-last audit.
10. Archive the old Transpiler repository only after all gates pass.

Each step must leave a runnable, recoverable state. No later step retroactively
licenses history rewriting in an earlier step.

---

## 11. Relationship to Projects 025–028

- Project 025 remains authoritative for the generated semantic source surface,
  lazy elaboration, frame equivalence, and backend emission behavior. Project
  029 supersedes any reading in which one partition result is the authority for
  public module ownership, and relocates Transpiler implementation behind a
  backend protocol.
- Project 026 remains authoritative for definingness, stable migrations,
  dependency completeness, reproducibility, and its recorded partition
  experiments. Its former repository handoff is historical.
- Project 027 remains authoritative for the Prelude content boundary and
  capability-slice migration principle. The boundary is Set.mm
  foundation/catalog data, not a compiler-core constant.
- Project 028 remains authoritative for the sixteen Set.mm mathematical
  release units and their one-root/one-release topology. That topology is a
  versioned Set.mm projection input, not a generic core allowlist.

Project 029 changes tool boundaries and migration mechanics. It does not
reopen the mathematical adjudications in Projects 027–028.

---

## 12. Non-Goals and Deferred Decisions

This project does not:

- choose a universal ontology or foundation;
- claim that every source system can already supply every optional capability;
- freeze a universal theory-graph edge vocabulary beyond versioned contracts;
- define the mathematical conclusions of a reverse-mathematics analysis;
- rename frozen historical schemas, CLIs, packages, or generated artifacts;
- authorize deletion of either old repository;
- adjudicate mathbox ownership, maturity, or promotion.

Future protocol versions may add capabilities, but they may not weaken the
zero-hard-binding rule, provenance requirements, SHA-preserving migration, or
archive-last gates.

---

## 13. Provider Layout V1 Boundary (2026-07-21)

The first post-migration semantic-package contract is
`provider-layout-v1`. Its normative schema and validator live in
`catalog-compiler`, but neither `CompilerSpec` nor the generic core imports or
constructs it. A semantic-package backend receives it as an explicit,
digest-bound parameter.

The contract normalizes five distinct facts:

1. the versioned compiled subject contract and digest;
2. public surfaces, each with an opaque public owner and target artifact;
3. physical provider shards, each with an opaque provider, target artifact,
   and exact direct shard requirements;
4. selected implementation identities, implementation digests, and typed
   target entry points;
5. exact declaration bindings to one public surface and one selected
   implementation.

All owner, provider, artifact, declaration, implementation, shard, and entry
point identifiers are opaque to the generic contract. A target-specific entry
point is interpreted only by an explicitly selected, versioned companion
validator. The base schema contains no source labels, assertion kinds, source
ordinals, Python paths, distribution names, fixed release registry, Prelude
default, or proof-format vocabulary.

Schema validity alone is insufficient. A consumer MUST inject an authority
context that supplies the exact subject digest, public surfaces, selected
implementations and digests, declaration bindings, provider/artifact authority,
and direct implementation dependency relation. Endpoint validators are a
separate explicit mapping whose keys must exactly equal the contracts used by
the layout. The layout assigns implementations to physical shards. Validation
rejects both missing and surplus shard edges after collapsing the authority-
supplied implementation graph. Shard, provider-quotient, and target-artifact-
quotient graphs must all be acyclic.

The authority facts have their own versioned contract and canonical content
digest, separate from the authority producer's capability ID, protocol version,
and configuration digest. Endpoint validators likewise expose versioned,
configuration-bound descriptors. A successful result computes a validation-
provenance digest over the layout, authority descriptor, and exact endpoint
descriptor set; it is a cache/provenance key, not Manifest V3 or a verification
certificate.

`provider-layout-v1` does not choose a provider, optimize shard boundaries, or
infer public ownership from proof order. A cycle requires an adjudicated shard
merge or stage, or a real interface extraction; it never licenses moving a
public declaration to another owner. V1 validates a supplied shard projection;
it does not attest that a merge or staging choice was adjudicated. A production
producer must therefore expose the shard-projection capability and
configuration digest explicitly in provenance.

For Set.mm V1, the compiled lock's `provider` remains a release-level
selection and `module` remains the public facade. Physical shards, generated
paths, and implementation entry points do not enter
`knowledge-release-lock-v1` or declaration-placement attestations. A later
Set.mm authority companion joins declaration UUIDs to a snapshot-matched Mono
graph and exact proof/replay facts, then supplies the physical decisions as
explicit data.

No production Set.mm provider layout is frozen by this section. The current
catalog is a partial four-declaration governance sample, its proofs require
declarations outside that partial lock, and the available corpus graph is not
snapshot-matched to the catalog pin. Inventing shard IDs or treating the
historical public-module plan as implementation placement is therefore
forbidden.

Acceptance gates for this stage are:

| Gate | Requirement |
| --- | --- |
| PL1 | The generic schema and validator contain no Set.mm, fixed release, Python, foundation, or backend defaults. |
| PL2 | RFC 8785 digest, canonical ordering, uniqueness, and every reference are checked fail-closed. |
| PL3 | Authority joins require exact declaration, owner, selected provider/implementation, artifact, entrypoint, and implementation-digest agreement; authority facts are independently content-addressed. |
| PL4 | Declared shard requirements exactly equal the direct cross-shard implementation quotient; missing and surplus edges fail. |
| PL5 | Shard, provider, and target-artifact quotients are acyclic. |
| PL6 | Unknown or unversioned endpoint contracts cannot use ambient discovery; exact authority and endpoint capability descriptors are bound in validation provenance. |
| PL7 | The Set.mm catalog, placement, and knowledge-release lock schemas remain unchanged; their physical-layout boundary is documented explicitly. |
| PL8 | Tests use a synthetic non-Set.mm authority context; no fabricated production shard appears in normative data. |

Generated-tree ownership and atomic publication are now frozen by the adjacent
Generated Tree V1 contract described below. Manifest V3, trust/foundation
closure, and the independent verification receipt remain later contracts. A
valid provider layout is necessary but not sufficient for a publishable
semantic package.

---

## 14. Generated Tree V1 Publication Boundary (2026-07-22)

`catalog-compiler` now owns a source-neutral `generated-tree-v1` content and
record contract, an explicit generated-output policy, and a selected POSIX
publisher that converges through terminal `COMPLETE`. This freezes the
publication boundary without moving Set.mm or proof-scaffold policy into the
generic compiler core.

The deterministic tree records only the authorized logical owned root, exact
portable file inventory, byte facts, content digest, and generation context.
Host roots, inode/device facts, locks, staging names, journals, and publication
receipts remain runtime-only and live outside the generated tree. A deployment
selects the target/control roots, requested-content provider, atomic adapter,
durability behavior, and pinned receipt schema explicitly.

The retained-lock session installs a durable journal before staging, validates
frozen bytes independently, uses a genuine exclusive install or atomic
directory exchange, and reaches the `DURABLE` visibility/durability boundary.
Its argument-free completion operation internally constructs and stores the
publication receipt, independently reopens it, rechecks exact post topology,
records `CLEANED` before transaction-owned deletion, proves durable staging
absence, and then records `COMPLETE`. The terminal head remains until a
different transaction actually installs its origin; permanent receipts prevent
transaction-ID reuse.

This changes proof-scaffold's integration obligation, not its authority. A
future semantic-package backend may supply only frozen generated bytes and
explicit capability descriptors to the selected publisher. Existing direct
write, `rmtree`, authoring-project, and legacy transpiler paths are not wrappers
for this capability and must not be described as atomic publication.

`COMPLETE` is an operational Generated Tree V1 result. It does not validate a
Manifest V3, prove declaration coverage, establish trust/foundation closure,
compare frames, verify proofs, or constitute an independent verification
receipt. It also does not make the current partial Set.mm catalog a production
release: a complete publishable lock, snapshot-matched dependency graph,
adjudicated provider layout, exact Prelude/provider locks, and independent
verification are still required.

Acceptance gates for this boundary are:

| Gate | Requirement |
| --- | --- |
| GTB1 | The generic tree, policy, journal, receipt, and publisher contracts contain no Set.mm, Python, Prelude, proof-format, or fixed generated-root default. |
| GTB2 | The publisher may replace only the explicitly authorized owned root; unknown topology, links, extra files, receipt drift, and ambiguous recovery preserve all data. |
| GTB3 | `DURABLE` remains the atomic visibility/durability boundary; only receipt-bound exact cleanup and absence proof may advance to `COMPLETE`. |
| GTB4 | Receipt paths and bytes, cleanup authority, control descriptors, and durability adapters are not caller-supplied session parameters. |
| GTB5 | Two clean synthetic emissions are byte-identical, and a separate process can recompute the tree solely from frozen bytes. |
| GTB6 | `COMPLETE` remains explicitly distinct from Manifest V3 and the independent semantic verification receipt. |
