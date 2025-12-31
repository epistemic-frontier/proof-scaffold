# ProofScaffold — Design Notes (Rev. 2)

## 1. Purpose

ProofScaffold is an experimental framework for **structured, verifiable mathematical proofs**, designed as a **layered build and linking system** rather than a monolithic proof assistant.

It relies on a strict separation of concerns:

* **Human-facing mathematics** (Documents)
* **Proof compilation and linking** (Python)
* **Formal verification** (Metamath)

The goal is to explore a **modernized architecture for formal proof systems**, treating mathematical proofs not as static artifacts, but as modular software components that are **assembled, relocated, linearized, and verified**.

---

## 2. The Three Layers

### 2.1 Document Layer (Human-facing)

* **Format**: Markdown / LaTeX
* **Role**: Express mathematical intent, motivation, and high-level strategy.
* **Non-goals**: Formal rigor or machine-checkability.

### 2.2 Python Layer (The Compiler & Linker)

* **Location**: `tools/`
* **Role**:
* **Compile**: Translate high-level proof strategies into Metamath steps.
* **Link**: Resolve dependencies, manage namespaces, and flatten DAGs into linear streams.
* **Map**: Maintain traceability between generated artifacts and source code (Source Maps).


* **Principle**:
> Python code is **not the proof**. Python code is the *builder* of the proof.



### 2.3 Metamath Layer (The Binary Artifact)

* **Location**: Generated in-memory streams or temporary fixtures.
* **Role**: The "object code" of the system. Extremely trustworthy, machine-checkable, but not intended for human authoring.

---

## 3. Core Architecture: The "Linker" Analogy

From an engineering perspective, ProofScaffold functions as a **Compiler Toolchain**:

1. **Parser (Input)**:
Modular Python objects define *what* should exist (theorems, axioms, proofs).
2. **Linker (Python Core)**:
This is the heart of the system. It performs tasks analogous to a C/C++ linker:
* **Dependency Resolution**: Calculating the topological sort of Python modules.
* **Symbol Management**: Maintaining a global Symbol Table to prevent collisions.
* **Relocation**: Dynamically renaming local labels (e.g., transforming `th1` in `logic.py` to `logic.th1` in the output stream).
* **Linearization**: Flattening the dependency DAG into a strict sequential stream.


3. **Executor (Verifier)**:
The Metamath verifier acts as the CPU. It executes the linearized instruction stream to validate correctness.

**Crucial Insight**: Correctness flows from *linking discipline* (structural integrity) and *verifier execution* (logical integrity), not from the heuristics of generation.

---

## 4. Trust Model

**Trusted Computing Base (TCB):**

1. The Metamath Verifier (`verifier/mmverify.py` or Rust backend).
2. The Metamath Specification (syntax and semantics).

**Untrusted:**

* All Python generation logic.
* The Linker itself.
* If the Linker produces garbage, the Verifier must reject it.

---

## 5. Sanity Checks & Development Philosophy

> **"Does the minimal pipeline link and execute?"**

Every new capability must be verified by a minimal, non-negotiable sanity check (`tools/check_sanity.py`).

* **Small**: No long-running benchmarks.
* **Stable**: If this fails, the build is broken.
* **Incremental**: We grow by small, verifiable steps.

---

## 6. Non-Goals

This project explicitly does **NOT** aim to:

* Be an automated **Theorem Prover** (AI/Solver).
* Compete with interactive assistants like Lean/Coq (UI/UX).
* Translate Metamath back to English.

---

## 7. Key Engineering Challenges (The "Deep" Roadmap)

### 7.1 Ecosystem Leverage (Package Management)

Instead of inventing a "Math Package Manager," we strictly use the **Python Ecosystem**:

* **Distribution**: PyPI.
* **Versioning**: `pip` & `requirements.txt`.
* **Imports**: Python `import` statements define the logical dependency graph.

### 7.2 Compute over I/O (Performance Strategy)

To scale, we must eliminate the I/O bottleneck.

* **In-Memory Generation**: Python generates proof streams directly in RAM.
* **Zero-Copy Verification**: The verifier should access these streams via **Shared Memory** or **Buffer Protocols**, avoiding disk writes and memory copying.

### 7.3 The Relocation Problem (Namespace Flattening)

Metamath has a flat global namespace. Python has scoped modules.
The Linker must bridge this gap by performing **Relocation**:

* All exported symbols from a module must be namespaced (e.g., `arithmetic.add_comm`).
* All internal references in proof steps must be rewritten to match the namespaced labels.

### 7.4 The Debugging Gap (Source Maps)

**Risk**: A verifier error in a 50MB generated stream is impossible to debug.
**Solution**: The Linker must generate **Source Maps** (metadata) that map:
`Byte Offset 1048576 (Error)` -> `arithmetic.py: Line 42 (Generator Function)`
This allows the developer to fix the Python logic, not the Metamath artifact.

---

## 8. Current Status

* **Pipeline**: Minimal Python -> `.mm` -> Verifier loop is active. ✅
* **Dependency**: Basic `$f` hypothesis injection is working. ✅
* **Next Step**: Implementing the first "Linker" prototype to handle multi-module symbol relocation. 🚧
