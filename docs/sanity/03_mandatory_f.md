# Sanity 03 — Mandatory `$f` Hypotheses (Technical Notes)

This document explains the verifier-level mechanics validated
by the Step 03 sanity check.

It focuses on mandatory `$f` hypotheses as **typing constraints**
that must be satisfied before any assertion can be applied.

---

## Purpose of This Sanity Check

Step 03 validates that:

- multiple mandatory `$f` hypotheses are required for multi-variable assertions
- these hypotheses must be explicitly pushed onto the stack
- the verifier consumes `$f` hypotheses in a fixed, deterministic order
- the Python layer can correctly compute this order

No essential hypotheses (`$e`) are involved at this stage.

---

## Structure of the Fixture

**File:** `fixtures/sanity/03_mandatory_f.mm`

The fixture declares:

- two variables: `ph`, `ps`
- two typing hypotheses: `wph`, `wps`
- one axiom: `ax-1`

Because `ax-1` references both variables,
the verifier determines that **two `$f` hypotheses are mandatory**.

---

## Generated Proof

The companion program appends:

```mm
sanity.03 $p |- ( ph -> ( ps -> ph ) ) $=
  wph
  wps
  ax-1
$.
````

This proof contains no logical premises.
It exists solely to test `$f` handling.

---

## Verifier Execution Semantics

When processing `ax-1`, the verifier:

1. Identifies all variables used in the assertion
2. Determines the required `$f` hypotheses
3. Pops those hypotheses from the stack in order
4. Builds a substitution (trivial here)
5. Pushes the conclusion

If any `$f` hypothesis is missing or out of order,
verification fails immediately.

---

## Error Diagnostics

Typical failures at this step include:

* **`stack underflow`**
  → One or more mandatory `$f` hypotheses were not pushed.

* **`mandatory var hyp mismatch`**
  → `$f` hypotheses were pushed in the wrong order.

These errors indicate incorrect proof construction,
not incorrect logic.

---

## Role of the Python Layer

The Python helper:

```python
required_f_labels(db, "ax-1")
```

encodes the contract:

> Given an assertion label,
> return the exact sequence of mandatory `$f` labels
> required to apply that assertion.

This function does not perform inference.
It reflects verifier requirements.

---

## Relation to Other Steps

* **Compared to Step 02**:
  Step 02 shows that proofs are stack programs.
  Step 03 explains *what must be on the stack* before execution.

* **Before Step 04**:
  Step 04 introduces essential `$e` hypotheses,
  which are consumed *after* mandatory `$f`.

Understanding Step 03 is a prerequisite for understanding Step 04.
