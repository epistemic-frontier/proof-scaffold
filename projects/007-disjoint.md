# Project 007: Distinct Variables (`$d`) Support

## 1. Goal
Implement support for Distinct Variable statements (`$d`) in the `MMBuilder` and downstream toolchain (`LIR`, `Linker`, `Emitter`). This is a critical prerequisite for supporting First-Order Logic (FOL) and migrating the `logic` package, as quantification requires expressing that variables do not overlap.

## 2. Implementation Details

### 2.1. LIR Model (`skfd.core.lir`)
*   Added `DisjointVar` dataclass to the LIR AST.
    ```python
    @dataclass(frozen=True)
    class DisjointVar:
        stmt_id: StmtId
        origin_ref: OriginRef
        vars: TokenSeq
    ```
*   **Critical Fix**: During implementation, we discovered that the existing `EssentialHyp`, `Axiom`, and `Theorem` LIR types were missing the `typecode` field (e.g., `|-`, `wff`). This caused the Emitter to generate invalid Metamath code. We patched `lir.py` to include `typecode: SymbolId` in these dataclasses.

### 2.2. Visitor Interface (`skfd.builder.visitor`)
*   Added `disjoint_var` method to `BuilderVisitor`.
*   Updated `essential_hyp`, `axiom`, and `theorem` signatures to accept `typecode_id`.

### 2.3. Builder (`MMBuilder`)
*   Implemented `d(*vars)` method:
    *   Accepts 2 or more variable names.
    *   Validates that all arguments are declared variables (`$v`) or imported symbols.
    *   Resolves `SymbolId`s and delegates to `visitor.disjoint_var`.
*   Updated `e`, `a`, `p` methods to correctly resolve and pass `typecode` IDs to the visitor.

### 2.4. Linker / Emitter (`skfd.linker.emit.emit_mm`)
*   Added handler for `DisjointVar` LIR statements to emit `$d <var1> <var2> ... $.`.
*   Updated handlers for `$e`, `$a`, `$p` to correctly emit the `typecode` token (previously missing).

## 3. Verification
*   Created `examples/test_distinct.py`.
*   Verified that:
    1.  `$d` statements are emitted correctly (e.g., `$d ph ps $.`).
    2.  Scoped `$d` statements obey block rules (`${ ... $}`).
    3.  Standard statements (`$a`, `$p`) now correctly include their typecodes.

## 4. Next Steps
*   Proceed with **Project 008: Logic Compiler**, bridging `src/logic` ASTs to the `MMBuilder`.
