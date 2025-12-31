# Step 03 — Mandatory `$f` Hypotheses

In Step 02, we learned that a Metamath proof is a **stack program**.

In this step, we focus on one specific kind of stack element:

> **Mandatory `$f` hypotheses are typing requirements that must always be provided,
> even when no logical reasoning is involved.**

This step explains *why* `$f` exists and *why it cannot be skipped*.

---

## What You Should Learn in This Step

After completing this step, you should understand:

- What mandatory `$f` hypotheses represent
- Why they are required before applying any assertion
- Why their order matters
- How they can be computed automatically by the Python layer

This step introduces **no new logic**.
It is about enforcing structure.

---

## The Fixture World

**Fixture:** `fixtures/sanity/03_mandatory_f.mm`

This fixture introduces the smallest situation in which `$f` becomes non-trivial:

```mm
$v ph ps $.

wph $f wff ph $.
wps $f wff ps $.

ax-1 $a |- ( ph -> ( ps -> ph ) ) $.
````

The key difference from earlier steps is:

> The axiom now mentions **two variables**, and therefore requires **two `$f` hypotheses**.

---

## Why `$f` Is Mandatory

The axiom `ax-1` mentions both `ph` and `ps`.

In Metamath, this means:

* `ph` must have a declared type
* `ps` must have a declared type

These typing requirements are *not optional*.
They are not inferred.
They are not implicit.

They must appear explicitly in the proof.

---

## Running the Companion Program

Run the sanity check:

```bash
python tools/sanity/check_03_mandatory_f.py --mmverify verifier/mmverify.py
```

You should see:

```
SANITY 03 OK
```

The generated proof looks like this:

```mm
sanity.03 $p |- ( ph -> ( ps -> ph ) ) $=
  wph
  wps
  ax-1
$.
```

---

## Reading the Proof

Read this proof as a stack program:

1. `wph`
   Pushes `(wff ph)`.

2. `wps`
   Pushes `(wff ps)`.

3. `ax-1`
   Consumes both typing hypotheses and pushes the conclusion.

Nothing logical happens here.
Only *typing requirements* are enforced.

---

## Why Order Matters

If you swap the order:

```mm
wps
wph
ax-1
```

The proof fails.

Metamath does not reorder stack entries.
It does not guess.
It checks the stack exactly as given.

This leads to an important rule:

> **Mandatory `$f` hypotheses must be provided in the exact order expected
> by the assertion.**

---

## Automation Insight

Manually writing `$f` labels is tedious and error-prone.

In this project, the Python layer computes mandatory `$f` labels automatically:

```python
required_f_labels(db, "ax-1")  # -> ["wph", "wps"]
```

This is the first place where the Python layer
adds value *without changing the underlying logic*.

---

## Why This Step Matters

Mandatory `$f` hypotheses are the backbone of Metamath’s discipline.

They ensure that:

* every variable is well-typed
* proofs are structurally explicit
* no hidden assumptions exist

Once `$f` is understood as a mandatory stack requirement,
many later Metamath behaviors become predictable.

---

## What Comes Next

In the next step, we introduce **essential `$e` hypotheses**.

Unlike `$f`, `$e` represents premises that may or may not be consumed,
depending on the assertion being applied.

Understanding the difference between `$f` and `$e`
is crucial for real inference.
