# Project 011: Scope Planning (Stage 5 Isolation)

## Motivation

Currently, the linker's emission logic (`emit_mm.py`) mixes two distinct responsibilities:
1.  **Scope Planning**: Deciding *what* to emit and *where* (header vs body, preamble comments, scope attributes).
2.  **Text Generation**: Converting internal objects to strings and concatenating them.

This coupling makes it difficult to:
*   Guarantee deterministic layout (e.g., ensuring headers are hoisted exactly once).
*   Implement Source Maps (which require precise layout tracking *before* string generation).
*   Support future "Parallel Emission" or "Incremental Emission" strategies.

## Goals

Separate **Stage 5 (Scope Planning)** from **Stage 7 (Emission)**.

1.  **Implement `Stage 5`**: A pass that transforms `list[ProofUnitIR]` into a `LinearPlan`.
2.  **Define `LinearPlan`**: An IR representing the final flat Metamath file structure (Preamble, Header, Body Frames).
3.  **Refactor `emit_mm`**: Reduce it to a dumb printer that consumes `LinearPlan`.

## Design

### Data Model (`LinearPlan`)

```python
@dataclass
class LinearPlan:
    preamble: list[str]  # Comments $( ... $)
    header: list[tuple[str, SymbolId]] # Type ($c/$v), SymbolId
    frames: list[ScopeFrame]
```

### Constraints (Invariant Preservation)
*   **Determinism**: The `LinearPlan` must be constructed deterministically (sorting header symbols, etc.).
*   **Correctness**: The refactor must not change the output of the current `LinkerV1`.

## Plan

1.  **Create `src/skfd/linker/passes/stage5_scope.py`**.
2.  **Define `LinearPlan` and helper structs**.
3.  **Move "Header Collection" logic** from `emit_mm` to `stage5_scope`.
4.  **Refactor `emit_mm.py`** to take `LinearPlan` as input.
5.  **Update `LinkerV1`** to pipeline `Stage 4 -> Stage 5 -> Stage 6 (Reloc) -> Stage 7 (Emit)`.

## Verification

*   **Regression**: All existing tests (including Project 10 adversarial tests) must pass.
*   **Golden Test**: Compare `emit_mm` output before and after refactor (should be byte-identical).
