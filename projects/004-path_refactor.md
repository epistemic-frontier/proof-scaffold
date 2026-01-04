# Refactoring Plan: Path and Naming Simplification (Status: Implemented)

## Motivation
The current package structure `proof_scaffold.linker_v1` exposes implementation details (versioning, internal names) to the public API. We want a cleaner API surface:
- `proof_scaffold.linker` instead of `linker_v1`.
- `proof_scaffold.linker.lir` instead of `ir_lir`.

## 1. Naming Changes

### 1.1 `linker_v1` -> `linker`
The primary linker module should simply be `linker`. If we introduce a v2 later, we can decide then (e.g., `linker.v2` or `linker_v2` next to it), but the "default" import should be clean.

*   **Move**: `src/proof_scaffold/linker_v1` -> `src/proof_scaffold/linker`
*   **Update Imports**: All `proof_scaffold.linker_v1` imports -> `proof_scaffold.linker`.

### 1.2 `ir_lir.py` -> `lir.py`
The name `ir_lir` is redundant. `LIR` (Linker Intermediate Representation) is sufficient.

*   **Move**: `src/proof_scaffold/linker/ir_lir.py` -> `src/proof_scaffold/linker/lir.py`
*   **Update Imports**: `proof_scaffold.linker_v1.ir_lir` -> `proof_scaffold.linker.lir`.

### 1.3 `linker/sanity` -> `tools/doctor` (or top-level)
The sanity check (`check_sanity.py`) is a toolchain health check, not a linker function. It belongs in the CLI/doctor logic or a top-level `tools` package.

*   **Move**: `src/proof_scaffold/linker/sanity` -> `src/proof_scaffold/doctor` (or merge logic into `cli.py` / `doctor.py`).
*   **Rationale**: The linker should just link. The doctor should check if the linker works.

## 2. Implementation Steps

1.  **Rename Directory**: Move `src/proof_scaffold/linker_v1` back to `src/proof_scaffold/linker`.
2.  **Rename File**: Rename `ir_lir.py` to `lir.py` inside `linker`.
3.  **Relocate Sanity**:
    *   Create `src/proof_scaffold/doctor/`.
    *   Move `check_sanity.py` and `build_sanity_ir.py` to `src/proof_scaffold/doctor/`.
4.  **Update Imports**:
    *   Search and replace `proof_scaffold.linker_v1` -> `proof_scaffold.linker`.
    *   Search and replace `.ir_lir` -> `.lir`.
    *   Update sanity imports.
5.  **Verify**:
    *   Run `skfd doctor`.
    *   Run `skfd smoke`.
    *   Run `pytest`.
