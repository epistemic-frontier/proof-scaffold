# ProofScaffold — Design Notes

## 1. Purpose

ProofScaffold is an experimental framework for **structured, verifiable mathematical proofs**
based on a strict separation of concerns:

- **Human-facing mathematics** (documents)
- **Proof generation and organization** (Python)
- **Formal verification** (Metamath)

The goal is *not* to build a new proof assistant, but to explore a **layered proof ecosystem**
in which mathematical insight, mechanical proof labor, and trust are cleanly decoupled.

This repository currently focuses on a **minimal, sanity-checked core**:
propositional logic, basic arithmetic, and small classical examples (e.g. the irrationality of √2).

---

## 2. The Three Layers

### 2.1 Document Layer (Human-facing)

- Format: Markdown / LaTeX (not part of this repo yet)
- Role:
  - Explain motivation, ideas, and proof strategy
  - Identify key lemmas and proof structure
  - Remain readable and compact
- Non-goals:
  - Full formal rigor
  - Machine-checkable completeness

The document layer expresses **mathematical intent**, not proof mechanics.

---

### 2.2 Python Layer (Proof Generation)

- Location: `tools/`
- Role:
  - Generate formal proofs mechanically
  - Organize proofs modularly
  - Eliminate repetitive bookkeeping (e.g. mandatory `$f` hypotheses)
- Key principle:
  > Python code is **not the proof**.  
  > Python code is a *proof generator*.

This layer is free to use:
- Abstraction
- Parameterization
- Meta-programming
- Iteration and composition

As long as the generated result is accepted by the verifier, the Python layer itself
is **not part of the trusted computing base**.

---

### 2.3 Metamath Layer (Formal Evidence)

- Location: `fixtures/`, generated temporary files
- Role:
  - Provide final, machine-checkable proof objects
  - Act as the *court of last appeal*
- Characteristics:
  - Minimal, explicit, stack-based
  - Unfriendly to humans
  - Extremely trustworthy

Metamath files are treated as **artifacts**, not as primary authoring material.

---

## 3. Trust Model

Only the following components are trusted:

1. The Metamath verifier (`verifier/mmverify.py`)
2. The Metamath specification itself

Everything else (Python code, scripts, generators) is *untrusted by design* and must
justify itself by producing verifiable `.mm` proofs.

---

## 4. Sanity Checks

### 4.1 Purpose of Sanity Checks

Sanity checks answer one question only:

> “Does the minimal proof pipeline still work?”

They are **not**:
- Exhaustive tests
- Performance benchmarks
- Mathematical coverage checks

---

### 4.2 Current Sanity Check

- Script: `tools/check_sanity.py`
- Fixture: `fixtures/mini.mm`
- What it verifies:
  - A minimal `.mm` database can be extended
  - Mandatory `$f` hypotheses are correctly identified
  - A new `$p` theorem can be generated
  - The external Metamath verifier accepts the result

This check is intentionally small, fast, and non-negotiable.

---

### 4.3 Philosophy

Sanity checks should be:
- Few in number
- Extremely stable
- Easy to run manually
- Suitable as CI entry points

Future checks may cover:
- `$e` hypotheses
- Scoped `${ ... $}` behavior
- Basic `apply` / goal-stack semantics

But **sanity checks must never grow into a second proof system**.

---

## 5. Minimal Metamath Interface (`mm_min.py`)

`tools/mm_min.py` provides a **minimal semantic interface** to Metamath databases.

It is explicitly:
- **Not a verifier**
- **Not a full parser**
- **Not a replacement for Metamath semantics**

Its sole purpose is to support *proof planning*, e.g.:

- Determine which `$f` labels are mandatory for a given assertion
- Enable automatic stack preparation in generated proofs

This file may grow *incrementally*, driven only by concrete needs from sanity checks
and small proof generators.

---

## 6. Non-Goals (Explicit)

This project intentionally does **not** aim to:

- Re-implement Metamath
- Compete with Lean / Coq / Isabelle
- Provide interactive proof editing
- Automatically discover new proofs
- Translate Metamath proofs back into human-readable text

Any feature that blurs the separation between layers should be treated with suspicion.

---

## 7. Development Principle

> **Small, verifiable steps. Always.**

Every new capability should be introduced by:
1. A minimal design discussion
2. A tiny sanity check
3. A clear success/failure criterion

If a change cannot be sanity-checked, it is probably too large.

---

## 8. Current Status

- Minimal pipeline: ✅
- External verifier integration: ✅
- Automatic `$f` dependency handling: ✅
- Sanity check infrastructure: ✅

Next steps are intentionally incremental.

---
