# Project 018: BuilderV2 Migration (Plan & Checklist)
 
## Status
Draft

BuilderV2 的主体方向已进入实现阶段；package role、foundation scope 与
prelude/logic 边界问题由后续
[Project 020](file:///Users/mingli/MetaMath/proof-scaffold/projects/020-foundation-scope-refactor.md)
继续推进。
 
## Context
This project defines a concrete migration plan to land **BuilderV2** as specified by:
 
- Frozen contract: [references/009_builder-v2.md](file:///Users/mingli/MetaMath/proof-scaffold/references/009_builder-v2.md)
- Migration rationale & friction points: [projects/017-builder_v2.md](file:///Users/mingli/MetaMath/proof-scaffold/projects/017-builder_v2.md)
- Linker/TCB/Determinism constraints: [WHITEPAPER.zh-CN.md](file:///Users/mingli/MetaMath/proof-scaffold/WHITEPAPER.zh-CN.md), [references/002_link-model_v4.md](file:///Users/mingli/MetaMath/proof-scaffold/references/002_link-model_v4.md)
 
This plan is written to be implementable in small, verifiable slices, while keeping the current toolchain working (pytest stays green at every step).
 
## Goals (What we want)
1. Make `build(ctx)` the primary entrypoint for packages, with a migration path from legacy modes.
2. Enforce **SymbolId-only** at the build boundary (no string token DSL for proofs/expr in the V2 path).
3. Ensure IR and emitted `.mm` are **ASCII canonical**, while allowing Unicode authoring via **NameResolver/Lexicon**.
4. Remove authoring/tooling code that relies on builder private fields (e.g. `mm._constants/_variables/_exports`).
5. Add machine-readable mapping artifact: `*.names.json`.
 
## Non-Goals (What we explicitly do NOT do in v1)
- Proof search / automation.
- Changing verifier semantics / expanding TCB.
- Replacing the Linker pipeline stages (Stage 1–8 remain the authority for relocation, scope planning, diagnostics).
- Immediately deleting Script Mode (`skfd.mm/skfd.deps`) or legacy `build(mm, **deps)`; these are deprecated later.
 
## Frozen Contract (Invariants)
From [references/009_builder-v2.md](file:///Users/mingli/MetaMath/proof-scaffold/references/009_builder-v2.md):
 
- **I1 Single entrypoint**: packages expose `build(ctx)`.
- **I2 Single truth layer**: cross-package interaction uses `SymbolId` only.
- **I3 ASCII canonical**: IR and `.mm` output remain ASCII-only.
- **I4 Unicode only in authoring**: Unicode enters via `NameResolver/Lexicon` and must produce machine-readable mapping.
- **I5 Auto-$f by default**: authors don’t write repetitive `$v/$f`.
- **I6 v1 is additive**: do not break the v1 interface once shipped.
 
## Current State (What exists today)
Key “dirty” coupling points (to be removed in V2 path):
 
- Driver injects deps via kwargs with `- -> _`, and builds exports by reading builder private state:
  - [runner.py](file:///Users/mingli/MetaMath/proof-scaffold/src/skfd/driver/runner.py)
- Authoring emitter reads `mm._constants/_variables` and manufactures temporary token names (`c{id}`, `v{id}`):
  - [emit.py](file:///Users/mingli/MetaMath/proof-scaffold/src/skfd/authoring/emit.py)
- Builder front-end is primarily a **string token DSL** (`mm.a/e/p` accept `Sequence[str] | str`), requiring mapping layers:
  - [builder.py](file:///Users/mingli/MetaMath/proof-scaffold/src/skfd/builder/builder.py)
 
## Target Shape (What “good” looks like)
### Build API
Packages:
 
```python
from skfd.api_v2 import BuildContextV2
 
def build(ctx: BuildContextV2) -> None:
    mm = ctx.mm
    deps = ctx.deps
    names = ctx.names
```
 
Toolchain:
 
- Resolves dependency graph (dist names) and stable module identity (module names).
- Constructs `BuildContextV2(mm, deps, unit, names, cfg, log)` and calls `build(ctx)`.
 
### Deps Injection
No kwargs injection. Instead:
 
- `ctx.deps["metamath-prelude"]`
- `ctx.deps.prelude`
- `ctx.deps.metamath_prelude`
 
All refer to the same dependency interface.
 
### BuilderV2: SymbolId-only
BuilderV2 accepts only `SymbolId` for proof/expr payloads; any string DSL remains legacy-only.
 
### NameResolver/Lexicon + Artifact
Toolchain emits (per monolith build):
 
- `*.mm` (ASCII canonical)
- `*.mm.map` (sourcemap)
- `*.names.json` (Unicode ↔ ASCII mapping usage)
 
## Work Plan (Phased, with acceptance per phase)
 
### Phase 0 — Lock contract with tests (No behavior change)
**Deliverables**
- Tests asserting the V1 contract shape and key properties:
  - DepsView aliasing rules (dist/module/snake).
  - NameResolver conflict behavior (must fail early).
  - BuilderV2 rejects string tokens for expr/proof (runtime assertions + typing).
 
**Acceptance**
- `uv run python -m pytest` passes.
- Added tests are deterministic and do not depend on environment state.
 
### Phase 1 — NameResolver/Lexicon + names.json pipeline (Minimal MVP)
**Deliverables**
- `NameResolver` implementation + minimal built-in lexicon:
  - Start with a small set.mm-compatible base table plus a few Unicode aliases (e.g. `φ ψ → ¬ ∧`).
- Toolchain writes `*.names.json` in `target/` beside `.mm` and `.mm.map`.
 
**Acceptance**
- Golden test: stable names.json output for a fixed build input.
- Adversarial test: conflicting lexicon entries fail with a structured error.
 
### Phase 2 — MMBuilderV2 (SymbolId-only + Auto-$f)
**Deliverables**
- `MMBuilderV2` with:
  - `sym.const/var/label(name: str) -> SymbolId` (canonicalize then intern)
  - `f/e/a/p/d` (ID-level)
  - `block/comment/export/exports/finish`
- Auto-$f subsystem:
  - `floating/mandatory_f/vars_in`
  - `a/p` automatically ensure floating hypotheses for variables in expr (configurable, default on)
  - Deterministic label policy: `w{var}` then `w{var}0...`
 
**Acceptance**
- Unit tests cover:
  - Determinism of auto-$f generation
  - Scope correctness (no unbalanced scopes)
  - Export collection without reading private attributes
- No changes required to existing packages yet; legacy path still works.
 
### Phase 3 — Driver supports `build(ctx)` (Dual-path runner)
**Deliverables**
- Update Driver to:
  - Prefer `build(ctx)` if present.
  - Otherwise fall back to existing `build(mm, **deps)` and Script Mode.
- Introduce `PackageMeta {dist_name, module_name, build_path}` used by `DepsView`.
 
**Acceptance**
- Existing tests remain green.
- New feature tests:
  - A minimal fake package using `build(ctx)` builds and links correctly.
  - DepsView resolves dist/module/snake access consistently.
 
### Phase 4 — Authoring emit migration (Remove token_map & private-field reads)
**Deliverables**
- Rewrite `skfd.authoring.emit` entrypoints to use V2 builder when available:
  - Stop generating `c{id}/v{id}` temporary names.
  - Use `mm.auto` and ID-level `a/e/p`.
- Remove uses of `mm._constants/_variables` from authoring code paths.
 
**Acceptance**
- Feature tests (especially emit_lowered / authoring) remain green.
- Additional tests ensure emitted `.mm` stays ASCII-only (no Unicode leakage).
 
### Phase 5 — Migrate external packages (prelude → logic)
**Deliverables**
- Update `metamath-prelude` to `build(ctx)` and V2 APIs (smallest, fastest “canary”).
- Update `metamath-logic` and any emit helpers to V2 path.
 
**Acceptance**
- End-to-end monolith verification works for migrated packages.
- No private-field reads remain in authoring and driver layers for V2 packages.
 
## Definition of Done (Project 018)
This project is considered done when:
 
1. A package using `build(ctx)` can be built, linked, and verified via the toolchain.
2. `ctx.deps` supports dist/module/snake access without kwargs injection.
3. BuilderV2 path is SymbolId-only (expr/proof are never strings).
4. `*.names.json` is emitted and stable, and `.mm` output is ASCII canonical.
5. No core code path requires reading builder private fields for exports/constants/variables.
 
## Open Questions (Explicitly tracked)
1. **origin_module_id policy**: use `module_name` vs `dist_name` as the stable symbol origin key.
   - Recommendation: prefer `module_name` for stability; keep `dist_name` only for dependency resolution / CLI UX.
2. **Const/Var visibility across packages**: enforce as lint-only or as a hard rule in Stage 1.
   - Recommendation: v1 lint-only warning; keep verifier semantics unchanged.
3. **Script Mode deprecation**: timeline and migration tooling.
   - Recommendation: keep as sugar until Phase 5 lands; then mark deprecated and gradually remove from docs.
 
