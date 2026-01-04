# Post-M1.4 Evolution Redesign (Proposed)

This document proposes a **stable evolution route after the current M1.4 baseline**, with the explicit goal:

- keep the existing M1.1–M1.4 tests unchanged (green)
- pay down the debts that made M1.5 fragile
- converge to the v3 architecture (SymbolTable + token-level relocation) with minimum “backwave” rework

---

## 0) What we keep fixed (non-negotiable invariants)

1. **Token Layout invariant (ADR-0001 / 005):** token payloads remain `int` contiguous sequences; passes must be layout-agnostic.
2. **Determinism:** no Python `hash()`; all ordering explicit and stable.
3. **Test discipline:** do not mix “change tests” and “change code” in the same step.

---

## 1) The key reframing: M1.5 cannot be “just Stage6”, because Stage6 depends on a SymbolTable

M1.5 docs (and v3) assume a `SymbolTable: SymbolId -> SymbolDef(kind, local_name, origin, ...)` exists.

In current M1.4 code, that table does not exist, and token IDs are not globally stable.

Therefore, the redesign is:

> Before implementing Stage6 relocation, implement **Stage 1.5: Unification / SymbolTable construction** on the linker side.

This is exactly the “Route B-Prime” idea: **do not force the generator to change first**; let the linker build its own worldview.

---

## 2) New minimal milestones after M1.4

### M1.4.1 (Tech Debt): GlobalSymbolTable + UnificationMap (no user-visible behavior change)

**Goal:** introduce global symbol identity while keeping the emitted stream identical to M1.4.

**Deliverables**

- `GlobalSymbolId = int` and `GlobalSymbolTable` structure, stored in `LinkContext`.
- `UnificationMap[(unit_id, local_tok_id)] -> global_sym_id`.
- A global `name_of(global_sym_id) -> raw_local_name` helper.
- Lint checks:
  - const/var collision (`ph` cannot be both `$c` and `$v` globally)
  - illegal token forms at the *raw* level (reserved `$c`, `$v`, ...)
  - out-of-range local token id should be a hard error (not silently stringified)

**No behavioral changes**

- Stage7 emission still outputs raw token names (no relocation yet).
- Existing tests remain green.

**Implementation strategy**

- Add a new pass `stage1_unify.run(ctx)` (or `stage2_symbols.run(ctx)`) inserted after `stage1_collect`.
- Do not rewrite LIR statements yet; keep UnificationMap as a side table.


### M1.5 (Relocation): Stage6 relocation uses GlobalSymbolId

**Goal:** implement real token-level relocation (v3 Stage6) on top of the new GlobalSymbolTable.

**Deliverables**

- `RelocationPlan` in context:
  - `name_of: dict[GlobalSymbolId, str]`
  - `reverse: dict[str, GlobalSymbolId]`
  - `collisions: list[...]`
  - `plan_hash: u64`
- Reserved token rejection uses **raw local_name**, not sanitized output.
- Collision resolution includes counter salt to guarantee termination.

**Test strategy**

- Enable the existing `tests/m15_relocation.py` by renaming to `tests/test_m15_relocation.py` only when the code is ready.
- Or, keep it as-is and add a new `test_m15_relocation_plan.py` first (tests-only commit), then implementation commit.


### M1.5.1 (Relocation Application): Stage7 emission becomes relocation-driven

**Goal:** ensure every token occurrence in emitted Metamath goes through relocation.

**Deliverables**

- Stage7 emits:
  - statement labels via relocation (either through a unified label-id table or a relabel side map)
  - `$c/$v` header via relocated names
  - all expr tokens via relocated names
  - proof token stream via relocated names
- Diagnostic:
  - `E_RELOC_UNMAPPED_SYMBOL` includes `hint_original_token` in the *string* message


### M1.6 (Header Hoisting / Contract): make header generation explicit and contract-driven

In the current codebase Stage7 already emits a global `$c/$v` header.
M1.6 should therefore be redefined as:

- **Contract extraction** (what each exported assertion requires)
- emission of per-unit prologue / contract blocks (if desired)
- optional sorting/grouping policy for header

---

## 3) Design sketch: Stage1 Unification (Route B-Prime)

### 3.1 Data structures (minimal)

- `GlobalSymbolId = int`
- `SymbolKey = (kind, name)` for `$c/$v` (global namespace)
- `LabelKey = (origin_unit_id, label_name)` for labels that must remain distinct
- `GlobalSymbolTable`:
  - `id_to_def: list[SymbolDef]`
  - `key_to_id: dict[SymbolKey|LabelKey, GlobalSymbolId]`
- `UnificationMap: dict[(unit_id, local_id), global_id]`

### 3.2 How unification can be done without changing the generator

- For each unit:
  - scan `ConstDecl` / `VarDecl` to classify local IDs
  - build a local map `local_id -> (kind, raw_name)`
  - install mapping into GlobalSymbolTable using the appropriate key
  - fill UnificationMap

- For tokens in expressions:
  - their (kind,name) is determined by the declared sets from that unit.

- For proof tokens:
  - initially treat them as label references by **raw label string**.
  - resolve them via `(owner_unit, label)` when unique.
  - if ambiguous: raise a new `E_AMBIGUOUS_LABEL_REF` and require the generator to provide an origin-qualified reference later.

This makes the limitation explicit and prevents silent wrong linkage.

---

## 4) Where this redesign reduces “backwave” rework

- M1.6 header hoisting becomes a trivial iteration over GlobalSymbolTable.
- `$d` propagation can merge constraints by GlobalSymbolId instead of fragile string matches.
- Debug slice can show before/after via SymbolDef.local_name and relocation plan.

---

## 5) Practical working mode: keep LinkerV0 stable, develop LinkerV1 side-by-side

To respect “don’t change tests and code in the same step” **and** keep the mainline green, the safest approach is:

- Keep `LinkerV0` unchanged (still passes M1.1–M1.4 tests).
- Implement a new `LinkerV1` (or `link_v1`) that includes:
  - Stage1_unify
  - Stage6 relocation
  - Stage7 relocation-driven emission

Then:

1. Add new M1.5 tests targeting LinkerV1 (tests-only step).
2. Implement passes to make them pass (code-only step).
3. Once stable, either:
   - switch LinkerV0 to delegate to V1, or
   - deprecate V0.

