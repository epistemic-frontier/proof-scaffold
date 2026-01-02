# Step 06 — Scoped Assertions (`${ ... $}`)

**Milestone:** M0.2
**Focus:** Label visibility and scoped blocks
**Out of scope:** `$d` constraints, advanced dependency pruning, modular imports

---

## 1. Motivation

As Metamath projects grow, it becomes essential to define **local assumptions and intermediate lemmas** without polluting the global namespace.

Metamath provides a scoped block mechanism:

```mm
${
  ... local declarations ...
$}
```

This step validates the most basic and critical property of scoped blocks:

> **Labels declared inside a block are not visible outside the block.**

Step 06 deliberately avoids more advanced semantics and focuses on **scope correctness only**.

---

## 2. Core Semantics

### 2.1 Label Visibility

* Any label declared inside a `${ ... $}` block (`$f`, `$e`, `$a`, `$p`) is:

  * **Visible only within that block**
  * **Not accessible after `$}`**

* Labels declared outside a block **are visible inside** the block.

This is standard lexical scoping.

---

### 2.2 Dynamic `$e` Hypotheses (Critical Detail)

A common source of confusion:

> `${ ... $}` controls **label visibility only**.
> It does **not** reset or isolate the active `$e` hypotheses.

Concretely:

* All `$e` statements that are active **before entering a block**
  remain active **inside the block**.
* Any `$a` or `$p` defined inside the block will include **all active `$e`**
  (outer + inner) as **mandatory hypotheses**.

This behavior is mandated by Metamath and is faithfully implemented in `mmverify.py`.

---

## 3. Canonical Happy Path (`06_scope_happy.mm`)

The following example is **minimal, correct, and stable**:

```mm
$( 06_scope_happy.mm — scoped block is well-formed and non-leaking. $)

$c wff ( ) -> $.
$v ph ps $.

wph $f wff ph $.
wps $f wff ps $.

${
  $( Local hypotheses + local MP axiom + local theorem. $)
  l1 $e wff ph $.
  l2 $e wff ( ph -> ps ) $.
  ax-mp-local $a wff ps $.

  tlocal $p wff ps $=
    wph wps l1 l2 ax-mp-local
  $.
$}

${
  $( Global MP hypotheses + global MP axiom. $)
  g1 $e wff ph $.
  g2 $e wff ( ph -> ps ) $.
  ax-mp $a wff ps $.

  $( Outside the block: prove using the global MP axiom. $)
  th_out $p wff ps $=
    wph wps g1 g2 ax-mp
  $.
$}
```

### Why this works

* When `tlocal` is defined:

  * No outer `$e` hypotheses are active
  * Its mandatory hypotheses are exactly: `ph ps l1 l2`
* All block-local labels (`l1`, `l2`, `ax-mp-local`, `tlocal`) are hidden after `$}`
* The global theorem `th_out` uses only global hypotheses and axioms

This is the **reference pattern** for scoped usage.

---

## 4. Scope Leakage (`06_scope_leakage.mm`)

This example must **fail**, because it violates label visibility:

```mm
$( 06_scope_leakage.mm — reference a block-local label outside its scope (must fail). $)

$c wff -> $. 
$v ph ps $.

ph $f wff ph $.
ps $f wff ps $.

${
  l1 $e wff ph $.
  l2 $e wff ( ph -> ps ) $.
  ax-mp-local $a wff ps $.

  tlocal $p wff ps $=
    ph ps l1 l2 ax-mp-local
  $.
$}

$( Must FAIL: tlocal is not visible here. $)
th_bad $p wff ps $=
  tlocal
$.
```

### Expected failure

* Error type: **undefined label / unknown label**
* This is the *intended* signal for Step 06

> Note: No `$e` statements appear before the block.
> This is intentional, to ensure the failure is due to **scope**, not stack mismatch.

---

## 5. Unbalanced Block (`06_scope_unbalanced.mm`)

Blocks must be properly closed.

```mm
$( 06_scope_unbalanced.mm — missing closing $} must cause parse failure. $)

$c wff -> $. 
$v ph ps $.

ph $f wff ph $.
ps $f wff ps $.

${
  l1 $e wff ph $.
  l2 $e wff ( ph -> ps ) $.
  ax-mp-local $a wff ps $.

  tlocal $p wff ps $=
    ph ps l1 l2 ax-mp-local
  $.
  $( Intentionally missing $} here. $)
```

### Expected failure

* Parse error (unexpected EOF or unbalanced block)

---

## 6. Technical Notes (for Implementers)

### 6.1 Mandatory Hypotheses Rule

For any `$a` or `$p`:

```
mandatory hypotheses =
  all relevant $f
  + all currently active $e (outer + inner)
```

Scoped blocks **do not** alter this rule.

---

### 6.2 Common Failure Modes

#### Stack underflow

* Proof supplies fewer items than mandatory hypotheses
* Often caused by forgetting inherited `$e`

#### Stack has >1 entry at end

* Rule does not consume inputs (e.g. missing `$e`)
* Leaves residual stack items

#### Undefined label

* Correct failure mode for Step 06
* Indicates a genuine scope violation

---

### 6.3 Engineering Guideline (Strongly Recommended)

> **Do not place `$e` statements before a scoped block unless you explicitly want them inherited.**

This keeps:

* Local theorems minimal and predictable
* Sanity tests precise and unambiguous

---

## 7. Summary

* `${ ... $}` enforces **label visibility**, not semantic isolation
* `$e` hypotheses form a **dynamic environment**
* Step 06 validates scope correctness only
* Correct tests must isolate scope errors from stack errors
