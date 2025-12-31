# Sanity 04 — Essential `$e` Hypotheses (Technical Notes)

This document explains, at the verifier level, what is being validated
by the Step 04 sanity check.

It focuses exclusively on `$e` hypotheses as part of the stack execution model.

---

## Purpose of This Sanity Check

Step 04 validates that:

- essential hypotheses (`$e`) are treated as explicit stack entries
- assertions consume `$e` hypotheses only if they are declared as dependencies
- mandatory `$f` hypotheses are always consumed before `$e` hypotheses

No logical inference is tested.
Only stack discipline is validated.

---

## Structure of the Fixture

**File:** `fixtures/sanity/04_essential_e.mm`

The fixture contains:

- one variable (`ph`)
- one typing hypothesis (`wph`)
- one essential hypothesis (`hph`)
- one assertion (`id-e`) declared in the same scope

Because `id-e` is declared in the presence of `hph`,
the verifier treats `hph` as an essential hypothesis of `id-e`.

This dependency is computed by the verifier, not inferred by the proof.

---

## Generated Proof

The companion program appends:

```mm
sanity.04 $p |- ph $=
  wph
  hph
  id-e
$.
````

This proof is intentionally minimal.

---

## Verifier Execution Semantics

When processing `id-e`, the verifier:

1. Collects mandatory `$f` hypotheses based on variables used in the assertion
2. Collects essential `$e` hypotheses based on scope
3. Requires the proof stack to contain, in order:

   * mandatory `$f` entries
   * essential `$e` entries

If the stack does not match this structure exactly, verification fails.

---

## Common Failure Modes

* **`mandatory var hyp mismatch`**
  → A `$e` entry was encountered where a `$f` entry was expected.

* **`stack underflow`**
  → One or more required hypotheses were not pushed before applying the assertion.

These errors indicate incorrect stack programs, not incorrect logic.

---

## Relation to Other Steps

* **Compared to Step 03**:
  Step 03 focuses on mandatory typing hypotheses (`$f`).
  Step 04 adds essential hypotheses (`$e`) and their consumption.

* **Before inference rules**:
  Understanding `$e` is required before introducing rules such as modus ponens,
  which consume multiple essential hypotheses.

This step completes the foundational model of Metamath proof execution.