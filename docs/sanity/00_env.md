# Sanity 00 — Environment and Verifier (Technical Notes)

This document explains **what is being validated at the mechanism level** by
the Step 00 sanity check, and why this check exists as a permanent anchor
in the ProofScaffold workflow.

This is not an introduction to Metamath logic.
It is an explanation of the *execution boundary* between our Python layer
and the Metamath verifier.

---

## Purpose of This Sanity Check

Step 00 validates the **existence and stability of the verification pipeline**.

Specifically, it answers the question:

> Can a Metamath database be extended programmatically and
> successfully verified by the external verifier?

Nothing else is tested at this stage.

If this step fails, all subsequent tutorial steps are meaningless,
because the final judge (the verifier) cannot be reached.

---

## What Is *Not* Being Tested

This sanity check deliberately avoids testing:

- logical inference
- proof search
- `$f` / `$e` semantics beyond the absolute minimum
- stack discipline beyond a single mandatory hypothesis

Any failure here should be interpreted as an **environmental or integration problem**,
not as a misunderstanding of Metamath theory.

---

## Structure of the Fixture

**File:** `fixtures/sanity/00_env.mm`

The fixture defines the smallest Metamath world that still admits a valid proof:

- `$c`: declares the constant `wff`
- `$v`: declares a single variable `ph`
- `$f`: declares the typing hypothesis `wph : wff ph`
- `$a`: declares a trivial axiom `ax-id : |- ( ph -> ph )`

There is **no `$p`** in the fixture.
This is intentional: the proof is generated externally by the Python layer.

The fixture exists solely to define an object-level context.

---

## Structure of the Generated Proof

The companion program (`check_00_env.py`) appends a single `$p` statement:

```mm
sanity.00 $p |- ( ph -> ph ) $=
  wph
  ax-id
$.
````

This proof sequence demonstrates the minimal stack interaction:

1. `wph`
   Pushes the mandatory typing hypothesis `(wff ph)` onto the stack.

2. `ax-id`
   Consumes the mandatory `$f` entry and pushes the conclusion
   `|- ( ph -> ph )`.

The proof contains no essential hypotheses (`$e`) and no substitutions
beyond the trivial one.

---

## Why This Is Sufficient

From the verifier’s perspective, this sequence confirms that:

* The verifier can read a database from standard input.
* `$f` hypotheses are correctly interpreted and consumed.
* A generated `$p` can be checked against an existing `$a`.
* The verifier exits normally when the proof is valid.

From the framework’s perspective, this establishes that:

> The Python layer can construct object-level evidence
> and submit it to the trusted verifier without interference.

---

## Failure Modes and Their Meaning

Typical failures at this step include:

* **Verifier not found / not executable**
  → Incorrect `--mmverify` path or environment setup.

* **Process hangs**
  → Verifier expects input from standard input but none is provided.

* **`const in $f not defined`**
  → Fixture is missing a required `$c` declaration (e.g. `wff`).

* **`stack underflow`**
  → Mandatory `$f` was not pushed before applying the axiom.

All of these indicate integration or fixture issues, not logical errors.

---

## Role in the Overall Design

Step 00 is intentionally trivial and intentionally permanent.

It serves as:

* the lowest-level regression test
* a smoke test for the verifier interface
* a guarantee that higher-level reasoning failures are *semantic*, not infrastructural

Every future development step implicitly depends on this one.

If Step 00 fails, the correct response is to fix the environment,
not to adjust later tutorial logic.
