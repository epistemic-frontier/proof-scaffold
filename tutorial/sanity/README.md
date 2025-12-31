# ProofScaffold Tutorial

This tutorial is an **executable introduction to Metamath**.

It is designed for readers who want to understand **how Metamath proofs actually work** —
not just as symbolic logic, but as a concrete, verifiable *mechanism* — and how to
build higher-level proof workflows on top of that mechanism.

The tutorial is fully self-contained: every conceptual step is paired with a
*sanity check* that you can run locally and verify with the official Metamath verifier.

---

## How to Read This Tutorial

This tutorial is meant to be read **in order**.

Each step introduces exactly one new idea and is accompanied by:

- a minimal Metamath fixture (`.mm`)
- a Python companion program (`check_*.py`)
- a human-facing explanation of what happens during verification

You are encouraged to **run the code as you read**.

If something fails, the error messages are not incidental — they are part of the lesson.

---

## Structure and Conventions

For each tutorial step `<NN>_<name>`, you will find four corresponding artifacts:

- **Tutorial explanation**  
  `docs/tutorial/sanity/<NN>_<name>.md`

- **Executable sanity check**  
  `tools/sanity/check_<NN>_<name>.py`

- **Metamath fixture (object-level world)**  
  `fixtures/sanity/<NN>_<name>.mm`

- **Generated proof (temporary)**  
  Written to `build/` during execution (not committed)

The same `<NN>_<name>` identifier is used across all layers.
This is a strict convention and an intentional design choice.

---

## Tutorial Steps

### Step 00 — Environment and Toolchain

**Goal:**  
Verify that your environment is correctly set up and that the Metamath verifier
can be invoked from Python.

- Tutorial: `sanity/00_env.md`
- Runner: `tools/sanity/check_00_env.py`
- Fixture: `fixtures/sanity/00_env.mm`

This step does not teach Metamath yet.  
It ensures that everything *around* Metamath works.

---

### Step 01 — The Minimal Metamath Database

**Goal:**  
Understand the smallest meaningful Metamath database:
constants, variables, typing hypotheses, and axioms.

- Tutorial: `sanity/01_minimal_db.md`
- Runner: `tools/sanity/check_01_minimal_db.py`
- Fixture: `fixtures/sanity/01_minimal_db.mm`

This step answers: *“What must exist before any proof is even possible?”*

---

### Step 02 — Proofs as Stack Programs

**Goal:**  
Internalize the idea that a Metamath proof is a **stack program**, not a derivation tree.

- Tutorial: `sanity/02_stack_machine.md`
- Runner: `tools/sanity/check_02_stack_machine.py`
- Fixture: `fixtures/sanity/02_stack_machine.mm`

This step introduces the operational model:
push, pop, match, substitute.

---

### Step 03 — Mandatory `$f` Hypotheses

**Goal:**  
Understand why typing hypotheses (`$f`) are *mandatory* and how their order matters.

- Tutorial: `sanity/03_mandatory_f.md`
- Runner: `tools/sanity/check_03_mandatory_f.py`
- Fixture: `fixtures/sanity/03_mandatory_f.mm`

This step connects Metamath’s formal requirements with practical proof generation,
and introduces the first meta-level helper logic.

---

### Step 04 — Essential `$e` Hypotheses

**Goal:**  
Understand `$e` hypotheses as **concrete stack objects**, not as informal assumptions.

- Tutorial: `sanity/04_essential_e.md`
- Runner: `tools/sanity/check_04_essential_e.py`
- Fixture: `fixtures/sanity/04_essential_e.mm`

This step resolves a common misconception and clarifies how rules consume hypotheses.

---

## What This Tutorial Is — and Is Not

This tutorial **is**:

- a principled, runnable introduction to Metamath mechanics
- a bridge between human reasoning and formal verification
- a foundation for building higher-level proof generators

This tutorial **is not**:

- a replacement for the Metamath specification
- a survey of logic or mathematics
- an automated theorem prover

---

## Where to Go Next

After completing Step 04, you will be ready to explore:

- inference rules such as modus ponens
- scoped assertions (`${ ... $}`)
- modular Metamath databases
- Python-based proof generators (`apply`, rewriting, normalization)

These topics will appear as later tutorial steps, following the same structure.

---

## One Guiding Principle

> **Small, verifiable steps. Always.**

Every mechanism in this project exists because it can be isolated,
executed, and checked against the trusted verifier.

That is the discipline this tutorial aims to teach.
