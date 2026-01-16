# Project 008: Prelude Framework Refactor

## 1. Goal
Separate the **Authoring Framework** (generic logic definition tools) from the **Logic Content** (specific definitions like `prelude` builtins and `logic` axioms). This establishes a clean "Toolchain vs Content" architecture.

## 2. Changes

### 2.1. New Module: `skfd.authoring`
Create a new package `src/skfd/authoring` to house the framework components.

*   **Move `src/prelude/authoring.py` -> `src/skfd/authoring/dsl.py`**
    *   Renaming `authoring.py` to `dsl.py` (or keeping `authoring.py`) inside `skfd.authoring`.
    *   Contains: `Expr`, `Constructor`, `RequireRegistry`.
*   **Move `src/prelude/rules.py` -> `src/skfd/authoring/rules.py`**
    *   Contains: `RuleBundle`, `RuleSig`, `Axiom` protocols.
*   **Move `src/prelude/typing.py` -> `src/skfd/authoring/typing.py`**
    *   Contains: `Sort`, `RuleSig`, basic errors.
*   **Move `src/prelude/symbols.py` -> `src/skfd/authoring/symbols.py`** (Maybe?)
    *   Wait, `SymbolInterner` is already in `skfd.core.symbols`. `prelude/symbols.py` might be redundant or a wrapper.
    *   *Check*: `prelude/symbols.py` likely imports from `skfd.core`. If it defines `SymbolId` logic for generic ASTs, it belongs in `skfd.authoring`.

### 2.2. Split `src/prelude/formula.py`
This file currently mixes:
1.  **Generic Formula**: `Formula[T]`, `TokenSeq` (Generic).
2.  **Specific Builtins**: `Builtins` class with `->`, `~`, `(`. (Content-specific).

*   **Plan**:
    *   Move generic `Formula`, `Wff`, `TokenSeq` to `src/skfd/authoring/formula.py`.
    *   Keep `Builtins` and specific constructors (`imp`, `wn`) in `src/prelude/formula.py` (or rename to `src/prelude/language.py`).

### 2.3. Update Dependencies
Refactor all imports in `src/prelude` and `src/logic` to point to `skfd.authoring`.

## 3. Revised Directory Structure

```
src/
  skfd/
    authoring/       <-- NEW FRAMEWORK
      __init__.py
      dsl.py         (was prelude/authoring.py)
      rules.py       (was prelude/rules.py)
      typing.py      (was prelude/typing.py)
      formula.py     (generic parts of prelude/formula.py)
  
  prelude/           <-- CONTENT ONLY
    __init__.py
    axioms.py        (uses skfd.authoring)
    formula.py       (specific builtins only)
    
  logic/             <-- CONTENT ONLY
    propositional/
      ...
```

## 4. Execution Steps
1.  Create `src/skfd/authoring`.
2.  Move files.
3.  Split `formula.py`.
4.  Mass update imports (sed or manual).
5.  Verify `prelude` and `logic` can import the new locations.
