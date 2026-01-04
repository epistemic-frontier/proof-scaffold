# Sanity 02 — Proofs as Stack Programs (Technical Notes)

This sanity check validates the operational model of Metamath proofs:
**a proof is a stack program executed by the verifier**.

Unlike Step 01, this step is not about database structure.
It is about execution order.

---

## Purpose of This Sanity Check

Step 02 verifies that:

- multiple mandatory `$f` hypotheses are handled correctly
- proof labels are executed strictly in sequence
- the verifier consumes stack entries in a fixed order

This step introduces no `$e` hypotheses and no inference rules.
Its sole focus is stack discipline.

---

## Structure of the Fixture

**File:** `fixtures/sanity/02_stack_machine.mm`

The fixture declares:

- two variables: `ph`, `ps`
- two typing hypotheses: `wph`, `wps`
- one axiom: `ax-1`

The axiom references both variables, which makes the stack behavior observable.

---

## Generated Proof

The companion program appends the following `$p` statement:

```mm
sanity.02 $p |- ( ph -> ( ps -> ph ) ) $=
  wph
  wps
  ax-1
$.
````

---

## Verifier Execution Trace

The verifier processes the proof as follows:

1. `wph`
   Push `(wff ph)` onto the stack.

2. `wps`
   Push `(wff ps)` onto the stack.

   Stack now contains two entries.

3. `ax-1`

   * Pop mandatory `$f` hypotheses in the required order.
   * Build a substitution (trivial in this case).
   * Push the conclusion `|- ( ph -> ( ps -> ph ) )`.

After this step, the stack contains exactly one entry,
which must match the target statement.

---

## Why This Matters

This sanity check establishes a critical invariant:

> **Proof order is semantic.**

Metamath does not reorder stack entries.
It does not infer missing hypotheses.
It executes exactly the sequence of labels it is given.

Understanding this makes later steps mechanical rather than mysterious.

---

## Failure Modes

Common errors at this step include:

* `stack underflow`
  → Not enough `$f` entries were pushed before applying the axiom.

* `mandatory var hyp mismatch`
  → `$f` entries were pushed in the wrong order.

Such errors indicate incorrect stack programs, not logical mistakes.

---

## Relation to Other Steps

* **Compared to Step 01**:
  Step 01 establishes *what exists*; Step 02 establishes *how execution works*.

* **Before Step 03**:
  Step 03 builds on this model to explain why `$f` hypotheses are mandatory
  and how they can be computed automatically.
