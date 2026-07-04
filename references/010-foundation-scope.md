# Foundation Scope v1

> Status: Draft, accepted direction for the next refactor round.
>
> Scope: package roles, dependency export semantics, and linker handling for the
> global Metamath foundation frame.

---

## 0. Decision

ProofScaffold supports one distinguished **Foundation Unit** in a build closure.
In the standard stack this unit is `metamath-prelude`.

The foundation unit is not modeled as an ordinary reusable library package. It
contributes the ambient Metamath frame that later packages build inside:

- global constants and variables used by the base logic;
- global floating hypotheses (`$f`) for schema variables;
- primitive syntax axioms that make formulas well-formed.

Ordinary packages remain normal dependency units. They may export vocabulary and
assertions, but they must not leak local `$f` or `$e` hypotheses across package
boundaries.

---

## 1. Motivation

The current implementation already behaves like a global foundation system:

- `metamath-prelude` is built as a dependency of `metamath-logic`;
- the emitted monolith leaves prelude declarations and floating hypotheses in a
  global frame;
- later proofs can use prelude `$f` labels such as `wph` and `wps`;
- Stage 1 currently treats all exported labels uniformly, which obscures the
  difference between exported assertions and ambient foundation hypotheses.

This document turns that implicit behavior into an explicit contract so the
prelude/logic split can be refactored without changing the Metamath verifier
semantics or weakening ProofScaffold's package boundaries.

---

## 2. Terms

- **Foundation Unit**: the unique package in a build closure that provides the
  ambient Metamath base frame. Standard name: `metamath-prelude`.
- **Library Unit**: an ordinary package that extends the theory with syntax,
  axioms, definitions, and theorems.
- **Application Unit**: an ordinary package that consumes libraries to prove
  project-specific results.
- **Foundation Frame**: the top-level Metamath scope emitted by the foundation
  unit.
- **Ambient Hypothesis**: a foundation-owned `$f` label that remains available
  in later statements because it lives in the foundation frame.
- **Vocabulary Export**: an exported `Const` or `Var` symbol used for authoring
  and formula construction.
- **Assertion Export**: an exported `$a` or `$p` label usable as a proof step by
  downstream packages.
- **Internal Hypothesis**: a non-foundation `$f` or `$e` label. It belongs to the
  unit that declares it and is not a dependency API.

---

## 3. Invariants

**F1. Single foundation.** A linked build closure may contain at most one
foundation unit. The standard foundation is `metamath-prelude`.

**F2. Foundation links first.** If present, the foundation unit is emitted before
all ordinary units, regardless of later topo-sort tie-breaks.

**F3. Foundation frame is top-level.** The foundation's declarations and
foundation-owned `$f` labels are emitted in the global Metamath frame.

**F4. Ordinary packages do not leak hypotheses.** Cross-unit references to
ordinary package `$f` or `$e` labels are invalid, even if the package called
`mm.export(...)` on those labels.

**F5. Foundation `$f` is special by ownership, not by syntax.** A `$f` label may
be used cross-unit only when its owning unit is the foundation unit.

**F6. Assertion imports stay explicit.** Cross-unit `$a` and `$p` proof
references are allowed only through assertion exports of declared dependencies.

**F7. Vocabulary imports are authoring support.** Exported constants and
variables may be read from `ctx.deps` so downstream packages can construct
SymbolId-level formulas, but a vocabulary export is not a proof reference.

**F8. `.mm` stays canonical.** The linked monolith remains ASCII canonical.
Unicode is an authoring/display concern handled before emission.

---

## 4. Standard Package Boundary

### 4.1 `metamath-prelude`

`metamath-prelude` should contain only the foundation mechanics needed before
ordinary logic packages begin:

- base typecodes: `wff`, `|-`;
- primitive syntax constants: `(`, `)`, `-.`, `->`;
- schema variables used by early logic: `ph`, `ps`, `ch`, `th`, ...;
- global floating hypotheses for those schema variables: `wph`, `wps`, ...;
- primitive syntax axioms: `wn`, `wi`.

These symbols exist to create the global frame in which later propositional
logic is authored and verified.

### 4.2 `metamath-logic`

`metamath-logic` should own ordinary propositional logic content:

- logical axioms such as `ax-mp`, `ax-1`, `ax-2`, `ax-3`;
- derived syntax beyond the foundation minimum, including `wo`, `wtru`, `wfal`;
- proof helper theorems such as `idi` and `a1ii`;
- later derived theorems, registries, and catalogues.

`wo`, `wtru`, and `wfal` are not foundation mechanics. They are ordinary syntax
extensions over the foundation frame and should move from `metamath-prelude` to
`metamath-logic`.

`idi` and `a1ii` are also not foundation mechanics. They use local essential
hypotheses and should live in `metamath-logic`, unless a separate compatibility
goal explicitly requires `metamath-prelude` to mirror a particular set.mm prefix.

---

## 5. Export Semantics

The current public API may remain:

```python
ExportsView = Mapping[str, SymbolId]
```

The linker must still classify exported symbols by their defining statement:

- `Const` / `Var` -> vocabulary export;
- foundation-owned `FloatingHyp` -> ambient foundation hypothesis;
- `Axiom` / `Theorem` -> assertion export;
- ordinary `FloatingHyp` / `EssentialHyp` -> internal hypothesis, not importable.

This classification can be implemented without changing the authoring-facing
`ctx.deps[...]` shape in the first refactor slice. A later API may expose a
structured export object if it removes ambiguity.

---

## 6. Linker Behavior

### 6.1 Discovery and metadata

The driver should identify package kind before linking:

- `foundation`;
- `library`;
- `application`.

Short-term detection may special-case `metamath-prelude`. Long-term package kind
should be declared in package metadata or ProofScaffold config.

### 6.2 Stage 1 access control

Stage 1 should enforce:

- proof tokens that reference dependency assertions must resolve to exported
  `$a` or `$p` labels;
- proof tokens may reference foundation-owned `$f` labels;
- proof tokens must not reference ordinary package `$f` or `$e` labels;
- math tokens may reference dependency vocabulary exports;
- diagnostics should distinguish "not exported", "hypothesis leakage", and
  "wrong export class".

### 6.3 Stage 5 scope emission

Foundation scope emission is intentionally different from ordinary unit scope
emission:

- foundation statements are emitted at top level;
- ordinary units are emitted inside an outer `${ ... $}` frame;
- ordinary units may still contain nested authoring scopes;
- ordinary local hypotheses do not become dependency APIs after the ordinary
  unit frame closes.

---

## 7. Builder and Authoring Behavior

BuilderV2 remains responsible for constructing well-scoped LIR from SymbolIds.
Foundation scope does not make the builder a Metamath verifier.

Authoring rules:

- ordinary packages should obtain foundation vocabulary and ambient `$f` labels
  through `ctx.deps["metamath-prelude"]` or `ctx.deps.prelude`;
- ordinary packages may create local `$e` hypotheses for a theorem block, but
  must not export them as reusable package API;
- auto-`$f` remains a local authoring convenience and should not silently create
  a second copy of foundation schema floating hypotheses when the package is
  intentionally using the foundation frame.

---

## 8. Migration Notes

The next refactor should perform these package moves:

1. Keep `wff`, `|-`, `(`, `)`, `-.`, `->`, schema variables, global `$f`,
   `wn`, and `wi` in `metamath-prelude`.
2. Move `wo`, `wtru`, and `wfal` to `metamath-logic`.
3. Move `idi` and `a1ii` to `metamath-logic`.
4. Update tests/goldens so downstream references still verify through the
   transient monolith.
5. Update package docs so `metamath-prelude` is documented as foundation, not as
   a broad propositional-logic library.

---

## 9. Open Questions

1. Where should package kind be declared: `pyproject.toml`, `.skfd`, or a small
   `proof_scaffold.toml` package manifest?
2. Should structured exports become public in BuilderV2 v1, or stay an internal
   linker index until the next API revision?
3. Should ordinary unit scope wrapping become mandatory in Stage 5 immediately,
   or first land as a strict-mode diagnostic?
