# Project 010: Logic Hardening (Adversarial Tests)

## Motivation

The roadmap analysis revealed a significant gap in Phase 1 (Linker v0) validation. The mandatory "Adversarial Tests" (ADV-P0-*) are crucial regression guards for the structural integrity of the linker, yet only 1 out of 6 is implemented.

We must implement these tests to ensure:
*   Global `SymbolId` space uniqueness.
*   Deterministic closure and emission order.
*   Correct export resolution logic.

## Goals

Implement the missing adversarial tests defined in `references/002_link-model_v4.md`:

1.  **ADV-P0-1**: Global SymbolId space (prevent unit-local ID collision).
2.  **ADV-P0-2**: Closure computation order-invariance.
3.  **ADV-P0-3**: Export-aware resolution consistency.
4.  **ADV-P0-4**: Label collision support (and ambiguity rejection).
5.  **ADV-P0-6**: Diagnostics determinism.

## Implementation Plan

### 1. Test Harness Update
Ensure `tests/adversarial/` can run these complex multi-module scenarios easily.

### 2. Test Implementation
Create separate test files for each requirement:
*   `tests/adversarial/test_adv_p0_1_global_id.py`
*   `tests/adversarial/test_adv_p0_2_closure_order.py`
*   ...and so on.

### 3. Verification
Run `pytest tests/adversarial` and ensure all pass. If any fail, fix the underlying linker logic immediately.
