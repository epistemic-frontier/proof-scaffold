# Project 011: Source Map and Diagnostics

## Motivation

As defined in the Linker v4 roadmap (Reference `003_roadmap-methodology_v2.md`), **Source Maps** are essential for the "Debugging Gap." They bridge the generated Metamath artifacts (flat `.mm` files) back to the high-level Python source code that produced them.

Currently:
*   `OriginTable` tracks `(module, file, line)`.
*   `Diagnostic` struct exists.
*   `emit_mm` generates text but **discards** the mapping between output tokens and input origins.
*   CLI errors print raw JSON.

## Goals

1.  **Emit Source Maps**: `skfd` must produce a source map artifact (e.g., `.map.json`) alongside the generated `.mm` file.
2.  **Human-Readable Diagnostics**: The CLI should use origin information to print file/line locations for errors, rather than raw JSON.
3.  **Standardized Format**: Define a stable source map format (likely custom but simple, or adopting a subset of Source Map v3 if applicable).

## Design

### 1. Source Map Data Structure

The Source Map should map **Output Locations** (Metamath file lines/columns or token indices) to **Source Locations** (Python / DSL file lines).

Since `.mm` is token-based, mapping by token index or line/column is viable. Given the line-oriented nature of Metamath, a list of `(OutputLine, OutputCol, OriginRef)` tuples (or a compressed format) is efficient.

Proposed JSON structure (`target/{package}.map.json`):

```json
{
  "version": 1,
  "file": "logic_full.mm",
  "sources": ["src/logic/prop.py", ...],  // Indexed by OriginRecord module_id/file
  "mappings": "..."  // Encoded mapping string or explicit list
}
```

### 2. Implementation: `emit_mm`

Update `skfd.linker.emit.emit_mm.emit_mm` to return a `BuildArtifact` named tuple:

```python
class EmissionResult(NamedTuple):
    text: str
    source_map: SourceMap
```

The emitter loop must track the `OriginRef` of each emitted token/statement and record it.

### 3. CLI Integration

*   **Build**: Write the `.map.json` to disk.
*   **Verify/Doctor**: When `LinkerDiagError` is caught:
    *   If `primary_origin_ref` is present, look it up in the `OriginTable` (in-memory) or Source Map (on disk).
    *   Format the error as:
        ```text
        Error: [E001] Rule mismatch
          --> src/logic/prop.py:42
           |
        42 |    prove(..., rule=ax_mp)
           |    ^^^^^
        ```

## Plan

1.  **Research**: Finalize Source Map format (consider VLQ vs explicit for simplicity).
2.  **Core Update**: Enhance `emit_mm` to produce mappings.
3.  **Driver Update**: Save source maps during `build_package`.
4.  **CLI Update**: Implement diagnostic pretty-printer.

## Testing Plan

To ensure the Source Map and Diagnostics system works as intended, we will implement **negative testing** using dedicated "bad" examples.

### 1. New Example: `examples/bad_logic`
Create a new example package `examples/bad_logic` intentionally containing common errors:
*   **Type Mismatch**: Using a `wff` where a `setvar` is expected.
*   **Arity Error**: Applying a rule with incorrect number of arguments.
*   **Scope Error**: Referencing a variable outside its scope.

### 2. Verification Procedure
The test will run `skfd verify bad_logic` and assert that:
1.  The command **fails** (exit code non-zero).
2.  The output contains the **exact file path** (e.g., `src/bad_logic/prop.py`).
3.  The output contains the **correct line number** matching the error source.
4.  The error message clearly explains the reason (e.g., "Expected Sort 'wff', got 'setvar'").

### 3. Golden Files
We will use "snapshot testing" (golden files) to lock in the error output format. This ensures that any regression in diagnostic quality (e.g., losing line numbers) is immediately detected.
