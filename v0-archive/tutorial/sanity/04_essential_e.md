# Step 04 — Essential `$e` Hypotheses

In the previous steps, we learned that Metamath proofs execute as stack programs,
and that typing hypotheses (`$f`) must be provided explicitly and in the correct order.

In this step, we introduce a second and often misunderstood concept:

> **Essential hypotheses (`$e`) are not “assumptions”.  
> They are concrete stack objects that must be explicitly consumed.**

This step resolves one of the most common sources of confusion for new Metamath users.

---

## What You Should Learn in This Step

After completing this step, you should understand:

- What `$e` hypotheses really are in Metamath
- How `$e` differs from `$f`
- Why `$e` does nothing unless an assertion explicitly depends on it
- Why `$f` must still appear *before* `$e` in a proof

This step introduces no real logic.
Its purpose is purely mechanical.

---

## The Fixture World

**Fixture:** `fixtures/sanity/04_essential_e.mm`

Open the file and read it carefully.

```mm
$c wff |- $.

$v ph $.

wph $f wff ph $.

hph $e |- ph $.

id-e $a |- ph $.
````

At first glance, this may look strange:

* The hypothesis states `|- ph`
* The axiom also states `|- ph`

Why introduce both?

Because this fixture is not about logic.
It is about *how hypotheses are consumed*.

---

## The Key Idea

In informal mathematics, we often say:

> “Assume `ph`, then derive something.”

In Metamath, this idea does **not** exist.

Instead:

* `$e` introduces a **stack object**
* An assertion (`$a` or `$p`) may or may not require that object
* Only assertions that explicitly depend on `$e` will consume it

If no assertion consumes an `$e`, it remains on the stack and breaks the proof.

---

## Running the Companion Program

Run the sanity check:

```bash
python tools/sanity/check_04_essential_e.py --mmverify verifier/mmverify.py
```

You should see:

```
SANITY 04 OK
```

Note: the fixture already embeds the minimal proof inside the local scope as:

```mm
sanity.e1 $p |- ph $=
  wph hph id-e
$.
```

The sanity script verifies the fixture as-is; it does not generate an extra theorem.

---

## Reading the Proof as a Stack Program

Let us execute this proof step by step.

### Step 1 — `wph`

Push the mandatory typing hypothesis:

```
[(wff ph)]
```

---

### Step 2 — `hph`

Push the essential hypothesis:

```
[(wff ph), (|- ph)]
```

---

### Step 3 — `id-e`

Apply the assertion.

Operationally, the verifier:

1. Pops mandatory `$f` hypotheses (typing)
2. Pops essential `$e` hypotheses (premises)
3. Pushes the conclusion

Final stack:

```
[ |- ph ]
```

The proof succeeds.

---

## Why Order Still Matters

If you reverse the order:

```mm
hph
wph
id-e
```

The verifier will fail.

Why?

Because `id-e` first expects a typing hypothesis (`$f`),
but instead encounters an essential hypothesis (`$e`).

This reinforces a rule already seen in earlier steps:

> **Mandatory `$f` hypotheses must always appear before `$e` hypotheses.**

---

## Why This Step Matters

This step establishes a crucial mental model:

* `$e` is not context
* `$e` is not an assumption in the human sense
* `$e` is a stack object that must be explicitly consumed

Once this is understood, later concepts such as inference rules,
modus ponens, and scoped hypotheses become mechanical.

---

## What Comes Next

With `$f` and `$e` understood as stack elements,
we are now ready to introduce *real inference rules*.

The next step will show how multiple `$e` hypotheses are consumed together
to perform logical inference.

That is the beginning of actual reasoning.
