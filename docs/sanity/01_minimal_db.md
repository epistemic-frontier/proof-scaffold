# Sanity 01 — Minimal Metamath Database (Technical Notes)

This sanity check validates the **structural minimum** required for a Metamath
database to support proofs.

Unlike Step 00, which only verifies toolchain connectivity,
this step begins to treat Metamath declarations as *semantic objects*.

---

## Purpose of This Sanity Check

Step 01 answers the question:

> What is the smallest set of declarations that makes proof verification possible?

It confirms that:

- constants (`$c`) must exist before they can be referenced
- variables (`$v`) must be declared before typing
- typing hypotheses (`$f`) are mandatory for any variable usage
- axioms (`$a`) can only be applied once their typing requirements are met

---

## Structure of the Fixture

**File:** `fixtures/sanity/01_minimal_db.mm`

The fixture contains exactly four kinds of declarations:

1. `$c` — declares the constant `wff` (the formula type)
2. `$v` — declares a single variable `ph`
3. `$f` — declares that `ph` has type `wff`
4. `$a` — declares a trivial axiom `|- ( ph -> ph )`

Each declaration is necessary.
Removing any one of them causes verification to fail.

---

## Generated Proof

The companion program generates the following `$p` block:

```mm
sanity.01 $p |- ( ph -> ph ) $=
  wph
  ax-id
$.
```