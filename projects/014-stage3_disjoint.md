# Project 014: Stage 3 ($d Disjoint Logic)

## Motivation
Currently, `$d` (Disjoint Variable) statements are handled implicitly.
*   They naturally flow through the LIR list.
*   We rely on the "Pass-Through" behavior (Mode A from Link Model v4).

However, explicit handling is required for:
1.  **Validation**: Checking that `$d` constraints claimed by a theorem are actually present in the scope.
2.  **Generality**: Supporting future "Mode B" (Linter-driven) or "Mode C" (Auto-propagation).
3.  **Correctness**: Ensuring that `$d` statements are correctly scoped (frame-local vs unit-global).

## Goals
1.  **Implement `stage3_disjoint.py`**: A dedicated pass that scans units for `$d` statements.
2.  **Explicit Data Model**: Update `AssertionContract` (from P012) to include `distinct_vars: list[set[SymbolId]]`.
3.  **Mode A Verification**: Verify that the explicit extraction matches the implicit pass-through (Golden Test byte-identity).

## Design

### Data Model Update (`skfd/core/contracts.py`)
```python
@dataclass(frozen=True)
class AssertionContract:
    ...
    distinct_vars: list[set[SymbolId]] # Explicit $d requirements
```

### Stage 3 Pass (`skfd/linker/passes/stage3_disjoint.py`)
*   **Input**: `SerializedUnit`, `SymTab`
*   **Action**:
    *   Iterate LIR.
    *   Respect `ScopeEnter`/`ScopeExit`.
    *   Collect active `$d` statements when hitting `$a`/`$p`.
    *   Populate `AssertionContract.distinct_vars`.
*   **Output**: Enhanced `ContractIndex` (or update existing one).
    *   *Note*: Stage 3 should probably run *before* or *during* Stage 2?
    *   Actually, Link Model says "Stage 2 Contract Extraction", "Stage 3 $d Processing".
    *   They are closely related. Stage 3 enriches the contract from Stage 2.

## Plan
1.  **Update `AssertionContract`**: Add `distinct_vars`.
2.  **Create `stage3_disjoint.py`**: Implement the scope-aware scanning logic (similar to Stage 2 but for `$d`).
3.  **Integrate**:
    *   Pipeline: `Stage 1 -> Stage 2 -> Stage 3 -> Stage 4 ...`
    *   Update `LinkerV1.link`.
4.  **Verification**:
    *   Golden Test: Output must match (since we are currently just extracting, not changing emission... wait).
    *   *Correction*: If we just *extract*, `emit_mm` currently iterates LIR.
    *   If `emit_mm` (Stage 7) is "dumb", it uses `LinearPlan`.
    *   `LinearPlan` (Stage 5) uses LIR.
    *   So `$d` emission is currently handled by `stage5_scope.py` just copying LIR statements to frames.
    *   **Goal**: Stage 3 validates. It doesn't necessarily change emission *yet* (unless we move to Mode B/C where we *generate* $d).
    *   For now (Mode A), Stage 3 is a **Validation Pass** and **Contract Enricher**.

## Verification Plan
*   **Golden Test**: Must remain byte-identical.
*   **New Test**: `tests/linker/test_stage3_disjoint.py` to verify it correctly captures `$d` sets from tricky scopes.
