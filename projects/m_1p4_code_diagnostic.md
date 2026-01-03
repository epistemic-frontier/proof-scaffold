# M1.4 Code Diagnostic (ProofScaffold)

This document is a code-level diagnostic of the **current M1.4 (Scope Planning)** baseline in the provided repository snapshot.

- Repo snapshot: `proof-scaffold.zip`
- Pipeline entrypoint: `src/proof_scaffold/linker_v0.py`
- Passes: `src/proof_scaffold/linker/passes/*`

> In this snapshot, the M1.4 test suite is green (run with `PYTHONPATH=src`).
> The items below are therefore **not “today it is red” bugs**; they are **structural debts / semantic gaps** that will predictably break or complicate M1.5+.

---

## 0) Current M1.4 pipeline (as implemented)

`LinkerV0.link()` runs the following passes:

1. **Stage 0.5**: `origin_seal.run(ctx)`
2. **Stage 1**: `stage1_collect.run(ctx)`
3. **Stage 1 lint**: `stage1_lint.run(ctx)`
4. **Stage 4**: `stage4_deps.run(ctx)`
5. **Stage 5**: `stage5_scope.run(ctx)`
6. **Stage 6**: `stage6_reloc.run(ctx)` (currently **label-only** mangling)
7. **Stage 7**: `stage7_emit.run(ctx)`

M1.4 *does* enforce:

- Scope balance within each unit (Stage1)
- Stable topo ordering (Stage4)
- “Decls before exports” ordering rule + `$c/$v` dropping inside frames (Stage5)

M1.4 *does not yet* implement:

- A real **SymbolTable** (`SymbolId -> SymbolDef`) required by v3 / M1.5 docs
- **Token-level relocation** for `$c/$v` and all token occurrences

---

## 1) P0 semantic gaps (high-risk debts)

### P0-1. Token IDs are *unit-local* today, but future passes already assume *global IDs*

**Where it shows up**

- Generator: `src/proof_scaffold/dsl/emitter.py` (`LIREmitter._tok_id`) interns token names into **per-unit** `self._symtab` and returns the local index.
- IR comment: `src/proof_scaffold/ir.py` claims `ProofUnitIR.symtab` is a “shared id space”, but the emitter contradicts this.

**Why this matters**

- As soon as you implement Stage6 token relocation as `dict[int, str]` (global table), you will collide because **tok_id=0** exists in *every* unit.
- This is the root reason why any “token-level relocation” quickly degenerates into hacks (e.g., `(unit_id,tok_id)` keys, string reverse-lookup), and why M1.6 header hoisting becomes brittle.

**Impact**

- Blocks a correct Stage6 (M1.5) implementation.
- Makes M1.6 (header hoist) and later `$d` propagation (M4) hard to implement without another rewrite.

---

### P0-2. Stage1 currently mixes “collect/index” with a *partial* “symbol resolution” (order-dependent)

**Where**

- `src/proof_scaffold/linker/passes/stage1_collect.py`
  - It computes `uses_assertions` by scanning theorem proof tokens.
  - During this scan it consults `label_owners` / `label_kind_by_unit` **as built so far**.

**Observed property**

- If unit B references an exported assertion label defined **later** (in input order), Stage1 may fail to record that dependency edge.
- The repository’s own tests already hint at this (“resolved at scan time” limitation in `tests/test_m13_acid.py`).

**Impact**

- Dependency closure can become incomplete in a way that is **silent** (not always caught by lint), yielding wrong unit ordering, missing required units, or verifier failures later.

---

### P0-3. Label resolution policy is inconsistent between Stage4 (deps) and Stage7 (emit)

**Where**

- Stage4 dependency owner selection (export-aware): `src/proof_scaffold/linker/passes/stage4_deps.py`
  - Picks an owner among exported `$a/$p` labels.
- Stage7 proof-token owner selection (NOT export-aware): `src/proof_scaffold/linker/passes/stage7_emit.py`
  - For a referenced label, it picks `stable_sorted(owners)[0]` with no export filtering.

**Why this matters**

- Even if Stage1_lint accepts a reference because *some* owner exports it, Stage7 may emit a reference to a **non-exported** owner (or the “wrong” owner) if multiple owners share the label string.

**Impact**

- Hidden nondeterminism (depends on which units define the same label name).
- Wrong proof token rewriting in output.

---

### P0-4. The current model cannot safely support cross-unit label collisions (the thing M1.5 wants to fix)

**Current reality**

- Linker indexes labels by *raw string label* (`ctx.label_owners: dict[label -> owners]`).
- Proof tokens refer to labels only by that same raw string (via symtab name).

**Consequence**

- If two units export the same label string, any third unit referencing that label becomes ambiguous.
- With the current representation, the linker cannot “know” which exported assertion was intended.

**Impact**

- M1.5’s relocation can rename symbols, but **it cannot retroactively disambiguate** an already-ambiguous reference.
- To truly allow label collisions, the IR needs to carry an **origin-qualified reference** (or a stable external key such as theorem `fqname`).

---

### P0-5. Global `$c/$v` namespace correctness is not validated

**What is missing**

- There is no global check preventing a token from being declared as both `$c` and `$v` across units.
- There is no early rejection of Metamath-reserved tokens (e.g. `$c`, `$v`, `$=`, `${`, …) being used as symbol names.

**Where**

- Generator does not forbid `$`-prefixed symbol names in `$c/$v` declarations (`MMBuilder.c/v`).
- Linker Stage1 checks token *type* is int, but does not validate token *form*.

**Impact**

- Verifier may fail much later with poor diagnostics.
- M1.5 requires Stage6 to reject invalid tokens based on **original form**, not sanitized output.

---

### P0-6. Diagnostics exist but are not fully observable

**Where**

- `src/proof_scaffold/linker/errors.py` → `LinkerDiagError.__str__` prints code + message + origins, but **omits `diag.details`**.

**Impact**

- Many passes already attach actionable details (e.g. offender unit, label, cycle path), but users/tests can’t see them.
- M1.5 tests (planned) require error messages to include `hint_original_token` when relocation mappings are missing.

---

## 2) P1 issues (medium risk, still worth fixing before M1.5)

### P1-1. Out-of-range token IDs are silently stringified

**Where**

- `_tok_name(...)` helpers in Stage1/Stage4/Stage7 often return `str(tok)` when `tok` is an int but out-of-range for `symtab`.

**Impact**

- A broken generator can produce token id 999; instead of failing fast, the system may emit literal `999` as a Metamath token.
- This is “debug-hostile” and will complicate M1.5 unmapped-symbol diagnostics.

---

### P1-2. `LinearPlan.prologue_stmts` exists but Stage7 ignores it

**Where**

- `src/proof_scaffold/linker/context.py` defines `LinearPlan.prologue_stmts`.
- `src/proof_scaffold/linker/passes/stage7_emit.py` always emits global `$c/$v` header and then frames; it does not consult prologue.

**Impact**

- M1.6 header hoisting + per-unit prologue will need a refactor anyway.
- Keeping a dead field increases the chance of “double prologue” bugs when M1.6 lands.

---

### P1-3. Stage5’s M1.4 “dropping-only” spec vs Stage7’s effective header hoist

**Observation**

- Stage5 drops `$c/$v` inside frames.
- Stage7 unconditionally re-emits a global header built from `ctx.global_consts/global_vars`.

**Impact**

- The repo’s `projects/m_1p4.md` describes M1.4 as “dropping-only” (not a full hoist), but the code behaves like a partial hoist.
- This spec/implementation mismatch becomes a recurring coordination tax.

---

### P1-4. Non-diagnostic exceptions still exist

**Where**

- `stage7_emit.py` raises `ValueError` for proof_step_ids length mismatch.

**Impact**

- Violates the “all failures as LinkerDiagError” expectation.
- Loses structured origin/chain information.

---

## 3) Summary of the “true crux”

The M1.4 codebase is intentionally minimalist, but **two design debts** dominate all later milestones:

1. **ID semantics debt**: token IDs are unit-local, while future passes need global IDs.
2. **Reference disambiguation debt**: cross-unit references are encoded as raw label strings, which cannot support collisions without additional origin-qualified information.

Everything else (relocation completeness, header hoist, `$d` propagation, debug before/after) becomes straightforward once those two are resolved.
