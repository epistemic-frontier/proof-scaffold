# Project: Python-to-Metamath Proof Lowering (Real Verification for Scripts)

**Status:** Proposed  
**Owner:** TBD  
**Priority:** Medium (Critical for prototyping confidence)  

## 1. Problem Statement

Currently, the `skfd` scripting workflow (used for `init-proof` and `proof-lab/`) employs a "trust-based" emission strategy. When a user defines a `LemmaProof` in Python, the emitter:
1. Generates a temporary axiom (`$a`) matching the lemma's conclusion.
2. Generates a proof (`$p`) that trivially applies this axiom.

**Consequence:**
The external verifiers (mmverify, metamath-exe, knife) only verify that the temporary axiom matches the theorem statement. They **do not** verify the internal logic steps constructed in Python (e.g., `mp`, `syl`). A user can write a logically invalid proof step in Python (e.g., modifying a conclusion arbitrarily), and the verifier will still report "PASS".

## 2. Goal

Implement a true **Proof Lowering** pipeline that translates the Python `LemmaProof` object into a standard Metamath RPN (Reverse Polish Notation) proof string. This ensures that `skfd verify script.py` provides genuine cryptographic verification of the user's logic.

## 3. Technical Approach

### 3.1 Phase 1: Enhanced IR (Intermediate Representation)
Modify `skfd.authoring.lemmas` and `LemmaBuilder` to capture strict dependency references.

*   **Current State:** `ProofStep` only holds `label` and `wff`. `mp()` calls return a result but don't record *which* previous steps were used.
*   **New State:** Introduce `ProofOp`:
    ```python
    @dataclass
    class ProofOp:
        rule: str  # e.g., "mp", "ax-1"
        args: list[str]  # labels of previous steps or hypotheses
    ```
    `LemmaProof` will hold a sequence of these operations alongside the step definitions.

### 3.2 Phase 2: RPN Emitter
Implement a new emission function `emit_rpn_proof(lemma) -> list[str]` in `skfd.authoring.emit`.

*   **Logic:**
    1.  **Topological Sort:** Ensure steps are ordered (already implicitly done by builder).
    2.  **Stack Simulation:**
        *   For a hypothesis reference (`h1`): Emit label `h1`.
        *   For a rule application (`mp`):
            *   Recursively emit RPN for arguments (or ensure they are on stack).
            *   Emit rule label `ax-mp`.
        *   **Substitution Handling (The Hard Part):**
            *   For axiom references (e.g., `ax-1`), we must determine the substitution $\sigma$ that maps axiom variables to current step expressions.
            *   **Simplified MVP:** Require `LemmaBuilder` to explicitly provide the substitution, OR implement a simple Unification matcher for standard axioms.

### 3.3 Phase 3: Integration
Update `emit_lemmas` to use the new RPN emitter instead of the `_ax` hack.

## 4. Roadmap & Milestones

### M1: IR Enhancement
*   **Deliverable:** `LemmaBuilder` records `args` for `mp` and `step` calls.
*   **Test:** A unit test can inspect a `LemmaProof` and reconstruct the dependency graph.

### M2: MVP Emitter (MP-only)
*   **Scope:** Support only `ax-mp` (Modus Ponens) without substitution (assuming strictly matching hypotheses).
*   **Deliverable:** A script proving `A, A->B |- B` generates a real RPN proof `A A->B ax-mp`.
*   **Verification:** `skfd verify` passes without generating `_ax`.

### M3: Full Emitter (Substitution Support)
*   **Scope:** Support axiom instances (e.g., `A1` with specific $\phi, \psi$).
*   **Deliverable:** Logic to compute or record the mandatory variable substitutions required by Metamath's verification engine.

## 5. Acceptance Criteria

1.  **Positive Case:**
    *   The existing `proof-lab/prove_modus_tollens.py` (correct version) passes verification.
    *   The generated `.mm` file contains **no** `$a ..._ax` statements for the lemmas being proved.
    *   The `.mm` file contains a valid RPN sequence (e.g., `h1 h2 ... ax-mp ...`).

2.  **Negative Case (The "Litmus Test"):**
    *   Modifying a middle step in `prove_modus_tollens.py` (e.g., changing a consequence to an arbitrary value) **MUST** cause `skfd verify` to fail with a verifier error (e.g., "Step 3 verification failed").

## 6. References
*   `proof-scaffold/src/skfd/authoring/emit.py`: Current "trust-based" emitter.
*   `proof-lab/prove_modus_tollens.py`: Test bed.
