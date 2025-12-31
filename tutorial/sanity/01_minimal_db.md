# Step 01 — The Minimal Metamath Database

In Step 00, we confirmed that the Metamath verifier is reachable and functional.

In this step, we answer a more fundamental question:

> **What is the smallest “world” in which a Metamath proof can exist?**

This is not about logic yet.
It is about *structure*.

---

## What You Should Learn in This Step

After completing this step, you should understand:

- What kinds of declarations a Metamath database must contain
- Why none of them can be omitted
- Why Metamath proofs depend on *declared structure*, not intention

At the end of this step, you will have a concrete mental model of
what “exists” before any proof is even possible.

---

## The Minimal Database

**Fixture:** `fixtures/sanity/01_minimal_db.mm`

Open the file and read it top to bottom.

You will see exactly four kinds of declarations:

```mm
$c wff ( ) -> |- $.
$v ph $.
wph $f wff ph $.
ax-id $a |- ( ph -> ph ) $.
````

Nothing more.
Nothing less.

Each line answers a different question.

---

## `$c` — What Symbols Exist?

```mm
$c wff ( ) -> |- $.
```

This line declares *constants*.

In Metamath, **nothing exists unless it is declared**.
Even basic-looking tokens such as `wff` or `->` must be introduced explicitly.

At this stage, you do not need to care what `wff` or `->` “mean”.
You only need to accept this rule:

> If a symbol is not declared by `$c`, it cannot appear anywhere else.

---

## `$v` — What Variables Exist?

```mm
$v ph $.
```

This line declares a variable named `ph`.

Again, Metamath is explicit:
variables do not exist implicitly.

You cannot write `ph` in a proof unless it has been declared by `$v`.

---

## `$f` — What Is the Type of a Variable?

```mm
wph $f wff ph $.
```

This line is often misunderstood, so read it carefully.

It does **not** assert a logical fact.
It does **not** say “`ph` is true”.

It only states:

> “The variable `ph` has type `wff`.”

In Metamath, typing is *mandatory*.
Any use of `ph` in a statement requires this typing hypothesis to be available.

There is no implicit typing.
There is no default.

---

## `$a` — What Is an Axiom?

```mm
ax-id $a |- ( ph -> ph ) $.
```

This line introduces an axiom.

For now, you can treat an axiom as:

> “A statement that may be used in a proof, provided all its requirements are met.”

Even this axiom is not free to use:
because it mentions `ph`, it *implicitly requires* the typing hypothesis declared earlier.

---

## Running the Companion Program

Now run the sanity check for this step:

```bash
python tools/sanity/check_01_minimal_db.py --mmverify verifier/mmverify.py
```

If everything is correct, you should see:

```
SANITY 01 OK
```

What just happened?

The program appended a new theorem:

```mm
sanity.01 $p |- ( ph -> ph ) $=
  wph
  ax-id
$.
```

This theorem does not introduce new logic.
It only confirms that the database structure is complete and consistent.

---

## What This Proof Really Demonstrates

This proof demonstrates one crucial fact:

> **A Metamath proof cannot exist without explicit structure.**

Even the most trivial statement requires:

* declared symbols
* declared variables
* declared typing
* declared axioms

Nothing is assumed.
Nothing is inferred automatically.

---

## Common Misconceptions

* “This is trivial, so Metamath should allow it without all this boilerplate.”
  → Metamath does not reason about intent. It checks structure.

* “Typing is just a formality.”
  → Typing is a mandatory hypothesis, not a comment.

* “The proof is boring.”
  → The *proof* is boring; the *mechanism* is not.

---

## Why This Step Matters

Before learning how proofs *execute* (next step),
you must first understand **what a Metamath world consists of**.

Step 01 establishes that world.

Only after this foundation is clear does it make sense to ask
how proofs run, how stacks evolve, or how hypotheses are consumed.

That is the focus of Step 02.
