# ProofScaffold Generator Design — Supplementary Document 04 (Rev. 2)

**Status**: Draft  
**Scope**: Python-side *Generator / DSL / import–export* design; a concrete supplement and realization of:

- `001_arch-design.md` (three-layer architecture and trust boundary)
- `002_link-model_v3.md` (Link Model v3: IR / Contracts / ScopeFrames / Relocation / SourceMap)
- `003_roadmap-methodology_v2.md` (Roadmap and engineering methodology)

The purpose of this document is to **upgrade the existing DSL + manifest + toy linker** into a *formal front-end*, **without changing any v3 Link Model invariants**, and to make explicit how it provides the Linker with **linkable, relocatable, and diagnosable IR inputs**.

---

## 0. Design Motivation: From “Interpreter-Style Construction” to a “Compiler Toolchain”

The current DSL usage experience is closer to an *interpreter*:

- Write Python code that is executed step-by-step to construct declarations, enter/exit scopes, and insert `$f/$e/$a/$p` statements.
- Perform conservative checks during construction (undeclared tokens, scope imbalance, label visibility, etc.).

By contrast, the v3 Link Model adopts a *compiler toolchain* perspective:

- The front-end outputs structured IR (LIR required, HIR optional).
- The back-end Linker performs closure computation, ScopeFrames planning, token-level relocation, two-phase emission, and SourceMap generation.

**Key conclusion**: These two views are not in conflict.

This design explicitly positions the DSL as **Stage 0 (Front-end IR construction)**. The DSL may remain “interpreter-like” in ergonomics, but its output **must be v3-compliant IR (with SymbolRef tokens)**, rather than prematurely materialized `.mm` strings.

---

## 1. Strengths of the Current Version (To Preserve and Amplify)

The existing `MMBuilder` / `export` / `Linker.resolve` already provide an excellent foundation:

1. **Early conservative semantic checks**  
   Many structural errors are caught at generation time (undeclared tokens, label conflicts, scope imbalance).

2. **Explicit scoping discipline**  
   In `strict` mode, top-level `$e` is forbidden and `${ ... $}` is enforced, aligning closely with v3’s ScopeFrames philosophy.

3. **Explicit cross-module dependencies**  
   Proof steps can reference `Theorem` handles; `requires()` collects linkable dependencies explicitly.

4. **Export manifest mechanism**  
   A lightweight JSON-based “interface database (mmdb)” enables import/export experiments.

This supplement does *not* discard these strengths. Instead, it **upgrades them from a string generator into an IR generator**.

---

## 2. Design Goals and Non-Goals

### 2.1 Goals

- **G1: Full compatibility with the v3 Link Model**
  - Proof tokens and math-string tokens must be `SymbolRef[]` (not raw strings).
  - Unit boundaries are centered on `ProofUnit`; cross-unit references are limited to exported `$a/$p`.
  - The Linker is free to perform relocation on *all tokens* at Stage 6.

- **G2: Preserve the DSL’s “fail fast” experience**
  - Reject declaration-order errors, scope errors, illegal references, and obvious contract violations as early as possible.

- **G3: Diagnosability**
  - Every Statement and ProofStep carries `origin` metadata (module + file:line + optional call-stack summary), enabling SourceMap to provide an *unmangled* view.

- **G4: Incremental adoption**
  - Support an explicit COMPAT transition period, default-off, with a clear migration plan.

### 2.2 Non-Goals

- No proof search or backtracking (the generator is not a prover).
- No standardization of proof compression, caching, or incremental verification (consistent with v3 non-goals).
- Metamath is not made human-facing; humans write DSL/docs, Metamath remains the target artifact.

---

## 3. Overall Structure: Generator Produces IR, Linker Links and Emits

### 3.1 Recommended Data Flow

```
Python proof packages (DSL code)
  └─ Generator Front-end (this document)
       ├─ Symbol registrations (SymbolDef)
       ├─ ProofUnitIR(s)
       ├─ LIR graph (required)
       └─ HIR graph (optional)
  └─ Linker (v3)
       ├─ resolve + lint
       ├─ contract extraction
       ├─ $d modes A/B/C
       ├─ closure + topo sort
       ├─ scope planning (ScopeFrames)
       ├─ relocation (token-level)
       ├─ emission (header + body)
       └─ SourceMap + diagnostics
  └─ Metamath verifier (authoritative)
```

### 3.2 Responsibility Boundary (Generator vs Linker)

**Generator (front-end) guarantees**:

- Structural well-formedness: balanced scopes, IR-resolvable tokens (SymbolId/Ref), no obvious cross-unit `$f/$e` leakage.
- Explicit dependencies: each ProofUnit’s external dependencies are explicit (at least as hints; ideally derivable from proof tokens).
- Provenance: every IR node carries `origin` metadata.

**Generator does not guarantee**:

- Logical correctness of proofs. Acceptance/rejection is solely the verifier’s responsibility.

**Linker (back-end) guarantees**:

- v3 middle-end invariants: deterministic emission, token-level relocation, correct contracts/binding, proper ScopeFrames.
- Emitted `.mm` is syntactically well-formed and executable by the verifier.

---

## 4. Core Artifacts and Data Structures

This section presents a *minimal implementable* data model aligned with v3 terminology.

### 4.1 Symbol System (Aligned with v3)

- `SymbolId`: internal stable ID, never emitted.
- `SymbolDef`: `{origin, local_name, kind(Const|Var|Label), scope_class}`.
- `SymbolRef`: reference to a `SymbolId`; **all token payloads must ultimately be `SymbolRef[]`**.

*Design decision*: the Generator may use provisional local SymbolIds, but Stage 1 must resolve them into the global, relocatable SymbolId space.

### 4.2 ProofUnitIR (Generator’s Primary Output)

Minimal fields:

- `unit_id`: stable ID (recommended: `<module_id>:<local_unit_name>` or a deterministic hash).
- `origin`: generation callsite (module + file:line).
- `decls_local`: unit-local declarations (`$f/$e/$d`) and permitted internal helper labels.
- `exports`: one or more exported assertions (initially recommended to limit to one).
- `proof_body`:
  - **LIR**: Metamath-shaped statements with `SymbolRef[]` tokens.
  - **Optional HIR**: structured traces such as `Apply(assertion, subst, step_id)`.

### 4.3 Export DB (mmdb) and Interface Records

The existing JSON-based `export.py` is a good minimal mmdb. This design recommends versioning and extending it as:

- `module`: module_id
- `format_version`: e.g. `"mmdb@2"`
- `exports[name]`:
  - `label_ref`: *do not* freeze final label strings; record relocatable references (SymbolId or `(origin, local_name, kind)` key)
  - `typecode_ref`
  - `expr_refs: SymbolRef[]`
  - `interface_contract` (optional but recommended):
    - `mandatory_hyps`
    - `mandatory_vars`
    - `dv_contract`
    - `public_symbols` (exported `$a/$p` only)
  - `closure_contract` (optional):
    - `uses_assertions`
  - `requires` (allowed as a bootstrap hint; eventually superseded by extracted closure)

During bootstrap, `label_ref` may temporarily fall back to string labels (COMPAT mode only).

### 4.4 Python-Side Handles: `TheoremRef` / `ImportedTheorem`

Current `Theorem` handles carry string labels for convenience. For token-level relocation, labels should no longer be the primary truth.

Recommended handle:

- `TheoremRef`:
  - `fqname`
  - `symbol_key` / `label_id` (relocatable reference)
  - optional `debug_label_hint` (for human display only)
  - optional `interface_contract_digest` (for early lint / IDE feedback)

Proof steps should prefer `TheoremRef` over raw string labels.

---

## 5. DSL (`MMBuilder`) Upgrade: From String Emission to IR Construction

### 5.1 Core Refactor: Builder Buffers Are No Longer `_lines: list[str]`

Instead of accumulating `.mm` strings, the builder should maintain:

- `_stmts: list[LIRStmt]` (required)
- `_hir_ops: list[HIROp]` (optional)
- `_symbols: LocalSymbolTable` (mapping local_name → local SymbolId)
- Captured `origin` metadata per statement

A **debug-only** `render_mm_compat()` may be retained to render LIR into a human-readable, *unrelocated* Metamath snippet.

### 5.2 Profiles and Restrictions (Suggested)

Extend existing `strict` rules into explicit profiles:

- `PROFILE_BOOTSTRAP`
  - Allows limited raw string tokens (explicitly enabled)
  - Allows `requires` as closure hints

- `PROFILE_V3_LIR` (default)
  - Forbids raw string tokens (unless allowlisted)
  - Proof steps must use `LabelRef/TheoremRef`

- `PROFILE_V3_HIR`
  - Requires recording substitution metadata
  - Enables `$d` mode C and MVP_STRICT

### 5.3 Unit Boundaries: Explicit `unit(...)` Blocks

Introduce explicit units:

```python
with mm.unit("sqrt2irr") as u:
    u.f(...)
    u.e(...)
    u.p(...)
    export(u, name="sqrt2_irrational", ...)
```

Rules:

- One `unit()` corresponds to one `ProofUnitIR`.
- Each unit implicitly forms a ScopeFrame (matching v3 Stage 5 baseline emission).
- Declarations outside a unit must not implicitly affect its interior.

---

## 6. Import / Export: Making Interfaces a Linkable API

### 6.1 Semantics of `export`

`export(...)` must *not* assume final emitted label names. It should:

- Record relocatable label references (`label_id` / `symbol_key`)
- Record `expr_refs: SymbolRef[]`
- Record interface contracts when available
- Return a `TheoremRef` for downstream imports

### 6.2 Semantics of `import`

Provide `import_theorem("a.b.c.thm") -> TheoremRef`:

- Reads the theorem record from mmdb
- Returns a relocatable handle
- Allows proof steps to reference it and records the dependency

### 6.3 Definitions as Exportable Packages

In Metamath, a “definition” is not a primitive; it is a *package* consisting of:

- New symbol declarations (`$c`, possibly public `$v` conventions)
- One or more assertions (`$a/$p`):
  - formation/typing axioms
  - definitional equations (`df-*`)
  - optional rewrite or existence lemmas

From the perspective of Link Model v3, a definition package is not merely
a convenience, but the canonical modeling unit for reusable,
symbol-introducing constructs.

- `provides_symbols`: new `Const`/`Var` SymbolDefs
- `exports_assertions`: one or more exported `$a/$p`
- `definition_meta` (non-TCB): unfold/rewrite/pretty-print hints

Correctness remains verifier-defined; definition packages do not alter the trusted computing base.
Their role is to make reuse, dependency closure, and relocation explicit and mechanically analyzable.

### 6.4 Extending mmdb: Assertions, Symbols, Definitions

Recommend a unified `ExportItem` schema:

1. **Assertion export** (`kind: "assertion"`)
   - relocatable label reference
   - typecode and expression refs
   - optional interface/closure contracts

2. **Symbol export** (`kind: "symbol"`)
   - symbol key or SymbolId
   - declaration class (`Const` or `Var`)

3. **Definition export** (`kind: "definition"`)
   - `provides_symbols`
   - `exports_assertions`
   - optional metadata

Corresponding APIs:

- `export_symbol`, `export_assertion`, `export_definition`
- `import_symbol`, `import_assertion`, `import_definition`

---

## 7. Contracts and `$d`: Generator Cooperation with v3 Modes

### 7.1 Mode A (Pass-through)

The Generator supplies:

- Interface-level `dv_contract`
- Optional local `$d` for internal proof safety

The Linker only places them at correct binding points.

### 7.2 Mode B (Linter-driven)

The Generator does not infer `$d`, but must provide:

- Precise `origin` metadata
- Minimal reproducible unit slices

So verifier errors can be mapped back to specific proof steps.

### 7.3 Mode C (HIR-assisted)

The Generator records HIR:

- `Apply(assertion, subst, step_id)`
- `SubstMap` with free-variable sets or digests

Enabling sound (non-search) constraint propagation in the Linker.

---

## 8. Build Modes: Avoiding “Fake Proof” Pollution in CI

Distinguish two artifact types:

1. **Interface build**
   - Output: mmdb (exports + contracts), optional debug snippets
   - Verifier acceptance not required

2. **Verifiable build**
   - Output: fully linked `.mm` stream
   - Verifier acceptance required (default CI path)

Toy examples with placeholder proofs should use *interface builds*, not failing `$p` proofs.

---

## 9. SourceMap: Capture Origin at Generation Time

Key points:

- Every stmt/proof step records `origin` (module, file, line; optional function/unit name)
- Stage 8 emits mappings:
  - `stream_span → (origin, unit_id, stmt_id, label?, proof_step_idx?)`
- Optional enrichments: active context digest, used assertion id, substitution digest

---

## 10. Testing and Acceptance (Aligned with the Roadmap)

- **Sanity tests**: minimal DAG → link → emit → verify
- **Golden tests**: fixed IR → fixed emission (relocation determinism)
- **Adversarial tests**:
  - scope imbalance
  - label/token collisions
  - forbidden cross-unit `$f/$e`
  - missing `$d` under different modes
  - dependency cycles or missing exports

---

## 11. Migration Plan (Recommended)

### 11.1 Step 0: Dual-track Output

- Retain `MMBuilder.render()` for toy demos
- Simultaneously build internal LIR (even if tokens are temporarily marked COMPAT)

### 11.2 Step 1: Version the Export Manifest

- Add `format_version`
- Add relocatable label references
- Allow string fallback only in COMPAT mode

### 11.3 Step 2: Introduce `import_theorem()` and `TheoremRef`

- Eliminate handwritten string labels across modules
- Transition dependency collection from `requires` to extracted `uses_assertions`

### 11.4 Step 3: Default-off Raw String Tokens (CI Shock Therapy)

- COMPAT must be explicit and allowlisted
- CI fails on accidental raw string token introduction

---

## 12. Appendix: Updated Toy Example (Illustrative)

*Interface-build style: declare a theorem API without emitting a fake `$p`.*

```python
from proof_scaffold.dsl import MMBuilder, expr
from proof_scaffold.imports import import_theorem
from proof_scaffold.export import export

mm = MMBuilder(profile="PROFILE_V3_LIR")

with mm.unit("sqrt2") as u:
    u.comment("Toy sqrt2 module (interface only)")
    u.c("|-","sqrt2","irrational")
    u.v("ph")
    u.f("wph","|-","ph")

    sqrt2irr = u.declare_theorem(
        label="sqrt2irr",
        typecode="|-",
        expr=expr("sqrt2", "irrational"),
        interface_only=True,
     )

export(
    module_id="number_theory.sqrt2",
    name="sqrt2_irrational",
    theorem=sqrt2irr,
    build_dir="build/mmdb",
)
```

This example demonstrates an *interface-only build*:
it exports a theorem API without emitting a verifiable `$p`.

Such builds are intended for dependency wiring and API stabilization,
and are explicitly excluded from CI verification paths.


