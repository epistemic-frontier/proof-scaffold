# Project 012: Contract Extraction (Stage 2)

## Motivation

"Do it right, do it perfect."

Currently, **Stage 2 (Contract Extraction)** is implicit.
*   **Stage 4 (Topo Sort)** manually scans `Theorem.proof` to find dependencies.
*   **Stage 7 (Emission)** manually scans `Axiom/Theorem` to find variable types (`$f`) and hypotheses (`$e`).

This coupling means:
1.  Every pass that needs semantic info re-implements the logic (DRY violation).
2.  We lack a central place to enforce "Interface Contracts" (e.g., verifying that a theorem only uses exported hypotheses).
3.  Future advanced features (like `$d` checking or incremental builds) will have no foundation.

## Goals

explicitly implement **Stage 2** as defined in Link Model v4.

1.  **Define `Contract` Data Models**: Explicitly represent what a unit "exports" (Assertion Interface) and "imports" (Theorem Dependencies).
2.  **Implement `stage2_contracts.py`**: A pass that transforms `ProofUnitIR` (raw LIR) into `ResolvedUnit` (or attaches metadata).
3.  **Refactor Downstream**: Update Stage 4 (Topo Sort) to use the pre-computed contracts instead of scanning LIR.

## Design

### New Data Models (`skfd/core/contracts.py`)

```python
@dataclass(frozen=True)
class AssertionContract:
    """The interface of a $a or $p (what you need to know to use it)."""
    label: SymbolId
    mandatory_hyps: list[SymbolId]  # $e labels, ordered
    mandatory_vars: list[SymbolId]  # $f vars, ordered
    # distinct_vars: list[set[SymbolId]] # Future: $d constraints

@dataclass(frozen=True)
class TheoremDetails:
    """Internal details of a theorem (what it uses)."""
    label: SymbolId
    direct_dependencies: set[SymbolId] # The $a/$p labels used in the proof
```

### Updates to `ProofUnitIR`
可以把这些内容附加到 unit，也可以放在独立的 `ContractTable` 中作为伴随数据。
Given `ProofUnitIR` is immutable serialization, let's keep it separate or create a `AnalysisContext`.

*   **Decision**: `Stage2` returns a `ContractIndex: dict[SymbolId, AssertionContract]` and `DependencyIndex: dict[SymbolId, TheoremDetails]`.

## Plan

1.  **Create `src/skfd/core/contracts.py`**.
2.  **Create `src/skfd/linker/passes/stage2_contracts.py`**.
    *   Iterate all units.
    *   For each `$a/$p`: compute mandatory hypotheses ($e) and variables ($f).
    *   For each `$p`: scan proof to compute direct dependencies.
3.  **Update `LinkerV1`**:
    *   Run Stage 2 after Stage 1.
    *   Store results in a new `LinkerContext` or pass them along.
4.  **Refactor Stage 4 (Topo Sort)**:
    *   Consume `DependencyIndex` instead of scanning LIR.
    *   This makes Stage 4 cleaner and purely graph-based.

## Verification

*   **Golden Verification**: The output of `emit_mm` must remain **byte-identical**. Stage 2 is pure analysis/refactor; it changes internal flow but not external behavior.
*   **Adversarial Tests**: `ADV-P0-2` (Closure Order) must still pass (Stage 4 still works).
