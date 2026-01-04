# Step 02 — Proofs as Stack Programs

In Step 01, we learned what *exists* in a Metamath database.

In this step, we learn something more important:

> **A Metamath proof is not a derivation tree.  
> It is a stack program.**

Understanding this single idea will resolve most early confusion
about Metamath.

---

## What You Should Learn in This Step

After completing this step, you should be able to:

- Read a Metamath proof as a sequence of stack operations
- Explain what each proof label *does* operationally
- Understand why proof order matters
- Recognize stack-related error messages from the verifier

This step still avoids logical inference.
We focus only on *execution mechanics*.

---

## The Fixture World

**Fixture:** `fixtures/sanity/02_stack_machine.mm`

This fixture extends the minimal database with a second variable.

You will see:

```mm
$c wff ( ) -> |- $.

$v ph ps $.

wph $f wff ph $.
wps $f wff ps $.

ax-1 $a |- ( ph -> ( ps -> ph ) ) $.
````

Compared to Step 01, the only conceptual change is:

> There are now **two variables**, and therefore **two mandatory typing hypotheses**.

This is enough to expose the stack nature of proofs.

---

## The Generated Proof

Run the companion program:

```bash
python tools/sanity/check_02_stack_machine.py --mmverify verifier/mmverify.py
```

The program generates a theorem equivalent to the axiom:

```mm
sanity.02 $p |- ( ph -> ( ps -> ph ) ) $=
  wph
  wps
  ax-1
$.
```

At first glance, this may look trivial.
But its execution is not.

---

## Executing the Proof Step by Step

Let us execute this proof as a stack program.

### Initial state

The stack is empty:

```
[]
```

---

### Step 1 — `wph`

```mm
wph
```

This is a `$f` label.

It **pushes** the typing hypothesis for `ph` onto the stack:

```
[(wff ph)]
```

---

### Step 2 — `wps`

```mm
wps
```

This is also a `$f` label.

It pushes the typing hypothesis for `ps`:

```
[(wff ph), (wff ps)]
```

---

### Step 3 — `ax-1`

```mm
ax-1
```

This is an `$a` (axiom) label.

Operationally, the verifier now:

1. **Pops mandatory `$f` entries**

   * `(wff ps)`
   * `(wff ph)`
2. Builds a substitution (trivial in this case)
3. **Pushes the conclusion**

Resulting stack:

```
[ |- ( ph -> ( ps -> ph ) ) ]
```

The proof is complete.

---

## Why Order Matters

If you change the proof order, the verifier will fail.

For example, this proof is invalid:

```mm
wps
wph
ax-1
```

Why?

Because `ax-1` expects its mandatory `$f` hypotheses in a specific order.
The stack is not symmetric.
Metamath does not reorder or guess.

This is your first encounter with a fundamental rule:

> **Metamath proofs are order-sensitive programs.**

---

## A Crucial Mental Shift

At this point, it is essential to let go of a common intuition:

* ❌ “A proof applies an axiom to assumptions.”
* ✅ “A proof executes a program that manipulates a stack.”

Logical meaning exists, but it is *encoded* in stack discipline,
not interpreted by the verifier.

---

## Typical Errors at This Stage

If something goes wrong here, you may see errors such as:

* `stack underflow`
  → Not enough items were pushed before applying an axiom.

* `mandatory var hyp mismatch`
  → The wrong stack item was used where a typing hypothesis was expected.

These errors are not bugs.
They are precise diagnostics of incorrect stack programs.

---

## Why This Step Matters

Step 02 is the foundation for everything that follows:

* mandatory `$f` hypotheses (Step 03)
* essential `$e` hypotheses (Step 04)
* inference rules
* automated proof generation

If you understand Metamath as a stack machine,
later concepts will feel mechanical rather than mysterious.

---

## What Comes Next

In the next step, we focus on **mandatory `$f` hypotheses** in isolation:

* Why they exist
* Why they must be supplied explicitly
* How the Python layer can compute them automatically

That is the focus of Step 03.
