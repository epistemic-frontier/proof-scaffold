# ProofScaffold Tutorial

This tutorial is an **executable introduction to Metamath** — and to the minimal
**build → emit → verify** loop that ProofScaffold is built around.

It is designed for readers who want to understand **how Metamath proofs actually work** —
not just as symbolic logic, but as a concrete, verifiable *mechanism* — and how to
build higher-level proof workflows on top of that mechanism.

The tutorial is self-contained: every conceptual step is paired with a runnable
sanity check and is validated against a trusted Metamath verifier.

---

## Start Here: M0.1 Minimal Pipeline Sanity (Non-Negotiable)

Before learning any Metamath mechanics, you should make sure the toolchain is alive.

**M0.1 contract:**
A clean checkout must be able to run a single command that:

1) constructs a minimal `.mm` artifact (from a fixture or a generator),
2) invokes a trusted Metamath verifier from Python,
3) returns success (exit code 0).

If this fails, nothing else matters: fix the environment first.

### Quickstart

From the repository root:

```bash
# 1) (Recommended) create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2) install the package in editable mode
pip install -U pip
pip install -e .

# 3) run the minimal pipeline sanity check
python tools/sanity/check_00_env.py
````

**What “success” means:**

* the script finishes without exceptions,
* a minimal Metamath stream/database is generated (often written under `build/`),
* the verifier accepts it.

**What “failure” means:**

* missing dependencies / Python import errors,
* verifier cannot be invoked,
* verifier rejects the emitted `.mm` stream.

All three are actionable and are part of the lesson.

### Verifier backends (trusted boundary)

The tutorial’s ground truth is the verifier’s decision, not Python’s opinion.

This repository ships verifier tooling under `verifier/` (e.g. a Python verifier wrapper
and/or an external verifier tool). The sanity checks use that boundary:
**Python is the builder; the verifier is the authority.**

---

## How to Read This Tutorial

This tutorial is meant to be read **in order**.

Each step introduces exactly one new idea and is accompanied by:

* a minimal Metamath fixture (`.mm`)
* a Python companion program (`check_*.py`)
* a human-facing explanation of what happens during verification

You are encouraged to **run the code as you read**.

If something fails, the error messages are not incidental — they are part of the lesson.

---

## How to Run

### Run a single step

Each step has a runnable script:

```bash
python tools/sanity/check_<NN>_<name>.py
```

Example:

```bash
python tools/sanity/check_02_stack_machine.py
```

### Run the entire sanity suite (recommended for contributors)

If you are changing code or adding steps, run the repository tests:

```bash
python -m pytest -q
```

At minimum, the M0.1 check (`check_00_env.py`) must stay green on a clean machine.
Treat it as a build contract.

---

## Structure and Conventions

For each tutorial step `<NN>_<name>`, you will find four corresponding artifacts:

* **Tutorial explanation (human-facing)**
  `tutorial/sanity/<NN>_<name>.md`

* **Executable sanity check**
  `tools/sanity/check_<NN>_<name>.py`

* **Metamath fixture (object-level world)**
  `fixtures/sanity/<NN>_<name>.mm`

* **Generated proof / emitted streams (temporary)**
  written to `build/` during execution (not committed)

The same `<NN>_<name>` identifier is used across all layers.
This is a strict convention and an intentional design choice.

### About `build/`

`build/` is scratch space.

* It is safe to delete.
* It is not committed.
* When a check fails, look here first: emitted `.mm` files and logs are usually kept
  precisely to make debugging possible.

---

## Tutorial Steps

### Step 00 — Environment and Toolchain (M0.1)

**Goal:**
Verify that your environment is correctly set up and that the Metamath verifier
can be invoked from Python.

* Tutorial: `tutorial/sanity/00_env.md`
* Runner: `tools/sanity/check_00_env.py`
* Fixture: `fixtures/sanity/00_env.mm`

This step does not teach Metamath yet.
It ensures that everything *around* Metamath works.

---

### Step 01 — The Minimal Metamath Database

**Goal:**
Understand the smallest meaningful Metamath database:
constants, variables, typing hypotheses, and axioms.

* Tutorial: `tutorial/sanity/01_minimal_db.md`
* Runner: `tools/sanity/check_01_minimal_db.py`
* Fixture: `fixtures/sanity/01_minimal_db.mm`

This step answers: *“What must exist before any proof is even possible?”*

---

### Step 02 — Proofs as Stack Programs

**Goal:**
Internalize the idea that a Metamath proof is a **stack program**, not a derivation tree.

* Tutorial: `tutorial/sanity/02_stack_machine.md`
* Runner: `tools/sanity/check_02_stack_machine.py`
* Fixture: `fixtures/sanity/02_stack_machine.mm`

This step introduces the operational model:
push, pop, match, substitute.

---

### Step 03 — Mandatory `$f` Hypotheses

**Goal:**
Understand why typing hypotheses (`$f`) are *mandatory* and how their order matters.

* Tutorial: `tutorial/sanity/03_mandatory_f.md`
* Runner: `tools/sanity/check_03_mandatory_f.py`
* Fixture: `fixtures/sanity/03_mandatory_f.mm`

This step connects Metamath’s formal requirements with practical proof generation,
and introduces the first meta-level helper logic.

---

### Step 04 — Essential `$e` Hypotheses

**Goal:**
Understand `$e` hypotheses as **concrete stack objects**, not as informal assumptions.

* Tutorial: `tutorial/sanity/04_essential_e.md`
* Runner: `tools/sanity/check_04_essential_e.py`
* Fixture: `fixtures/sanity/04_essential_e.mm`

This step resolves a common misconception and clarifies how rules consume hypotheses.

---

### Step 05 — Modus Ponens (M0.2)

**Goal:**
See your first real inference rule in action: applying two essential hypotheses to derive a conclusion.

* Tutorial: `tutorial/sanity/05_mp.md`
* Runners/Fixtures:
  * Happy path: `tools/sanity/check_05_mp.py`, `fixtures/sanity/05_mp_happy.mm`
  * Missing hyp (must fail): `fixtures/sanity/05_mp_missing_hyp.mm`
  * Bad proof tokens (must fail): `fixtures/sanity/05_mp_bad_proof_tokens.mm`

This step reinforces `$f`/`$e` ordering and shows how multiple `$e` are consumed.

---

### Step 06 — Scoped Assertions and Label Visibility (M0.2)

**Goal:**
Understand `${ ... $}` blocks, label visibility, and why scope controls names but not active `$e`.

* Tutorial: `tutorial/sanity/06_scope.md`
* Fixtures:
  * Happy path: `fixtures/sanity/06_scope_happy.mm`
  * Leakage (must fail): `fixtures/sanity/06_scope_leakage.mm`
  * Unbalanced (must fail to parse): `fixtures/sanity/06_scope_unbalanced.mm`

This step shows how to structure local hypotheses/theorems and avoid scope leakage.

---

### Step 07 — Linking Multiple Units (M0.2)

**Goal:**
Learn to compose small Metamath units using include ($[ ... $]) and the rules for cross-unit visibility.

* Tutorial: `tutorial/sanity/07_linking_units.md`
* Fixtures (under `fixtures/sanity/m02/`):
  * Happy path: `07_two_units_happy.mm` (includes `07_unit_mp.mm` exporting `ax-mp` and `07_unit_thm.mm` proving `t_from_units`)
  * Cycle (must fail): `07_cycle.mm` (mutual references)
  * Non-exported label reference (must fail): `07_non_exported_label_ref.mm`

This step highlights exported vs private labels across units and why cycles are invalid.

---

## Troubleshooting (Common Failures)

### “Verifier not found” / “cannot execute verifier”

* Confirm you are running from the repository root.
* Confirm the verifier tooling under `verifier/` is present and runnable.
* Re-run Step 00; it is designed to fail early with a clear message.

### “ImportError: proof_scaffold …”

* Make sure you installed the repo in editable mode:
  `pip install -e .`
* Confirm your virtual environment is activated.

### “Verifier rejects the emitted stream”

This is not always an environment problem.

* Read the corresponding `tutorial/sanity/<NN>_<name>.md` explanation.
* Inspect the generated `.mm` artifact under `build/`.
* The rejection is part of the learning loop: it tells you exactly which formal
  constraint you violated.

---

## What This Tutorial Is — and Is Not

This tutorial **is**:

* a principled, runnable introduction to Metamath mechanics,
* a bridge between human reasoning and formal verification,
* a foundation for building higher-level proof generators.

This tutorial **is not**:

* a replacement for the Metamath specification,
* a survey of logic or mathematics,
* an automated theorem prover.

---

## Where to Go Next

After completing Step 04, you will be ready to explore:

* inference rules such as modus ponens (Step 05),
* scoped assertions (`${ ... $}`) and label visibility (Step 06),
* modular Metamath databases,
* Python-based proof generators (apply, rewriting, normalization).

These topics will appear as later tutorial steps, following the same structure.

If you are interested in ProofScaffold’s overall architecture and roadmap,
look under `references/` and `docs/`.

---

## One Guiding Principle

> **Small, verifiable steps. Always.**

Every mechanism in this project exists because it can be isolated,
executed, and checked against the trusted verifier.

That is the discipline this tutorial aims to teach.
