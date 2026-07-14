# ProofScaffold Link Model v4

**Status**: Draft (implementable spec)  
**Supersedes**: Link Model v3 (as the *entry* spec; v3 remains a reference at ./deprecated/002_link-model_v3.md )  
**Integrates**:  
- Link Model v3 (semantic IR + stages, ./deprecated/002_link-model_v3.md)  
- ADR-0001 IR Token Layout invariants (ID-based, contiguous, layout-agnostic, ./deprecated/005_ir_layout.md)  
- SPEC-0001 Debug Slice MVP (step-level diagnosability, ./deprecated/006_debug.md)

---

## 0. Scope and intent

This document is the **single entry specification** for implementing `linker_v1`.

It locks down:
- the **semantic contracts** of the middle-end (HIR optional, LIR required),
- the **representation contracts** that keep passes future-proof (int tokens, contiguous TokenSeq, layout-agnostic APIs),
- the **debug/diagnostic contracts** required from day 1 (origin chain, step spans, debug slice artifacts),
- and the **mandatory adversarial tests** that prevent regressions against known M1.4 structural debts.

This spec deliberately **does not mandate concrete storage layouts** (list vs array vs memoryview, tables vs objects),
only observable behavior and pass interfaces.

---

## 1. Principles and trust boundary

### 1.1 Verifier authority and untrusted generation

- The Metamath verifier is the **semantic authority**.
- Python generators and the linker are **untrusted builders**.
- The linker’s job is **structural integrity**: linkability discipline, relocation, scoping, and actionable diagnostics.

### 1.2 Determinism is a first-class constraint

Same input IR **must** produce the same:
- unit ordering,
- emitted names,
- emitted stream (byte-identical or token-identical, per test policy),
- diagnostics (same error → same structured fields and stable formatting).

### 1.3 Incremental verifiability

Every new capability must be introduced with:
- at least one sanity test (minimal link → emit → verify),
- at least one golden determinism test (fixed IR → fixed output),
- and adversarial tests for failure modes.

---

## 2. Terminology

- **Origin**: a stable provenance record (module + file:line + optional callsite summary).
- **Symbol**: any relocatable identifier (Const/Var/Label). Internally referenced by `SymbolId`.
- **Token**: an `int` (a `SymbolId`) that appears in math strings or proof token sequences in IR.
- **TokenSeq**: a contiguous, indexable sequence of tokens (ints), layout-agnostic.
- **ProofUnit**: the linkable boundary. A unit may export vocabulary, assertions,
  and foundation-owned ambient hypotheses; ordinary local hypotheses are not a
  dependency API.
- **Textual include**: Metamath `$[ file $]`, which splices another file into one
  statement stream. The file boundary has no scope or interface semantics.
- **Assertion contract**: the verifier-visible signature of an exported `$a` or
  `$p`, including mandatory `$f/$e` hypotheses and mandatory distinct-variable
  pairs. It survives after the provider unit's lexical scope closes.
- **Active DV relation**: the complete set of exact unordered variable pairs
  active at an assertion's definition site. It is implementation/proof-replay
  context and may mention proof-only variables.
- **Mandatory DV relation**: the subset of the active relation whose two
  endpoints are mandatory variables of the assertion. It is part of the public
  assertion contract.
- **HIR**: optional structured proof trace (e.g., `Apply(assertion, subst, step_id)`).
- **LIR**: required Metamath-shaped IR whose token payloads are **SymbolIds**, not strings.
- **ScopeFrame**: an explicit `${ ... $}` region in linear IR emission.

---

## 3. Representation invariants

### 3.1 Token identity invariants

1. **SymbolId is `int` at runtime.**  
   `SymbolRef` is not an object. It is an `int`.

2. **After Stage 1, all tokens are in a single global SymbolId space.**  
   No pass after Stage 1 may observe “unit-local token ids”.

3. **Tokens must never carry debug/provenance fields.**  
   Debug information lives in side tables (OriginTable, StepMap, SpanMap).

### 3.2 TokenSeq invariants

A token payload is a **TokenSeq** with the following required behavior:

- `len(seq) -> int`
- `seq[i] -> int` for `0 <= i < len(seq)`
- iteration yields `int`
- slicing is allowed either by:
  - Python slice returning a TokenSeq view, or
  - an explicit `slice_view(seq, start, stop)` helper.

Allowed implementations include:
- `list[int]`,
- `array('I') / array('L')`,
- `memoryview` over integer buffers,
- custom packed buffers.

**Passes must be layout-agnostic**:
- they must not assume `list` methods,
- they must not mutate token sequences in-place unless explicitly permitted by the pass contract.

---

## 4. Core data model

### 4.1 Primitive types

- `SymbolId = int`
- `OriginRef = int`
- `UnitId = str` (deterministic; recommended: `<module_id>:<unit_name>` or stable hash)
- `StmtId = int` (unique within a unit)
- `StepId = int` (unique within a unit; stable across runs)

### 4.2 OriginTable

An OriginTable is required from day 1.

- `OriginTable[OriginRef] -> OriginRecord`

OriginRecord fields (minimum):
- `module_id: str`
- `file: str`
- `line: int`
- optional: `function: str`
- optional: `callsite_digest: str` (short)

Rules:
- OriginRecords must be interned/deduplicated deterministically.
- Any Diagnostic must be able to reference at least one OriginRef.

### 4.3 SymbolDef and SymbolKey

SymbolDef (semantic record):

- `id: SymbolId`
- `kind: "Const" | "Var" | "Label"`
- `origin_ref: OriginRef`  (definition site)
- `local_name: str`        (human-facing within origin)
- `origin_module_id: str`  (for relocation naming)
- optional: `scope_class: "global_only" | "nest_safe"` (if still used)

SymbolKey (for global interning):

- `(origin_module_id, local_name, kind)` → `SymbolId`

Constraints:
- `local_name` MUST NOT start with `$` (reserved token prefix).
- Within the same `(origin_module_id, local_name)`:
  - it is an error for `kind` to be both Const and Var (kind conflict).

### 4.4 LIR statements

All LIR statements carry:
- `stmt_id: StmtId`
- `origin_ref: OriginRef`

Unlabeled statements:
- `ConstDecl(tokens: TokenSeq)`  // tokens are SymbolIds of kind Const
- `VarDecl(tokens: TokenSeq)`    // tokens are SymbolIds of kind Var
- `DisjointDecl(vars: TokenSeq)` // SymbolIds of kind Var
- `ScopeEnter`
- `ScopeExit`
- optional: `Comment(text: str)` (not a token payload; emitted as `$( ... $)`)

Labeled statements:
- `FloatingHyp(label: SymbolId, typecode: SymbolId, var: SymbolId)`
- `EssentialHyp(label: SymbolId, expr: TokenSeq)`
- `Axiom(label: SymbolId, expr: TokenSeq)`
- `Theorem(label: SymbolId, expr: TokenSeq, proof: TokenSeq)`

Rules:
- `label` SymbolId MUST be kind Label.
- `typecode` MUST be a Const symbol (as in Metamath typecodes).
- `expr` is TokenSeq of Const/Var symbols (typecode included in expr if your convention requires; keep v3 conventions consistent).
- `proof` is TokenSeq of Label symbols (proof tokens reference assertions/hyps labels).

### 4.5 HIR steps

HIR is optional, but Debug Slice requires at least StepId tracking (see §7).

Minimal HIR kernel:

- `Apply(step_id: StepId, assertion: SymbolId, subst: SubstMap, origin_ref: OriginRef)`

SubstMap:
- mapping `VarSymbolId -> Expr`
- `Expr` is `TokenSeq` (SymbolIds)

HIR step record (for debug slice):
- `step_id`
- `assertion_label_id`
- `subst_digest` (short, deterministic)
- `origin_ref`
- optional: `free_vars_digest`

### 4.6 ProofUnitIR

A ProofUnitIR contains:

- `unit_id: UnitId`
- `origin_ref: OriginRef` (unit creation site)
- `origin_module_id: str`
- `lir_stmts: list[LIRStmt]` (required)
- optional: `hir_steps: list[HIRStep]`
- `exports: list[SymbolId]` (exported symbols; classified by statement kind)
- optional: `export_contracts` (interface contract records if precomputed)

Export classes:
- `Const` / `Var`: vocabulary exports for authoring and formula construction.
- Foundation-owned `$f`: ambient foundation hypotheses.
- `$a` / `$p`: assertion exports usable as cross-unit proof references.
- Ordinary `$f` / `$e`: internal hypotheses; not importable cross-unit.

Constraints:
- A unit must be internally scope-balanced (its LIR scopes must balance).
- Cross-unit proof references to ordinary units are allowed only via exported
  `$a` / `$p` assertions.
- Cross-unit proof references to foundation-owned exported `$f` labels are
  allowed because the foundation frame is global.
- A unit must not depend on ordinary packages by referencing their internal
  `$f/$e` labels.
- A unit does not export a lexically active `$d` statement. Each exported
  assertion instead retains its own `mandatory_dv_pairs` after the unit frame
  closes.
- A theorem that applies an imported assertion must satisfy that assertion's
  mandatory DV relation from the theorem's own active DV relation. Provider
  scope is never inherited by an ordinary consumer unit.

### 4.7 Module boundary and `$d` semantics

ProofUnit linking is not Metamath textual inclusion. `$[ file $]` only expands
text; after expansion, `$d` follows ordinary `${ ... $}` lexical scope and the
included file has no independent interface. A ProofUnit is a semantic boundary:

- ordinary unit-local `$f/$e/$d` state is isolated by the unit's outer scope;
- an assertion label is exported together with its extracted assertion
  contract, not together with the provider's lexical environment;
- `active_dv_pairs` stays with the provider declaration/proof replay;
- `mandatory_dv_pairs` crosses the boundary as part of the exported assertion;
- the consumer supplies its own active `$d` relation and the verifier checks
  the imported contract after substitution.

For an application of assertion `A` under substitution `sigma`, every free
variable in `sigma(x)` must be disjoint from every free variable in `sigma(y)`
for each `(x, y)` in `mandatory_dv_pairs(A)`. Those substituted pairs must be
present in the consumer theorem's active DV relation. Closing the provider
scope neither erases this obligation nor satisfies it for the consumer.

The current linker implements this contract by loading the complete transitive
dependency closure, linking it in one process, and emitting one verified
transient monolith. This is whole-closure modular linking, not separate
compilation. An independently cached or cross-process unit interface is a
future format and must include stable semantic symbol identities, assertion
statements, ordered mandatory `$f/$e`, `mandatory_dv_pairs`, and an interface
digest. Process-local `SymbolId` values are not a serializable module ABI.
`ProofUnitIR` currently has exports but no declared imports, so level-1 access
control can enforce owner/export visibility within the supplied closure but
cannot yet prove that every reference follows a declared direct dependency
edge. `LinkResult` currently returns emitted text, source map, and linker
context, but does not persist its extracted assertion-contract table. Explicit
imports and a serializable contract-bearing result/interface are prerequisites
for separate compilation, not current features.

---

## 5. Pipeline stages

### Stage 0 — Front-end IR construction

Inputs:
- Python generators / DSL.

Outputs:
- OriginTable seeds
- local symbol registrations (possibly provisional)
- ProofUnitIRs with LIR (required) and HIR (optional)

Policy:
- Stage 0 may be conservative and reject obvious structural errors early
  (undeclared symbols, scope imbalance, illegal names).
- Stage 0 MUST attach `origin_ref` to every Statement and (if present) every HIR step.

### Stage 1 — Global symbol resolution and early lint

Purpose:
- establish a single global SymbolId space,
- rewrite all token payloads to global SymbolIds,
- reject forbidden patterns early.

Required outputs:
- `SymbolTable: SymbolId -> SymbolDef`
- rewritten ProofUnitIRs (all tokens are global SymbolIds)
- `ExportIndex` mapping exported label SymbolIds → owning units

Required checks:
1. **No raw-string tokens**, unless in explicit COMPAT mode.
2. **Reserved token names**: any local_name starting with `$` is rejected.
3. **Const/Var kind conflict** within same origin (see §4.3).
4. **Token kind correctness**:
   - proof tokens must be Label ids,
   - math tokens must be Const/Var ids.
5. **Out-of-range / unresolved token ids** are rejected (no silent stringification).
6. At conformance level 1 or higher, **cross-unit access control** is enforced:
   - referencing a non-exported assertion from another unit is an error.
   - referencing an ordinary unit’s `$f/$e` labels is an error, even if the
     owner attempted to export them.
   - referencing an exported foundation-owned `$f` label is allowed.
   - diagnostics distinguish assertion export, foundation hypothesis export,
     and internal hypothesis leakage.

COMPAT behavior (optional):
- raw label strings in proof tokens MAY be accepted only if they resolve to
  exactly one exported owner. If 0 or >1, fail with an ambiguity diagnostic.

### Stage 2 — Contract extraction

Outputs:
- For each exported assertion `A`:
  - `mandatory_hyps(A)` and `mandatory_vars(A)` (deterministic order)
  - `mandatory_dv_pairs(A)`, computed from the active relation and mandatory
    variables (it may be empty, but must not be silently unavailable)
- For each theorem `T`:
  - `uses_assertions(T)` computed from proof token ids (preferred)
  - optional: `uses_subst(T)` derived from HIR (if present)

Rules:
- If HIR exists, it must align with LIR proof ordering (StepId mapping must be consistent).

### Stage 3 — `$d` processing modes

Same as v3, with three modes:

- Mode A: pass-through explicit `$d`
- Mode B: linter-driven mapping (verifier errors → origin)
- Mode C: HIR-assisted propagation

Mode selection must be explicit per build configuration.

Regardless of mode, pair semantics are exact and unordered. Separate
declarations `$d x y $.` and `$d y z $.` do not imply `$d x z $.`. Stage 3 must
preserve the active relation needed to replay a provider assertion and derive
the mandatory relation attached to its exported contract. It must not copy the
provider's active relation into an ordinary consumer unit.

### Stage 4 — Dependency closure and topo sort

Inputs:
- `uses_assertions` graph from Stage 2.
- ExportIndex from Stage 1.

Outputs:
- a deterministic topological order of units,
- cycle detection diagnostics (reject cycles).

Rules:
- closure computation MUST be order-invariant w.r.t. input list ordering.

### Stage 5 — Scope planning

Baseline strategy (foundation-aware, conservative, debuggable):

- Emit the foundation unit at top level so its `$c/$v/$f` frame is ambient.
- Emit each ordinary unit inside an outer `${ ... $}` frame.
- Preserve author-authored nested scopes inside ordinary units.
- Emit unit-local `$f/$e/$d` as required inside that ordinary-unit frame.
- Emit exported assertion(s) and required internal statements inside that
  ordinary-unit frame.

Outputs:
- `LinearPlan` with:
  - `preamble_stmts` (optional comments)
  - `header_consts: set[SymbolId]`
  - `header_vars: set[SymbolId]`
  - `frames: list[ScopeFrame]` (each frame has statements)

Rules:
- `$c/$v` are not emitted inside frames in the final stream (see Stage 7).
- Ordinary unit frames prevent accidental `$f/$e/$d` leakage into downstream
  units. An exported assertion remains usable because its assertion contract
  was captured when the assertion was declared.
- A foundation `$d` emitted at top level is ambient for the remainder of the
  closure. That is verifier-compatible but privileged global state; the
  standard foundation policy is defined in
  [Foundation Scope v1](010-foundation-scope.md).

### Stage 6 — Token-level relocation

Compute deterministic emitted names:

- `emitted_name(SymbolId) -> str`

Relocation applies to:
- all labels,
- all constants and variables appearing in math strings,
- every endpoint of every `$d` relation,
- all proof tokens (labels).

Rules:
- Emitted names must be deterministic and collision-safe.
- A collision resolution strategy must be stable (e.g., stable prefix + stable suffix).

Output:
- `RelocTable: SymbolId -> str`
- optional: `RelocDebugTable` (local_name + origin for debug display)

### Stage 7 — Two-phase emission

Emit Metamath stream in three segments:

1. Preamble (optional):
   - comments only (`$( ... $)`), deterministic ordering.

2. Global header:
   - all `$c` declarations (relocated names)
   - all `$v` declarations (relocated names)

3. Body:
   - ScopeFrames and statements (`${ ... $}`),
   - contains `$d/$f/$e/$a/$p` only.

Rules:
- header tokens order must be deterministic.
- body must not contain `$c` or `$v` statements.

### Stage 8 — Debug artifacts and SourceMap

Minimum required outputs:
- structured Diagnostics (see §6)
- Debug Slice artifacts (see §7)

Optional:
- SourceMap from emitted spans to `(origin, unit_id, stmt_id, step_id)`.

---

## 6. Diagnostics contract

### 6.1 Diagnostic structure

A Diagnostic MUST include:

- `error_code: str`
- `message: str`
- `primary_origin_ref: OriginRef`
- `related_origin_refs: list[OriginRef]` (sorted deterministically)
- `details: dict[str, Any]` (JSON-serializable; stable key ordering)
- `origin_chain: list[dict]` (stage/unit/stmt/step breadcrumbs)

### 6.2 LinkerDiagError

All linker failures MUST raise `LinkerDiagError(diag)`.

Rules:
- No bare `ValueError`, `KeyError`, etc should escape the linker boundary.
- `__str__` MUST include `diag.details` in a deterministic rendering.

### 6.3 Deterministic formatting

- Any list in details must be sorted deterministically.
- Any “candidate list” must be ordered by a stable key (e.g., origin_module_id, local_name).

---

## 7. Debug Slice contract

Debug Slice is required from day 1 as sidecar metadata.
It must not pollute tokens.

### 7.1 Required mappings

For each theorem `T`:

- `proof_tokens: TokenSeq`
- `step_to_span: dict[StepId -> (start:int, end:int)]`
  - spans are half-open `[start, end)` in the LIR proof token sequence.

If HIR exists:

- `StepRecord[StepId] -> {assertion_label_id, subst_digest, origin_ref, ...}`

Optional but recommended:

- `emitted_step_index -> StepId` map (for robust verifier-step mapping)
- relocation before/after view for token windows:
  - show `SymbolId` window with `(local_name, origin_module_id)`
  - show relocated emitted token names

### 7.2 Determinism requirement

For the same failing verifier step, debug slice output must be deterministic:
- JSON byte-identical or field-identical with stable ordering.

---

## 8. Conformance levels

- **L0 Bootstrap**:
  - LIR required
  - no HIR
  - Debug Slice optional (but still recommended)
  - cross-unit export access control is not enforced; L0 is not an admissible
    module-boundary, cross-module DV, integration, or release gate

- **L1 Debug Slice**:
  - LIR required
  - StepId tracking + step_to_span required
  - cross-unit assertion/foundation-hypothesis export access control required
  - enables step-local debugging

- **L2 HIR-assisted**:
  - HIR Apply records with substitution metadata
  - enables MVP_STRICT checks and `$d` mode C

Build configuration must state the conformance level, and the linker must fail early if required artifacts are missing.

---

## 9. Testing strategy and mandatory adversarial suite

### 9.1 Test classes

1. Sanity tests:
   - minimal build → emit → verifier accepts.

2. Golden tests:
   - fixed IR input → fixed emitted output
   - deterministic relocation snapshots.

3. Adversarial tests:
   - crafted inputs that must fail fast, or must succeed in tricky edge cases,
   - with precise diagnostics and determinism guarantees.

4. Cross-module DV gates:
   - a consumer-local `$d` satisfies an imported assertion contract;
   - omitting that consumer-local `$d` is rejected by the verifier;
   - relocation keeps formula variables and `$d` endpoints aligned when
     provider and consumer intern the same local spellings as distinct symbols;
   - a package-driver integration companion carries the same contract through
     package metadata, `DepsView`, level-1 linking, relocation, and verification.

### 9.2 Mandatory adversarial tests for known M1.4 debts

The following tests are mandatory and must be included in CI.
Each test must enforce:
- earliest-stage failure/success as specified,
- deterministic outcome across input permutations.

---

## 10. Mandatory adversarial tests list

### ADV-P0-1 Global SymbolId space prevents token-relocation collision

**Motivation**: prevent unit-local token ids from breaking token-level relocation.

**Setup**:
- Unit A and Unit B each declare local symbols that would receive local ids starting from 0 in a naive per-unit interner.
- Both export a theorem label `th` and use a constant `c`.

**Execution**:
- Provide units in both orders: `[A,B]` and `[B,A]`.
- Run Stage 1 → Stage 6.

**Expectations**:
- Stage 1 outputs a single global SymbolId space; no `(unit,tok)` hacks exist after Stage 1.
- Stage 6 produces a RelocTable with distinct emitted names for A.th vs B.th and A.c vs B.c.
- The RelocTable and emitted output are identical across permutations.

**Failure mode**:
- If any pass still assumes unit-local ids, the test must fail with a diagnostic:
  `E_GLOBAL_ID_REQUIRED` including offending unit/token evidence.

---

### ADV-P0-2 Closure computation is order-invariant

**Setup**:
- Unit A exports theorem `A.th`.
- Unit B proves `B.th` and its proof references `A.th`.
- The input order is adversarial: units list is `[B, A]`.

**Execution**:
- Run Stage 1 → Stage 4.

**Expectations**:
- Stage 2 extracts `uses_assertions(B.th)` including `A.th`.
- Stage 4 topo-sorts units into `[A, B]` deterministically.
- The final emitted stream is identical to the build with input `[A, B]`.

**Failure mode**:
- Missing closure edge or silent omission must be rejected with:
  `E_CLOSURE_INCOMPLETE` at Stage 2/4 with details including the missing referenced label.

---

### ADV-P0-3 Export-aware resolution is consistent across stages

**Setup**:
- Unit A defines and exports label `th`.
- Unit B defines a non-exported internal label also named `th`.
- Unit C references `th` in a way that requires owner resolution.

**Execution**:
- In COMPAT mode only: C uses a raw label string `"th"` reference.
- Run Stage 1 and emission.

**Expectations**:
- Stage 1 resolves `"th"` to the **only exported** owner (Unit A).
- Stage 7 emits proof tokens referencing the relocated name of A.th, not B.th.
- Deterministic across permutations of unit ordering.

**Failure mode**:
- Any later-stage “owner selection” must not exist; if ambiguity persists, Stage 1 must fail, not Stage 7.

---

### ADV-P0-4 Label collision support and disambiguation

#### ADV-P0-4a Ambiguous raw label reference fails fast

**Setup**:
- Unit A exports label `th`.
- Unit B exports label `th`.
- Unit C references `"th"` as a raw label string (COMPAT mode).

**Execution**:
- Run Stage 1.

**Expectations**:
- Stage 1 fails with `E_LABEL_AMBIGUOUS`.
- Diagnostic details include a stable ordered candidate list:
  - `[{origin_module_id, unit_id, label_local_name, label_symbol_id}, ...]`.
- `__str__` includes details.

#### ADV-P0-4b Origin-qualified reference succeeds

**Setup**:
- Same A and B both export `th`.
- Unit C references **A.th explicitly** using an origin-qualified handle:
  - `TheoremRef` / `LabelRef` that resolves to A’s exported label SymbolId.

**Execution**:
- Run full pipeline to emission.

**Expectations**:
- Build succeeds.
- A.th and B.th are relocated to distinct emitted labels.
- C’s proof tokens reference the relocated label of A.th exactly.

---

### ADV-P0-5 Global `$c/$v` legality and reserved tokens

#### ADV-P0-5a Reserved token rejection

**Setup**:
- A unit declares a constant or variable with local_name starting with `$` (e.g. `$c`, `$=`).

**Execution**:
- Run Stage 1.

**Expectations**:
- Stage 1 fails with `E_RESERVED_TOKEN_NAME`.
- Diagnostic includes `hint_original_token` with the original local_name and origin.

#### ADV-P0-5b Const/Var kind conflict rejection within origin

**Setup**:
- Same origin_module_id declares local_name `x` as Const in one unit and Var in another unit.

**Execution**:
- Run Stage 1.

**Expectations**:
- Stage 1 fails with `E_CONST_VAR_KIND_CONFLICT`.
- Diagnostic includes both definition origins in `related_origin_refs` and details listing both defs.

---

### ADV-P0-6 Diagnostics details are observable and deterministic

**Setup**:
- Trigger any diagnostic that sets a non-empty `details` (e.g. `E_LABEL_AMBIGUOUS`).

**Execution**:
- Capture `str(LinkerDiagError)` and the structured `diag`.

**Expectations**:
- `__str__` contains a deterministic rendering of `details`.
- Re-running the same test produces identical string output.

### ADV-P0-7 Cross-unit `$d` assertion contract

These three gates are mandatory and live together in
`tests/linker/test_module_disjoint_contract.py`.
They MUST invoke the linker with `conformance_level=1` or higher. A verifier
success obtained from the default level 0 does not exercise the cross-unit
export boundary and is not gate evidence.

#### ADV-P0-7a Consumer-local `$d` satisfies an imported contract

**Setup**:
- Provider unit A declares a local `$d x y` and exports an assertion whose
  mandatory variables include `x` and `y`.
- Consumer unit B declares the corresponding local `$d` pair and proves a
  theorem by applying A's exported assertion.

**Expectations**:
- Linking closes A's ordinary unit scope before B.
- The emitted transient monolith verifies successfully.
- A's `$d` does not appear as ambient state in B; B's local relation is what
  satisfies the imported assertion contract.

**Test**:
- `test_cross_unit_dv_contract_accepts_consumer_local_disjoint`

#### ADV-P0-7b Missing consumer-local `$d` is rejected

**Setup**:
- Use the same provider and consumer application as ADV-P0-7a, but omit the
  required pair from B's active DV relation.

**Expectations**:
- Link and emission must not manufacture or inherit A's local `$d` for B.
- Metamath verification rejects the theorem with a disjoint-variable
  violation.

**Test**:
- `test_cross_unit_dv_contract_rejects_missing_consumer_local_disjoint`

#### ADV-P0-7c Relocation preserves formula/DV endpoint identity

**Setup**:
- Provider and consumer independently intern variables with the same local
  spellings, so their `SymbolId`s differ.
- Both formulas and local `$d` relations use those distinct symbols before
  linking.

**Expectations**:
- Collision-safe emitted names may differ, for example provider `x/y` and
  consumer `x0/y0`.
- Each unit's formula endpoints and `$d` endpoints relocate to the same names
  within that unit; no endpoint is captured by the other unit's spelling.
- The final stream verifies successfully.

**Test**:
- `test_cross_unit_dv_relocation_keeps_formula_and_dv_endpoints_aligned`

### ADV-P0-8 Package-driver cross-package `$d` integration

The three ADV-P0-7 tests lock the native linker semantics. The companion
integration gate MUST also exercise the actual package path rather than
constructing only in-memory units:

- `tests/driver/test_runner_v2.py::test_runner_ctx_deps_preserves_cross_package_dv_contract`

It must resolve a provider through package metadata and `DepsView`, invoke
`verify_package(..., conformance_level=1)`, relocate the linked closure, and
complete Metamath verification. This positive integration gate does not replace
ADV-P0-7b: the native negative test remains the proof that provider scope is not
silently inherited.

---

### ADV-P1-1 Out-of-range token ids are rejected, never stringified

**Setup**:
- Construct a unit with a token id 999 in its token payload that is not resolvable by Stage 1.

**Execution**:
- Run Stage 1.

**Expectations**:
- Stage 1 fails with `E_TOKEN_ID_OUT_OF_RANGE`.
- Diagnostic details include `tok_id=999` and the owning unit/stage info.
- No emitted output exists; “999” must never appear as a Metamath token.

---

### ADV-P1-2 Preamble statements are emitted exactly once

**Setup**:
- Build a LinearPlan with `preamble_stmts` containing 1–2 `Comment` statements.

**Execution**:
- Run Stage 7 emission.

**Expectations**:
- The emitted stream begins with those comments (in order).
- Each preamble comment appears exactly once.
- Deterministic across runs.

---

### ADV-P1-3 Two-phase header hoist is consistent and complete

**Setup**:
- Two units each declare some `$c/$v` locally (in LIR) and export simple assertions.

**Execution**:
- Run Stage 5 → Stage 7.

**Expectations**:
- Header contains the union of all constants and variables (after relocation), each exactly once.
- Body contains no `$c` or `$v` statements.
- Output deterministic across unit order permutations.

---

### ADV-P1-4 All failures are LinkerDiagError, never bare exceptions

**Setup**:
- Construct an IR mismatch such as `proof_tokens` vs `proof_step_ids` / `step_to_span` inconsistency.

**Execution**:
- Run the stage that validates the mapping (Stage 2/8 depending on implementation).

**Expectations**:
- Failure is `LinkerDiagError` with code `E_STEP_SPAN_MISMATCH` (or equivalent).
- Diagnostic includes origin chain pointing to the theorem/unit/step.

---

## 11. Notes on implementation freedom

This spec intentionally freezes only:
- **interfaces and invariants** (int tokens, TokenSeq behavior, sidecar debug tables),
- **stage responsibilities** and deterministic requirements,
- and **adversarial tests** as regression guards.

It does **not** freeze:
- whether you store SymbolTable as dicts vs arrays,
- whether TokenSeq is list vs array vs packed buffer,
- whether you implement SourceMap now or later (Debug Slice is the MVP requirement).

---

**End of Link Model v4.**
