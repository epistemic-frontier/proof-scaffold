# Project 020: Foundation Scope and Prelude/Logic Boundary Refactor

## Status

Implemented for the current foundation/prelude/logic refactor slice.

## Context

Project 018 landed the main BuilderV2 direction, but the package/link model is
still not aligned with how the standard `metamath-prelude` / `metamath-logic`
stack actually works.

The key mismatch is that the Metamath kernel is tiny, while our current docs
sometimes treat `metamath-prelude` as an ordinary package and sometimes rely on
it as a global foundation frame. The implementation already depends on the
second interpretation: prelude `$f` labels are effectively ambient.

Normative reference: [references/010-foundation-scope.md](file:///Users/mingli/MetaMath/proof-scaffold/references/010-foundation-scope.md)

Related references:

- [references/002_link-model_v4.md](file:///Users/mingli/MetaMath/proof-scaffold/references/002_link-model_v4.md)
- [references/007-package.md](file:///Users/mingli/MetaMath/proof-scaffold/references/007-package.md)
- [references/009_builder-v2.md](file:///Users/mingli/MetaMath/proof-scaffold/references/009_builder-v2.md)
- [projects/018-builder-v2-migration.md](file:///Users/mingli/MetaMath/proof-scaffold/projects/018-builder-v2-migration.md)

## Goals

1. Make foundation scope explicit in driver/linker semantics.
2. Split export handling into vocabulary, foundation hypothesis, assertion, and
   internal hypothesis classes.
3. Move non-foundation logic content out of `metamath-prelude`.
4. Preserve verifier authority and ASCII canonical `.mm` emission.
5. Refresh stale package templates and docs so new packages use `build(ctx)`.

## Non-Goals

- Changing Metamath verifier semantics.
- Adding proof search or proof automation.
- Replacing the whole linker pipeline.
- Deleting legacy script mode in this project.
- Migrating all future predicate/set-theory content.

## Current State

- `metamath-prelude` currently exports foundation vocabulary and global `$f`
  labels, and `metamath-logic` uses them.
- `metamath-prelude` also currently contains `wo`, `wtru`, `wfal`, `idi`, and
  `a1ii`, which are ordinary propositional-logic content.
- `ExportsView` is a flat `Mapping[str, SymbolId]`; it does not expose export
  class to authors or linker diagnostics.
- Link Model v4 says cross-unit `$f/$e` references are forbidden, but the
  practical standard stack needs a controlled exception for foundation-owned
  `$f`.
- Some templates and examples still describe pre-BuilderV2 entrypoints.

## Target Shape

### Package roles

The build closure contains at most one foundation unit:

- `foundation`: standard `metamath-prelude`, emitted first and top-level.
- `library`: reusable logic package such as `metamath-logic`.
- `application`: project package proving local results.

### Prelude boundary

`metamath-prelude` should contain:

- `wff`, `|-`;
- `(`, `)`, `-.`, `->`;
- schema variables and their global `$f` labels;
- primitive syntax axioms `wn` and `wi`.

`metamath-logic` should contain:

- `ax-mp`, `ax-1`, `ax-2`, `ax-3`;
- `wo`, `wtru`, `wfal`;
- `idi`, `a1ii`;
- later derived propositional theorems.

### Export classes

The linker should classify exported symbols as:

- vocabulary export: `Const` / `Var`;
- foundation hypothesis export: foundation-owned `$f`;
- assertion export: `$a` / `$p`;
- internal hypothesis: ordinary `$f` / `$e`, not importable cross-unit.

The first implementation may keep the public `ExportsView` mapping unchanged and
perform classification through internal indices.

## Work Plan

### Phase 0 - Documentation lock

Deliverables:

- Add the foundation scope specification.
- Add this engineering plan.
- Add cross-reference notes to Package, BuilderV2, and Project 018 docs.

Acceptance:

- Documentation states one consistent model for prelude/logic boundaries.
- The current implementation gaps are named explicitly.

Status: done.

### Phase 1 - Package kind metadata

Deliverables:

- Add an internal package kind field to discovered/build metadata.
- Short-term: detect `metamath-prelude` as `foundation`.
- Default all other build units to `library` or `application` without behavior
  change.

Acceptance:

- Existing driver tests pass.
- A test closure containing `metamath-prelude` records exactly one foundation.
- A closure with two foundations fails deterministically.

Status: done.

### Phase 2 - Export classification and access control

Deliverables:

- Build a linker-side export classifier from resolved LIR statement kinds.
- Permit cross-unit proof references to foundation-owned `$f`.
- Reject cross-unit proof references to ordinary `$f/$e`.
- Keep assertion imports restricted to declared dependency exports.
- Produce diagnostics that identify the failed export class.

Acceptance:

- Existing `metamath-prelude` -> `metamath-logic` proofs still verify.
- A test ordinary package exporting `$f` cannot make another package use it.
- A test ordinary package exporting `$e` cannot make another package use it.

Status: done.

### Phase 3 - Prelude/logic content move

Deliverables:

- Move `wo`, `wtru`, and `wfal` from `metamath-prelude` to `metamath-logic`.
- Move `idi` and `a1ii` from `metamath-prelude` to `metamath-logic`.
- Update imports, theorem registry, catalogue, and package READMEs.
- Update source maps/goldens if affected.

Acceptance:

- `metamath-prelude` emits only foundation content.
- `metamath-logic` emits and exports the moved labels.
- Full transient monolith verification passes.

Status: done.

### Phase 4 - Scope hardening

Deliverables:

- Audit Stage 5 ordinary-unit emission.
- Wrap ordinary units in `${ ... $}` while keeping the foundation frame top-level.
- Add regression tests for ordinary local `$e` and `$f` non-leakage.

Acceptance:

- No ordinary package can accidentally create ambient hypotheses for dependents.
- Foundation remains top-level and continues to verify.

Status: done.

### Phase 5 - Templates and docs cleanup

Deliverables:

- Update `init-pkg` template to generate `build(ctx)`.
- Update or replace `init-proof` template if it references removed classes.
- Refresh README quickstart and package authoring examples.
- Align package versions mentioned by docs with `pyproject.toml`.

Acceptance:

- `python -m skfd.cli init-pkg <name>` creates a project that builds through the
  current driver path.
- `python -m skfd.cli init-proof <file>` either creates a valid artifact or is
  clearly marked legacy/deprecated.

Status: done for templates and primary docs.

## Definition of Done

Project 020 is done when:

1. Foundation scope is represented in driver/linker metadata.
2. Stage 1 distinguishes foundation `$f` from ordinary `$f/$e` leakage.
3. `metamath-prelude` contains only foundation content.
4. `metamath-logic` owns `wo`, `wtru`, `wfal`, `idi`, and `a1ii`.
5. Templates and user-facing docs no longer teach stale APIs.
6. The standard prelude+logic build verifies through the existing verifier
   aggregate.

## Risks

- Moving labels can change emitted order. Tests should assert verifier behavior,
  not merely old textual placement.
- Keeping `ExportsView` flat may remain confusing. If diagnostics become messy,
  structured exports should be promoted earlier.
- Auto-`$f` and foundation ambient `$f` overlap. The refactor should prevent
  duplicate schema floating hypotheses for packages intentionally using the
  foundation frame.
