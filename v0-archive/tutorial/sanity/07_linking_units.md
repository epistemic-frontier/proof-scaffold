# Step 07 — Linking Multiple Units ($[ ... $])

Milestone: M0.2
Focus: include ($[ ... $]) across small units; exported vs non-exported labels; simple cycle case

---

## What you will learn

- How to split a minimal Metamath world into small units and include them
- What can be referenced across units (exported $a/$p only)
- Why cycles across units must be rejected (by the linker/pipeline)
- Why includes should be placed at the top level (per linter constraints)

This step deliberately keeps logic minimal so the “linking shape” is easy to see.

---

## The fixtures

We use three fixtures under fixtures/sanity/:

1) 07_two_units_happy.mm — happy path, two units link and verify

```
$( Step 07 - two units link in correct order and verify. $)

$c wff ( ) -> $.
$v ph ps $.

wph $f wff ph $.
wps $f wff ps $.

$( Include MP unit providing an exported axiom, and a unit that proves a theorem using it. $)
$[ fixtures/sanity/07_unit_mp.mm $]
$[ fixtures/sanity/07_unit_thm.mm $]
```

The two included units are:

- 07_unit_mp.mm (exports a simple axiom):
```
$( Unit providing a simple axiom ax-mp at top-level. $)

ax-mp $a wff ps $.
```

- 07_unit_thm.mm (uses the exported axiom to prove a theorem):
```
$( Unit defining a theorem using ax-mp exported by another unit. $)

${
  t_from_units $p wff ps $=
    wps ax-mp
  $.
$}
```

Notes:
- We keep ax-mp minimal (no $e) so the cross-unit dependency is very clear: the theorem unit only consumes its local mandatory $f (wps) and the imported axiom label.
- The theorem is defined inside a local block to illustrate local label scoping (although here it exports a single theorem label).
- Includes appear at the top level, matching metamath-knife’s constraints.

2) 07_cycle.mm — cycle across units (must fail)

```
$( Step 07 — dependency cycle between two units (should be rejected by linker once gate exists). $)

$c wff ( ) -> $.
$v ph ps $.

wph $f wff ph $.
wps $f wff ps $.

${
  $[ 07_unit_a_cycle.mm $]
  $[ 07_unit_b_cycle.mm $]
$}
```

A and B mutually reference each other’s theorem labels. The semantic verifiers reject it.

3) 07_non_exported_label_ref.mm — reference a non-exported label (must fail)

```
$( Step 07 — non-exported label reference should fail early. $)

$c wff ( ) -> $.
$v ph ps $.

wph $f wff ph $.
wps $f wff ps $.

${
  $[ 07_unit_private.mm $]
$}

$( Attempt to use a private/internal label from another unit — invalid. $)
use_private $p wff ps $=
  priv_helper
$.
```

The included unit declares a helper label `priv_helper` that is not meant for external references. Using it outside should fail.

---

## How to run

- Run the individual tests (recommended):

```
python -m pytest -q tests/test_sanity_m02.py::test_07_two_units_link_and_verify
python -m pytest -q tests/test_sanity_m02.py::test_07_cycle_is_detected
python -m pytest -q tests/test_sanity_m02.py::test_07_non_exported_label_reference_fails_early
```

- Or run the full suite for M0.2:

```
python -m pytest -q
```

---

## Takeaways

- Only exported $a/$p labels are usable across unit boundaries; $f/$e are local to definition sites and scopes.
- Includes should be top-level to satisfy the linter; units themselves can open local blocks internally when needed.
- Dependency cycles across units are invalid and should be rejected by the build/link pipeline; the semantic verifiers also refuse the resulting database.

With this step, you have a minimal but concrete picture of how small Metamath units can be assembled into a working database, and what visibility rules apply across unit boundaries.
