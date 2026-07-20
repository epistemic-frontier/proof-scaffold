# Project 019: Proof Explorer (Theorem Dependency Browser)

## Status
Implemented (MVP)

## Context
Classic Metamath workflows often rely on the `metamath` executable’s built-in HTML output (`show statement ... /html|/alt_html`, `markup`, `write theorem_list`) to browse statements and navigate proof structure.

In ProofScaffold, we already maintain structured build/link state:
- A global `SymbolInterner` / `symtab` for labels, constants, variables.
- A deterministic `OriginTable` and emitted `SourceMap` for traceability.
- A linker pipeline with a Stage 2 “contract extraction” pass that computes (for each `$p`) its `direct_dependencies` by scanning proof labels.

This makes it feasible to host a small local web service for exploring theorem dependency chains for a selected build unit (project/package) without introducing external web frameworks.

## Goals
1. Provide a local browser UI to explore assertion dependency chains for a chosen build unit.
2. Expose both **direct dependencies** and **reverse dependencies** for a selected theorem/axiom label.
3. Show source origin information (file/line) when available.
4. Keep the implementation dependency-free (stdlib-only), lightweight, and easy to run in dev workspaces.
5. Reuse existing linker analysis (Stage 1–3 + Stage 2 details) as the single source of truth.

## Non-Goals
- Rendering full proof trees step-by-step (proof tokens, substitution, unification).
- Producing the same HTML output format as `metamath`/`set.mm` sites.
- Serving over the network (defaults bind to `127.0.0.1`).
- Introducing a hard dependency on Flask/FastAPI or a front-end framework.
- Replacing `skfd doctor slice` / `skfd debug` (this project complements them).

## Design Summary
### Data Source
We build a theorem/axiom dependency graph using existing linker passes:
1. Run Stage 1 lint/resolution for correctness.
2. Run Stage 2 Contract Extraction to obtain:
   - `contracts.contracts`: the exported assertion interface contracts (`$a` and `$p`)
   - `contracts.details`: theorem details for `$p`, including `direct_dependencies`
3. Run Stage 3 disjoint processing (kept consistent with normal linker flow).

This analysis is performed in-memory, and does not require emission of a transient monolith `.mm` file.

### Dependency Semantics (MVP)
- Node set: all assertion labels seen in Stage 2 `contracts.contracts`.
- Edges: for each theorem `$p`, add edges to every proof label in `direct_dependencies` that is also an assertion label.
- Reverse edges are computed mechanically from the forward edges.

Note: Stage 2 currently records “all proof labels” and does not distinguish local hypotheses; the browser filters to assertion labels only (axioms/theorems).

### API Surface
The service exposes:
- `GET /` (HTML UI)
- `GET /api/graph` (nodes + edges + reverse edges; JSON)
- `GET /api/node?sid=<int>` (details for a single node; JSON)
- `GET /api/ping` (health)

### UI
The UI is a minimal static page embedded in the server:
- Search/filter by label substring.
- Click a label to view:
  - direct dependencies
  - reverse dependencies
  - origin (file:line) if available

## Implementation
### CLI Entry Point
A new CLI command is added:
```bash
python -m skfd.cli serve <project-name> --port 8000
```

This command:
1. Discovers and builds all local build units via the existing driver.
2. Selects the requested build unit and its transitive dependency closure.
3. Builds the theorem dependency graph from their units.
4. Starts a local HTTP server.

Code: [cli.py](../src/skfd/cli.py)

### Web Module
The web server and graph construction live under `skfd.web`:
- Graph construction: `build_theorem_graph(...)`
- HTTP server: stdlib `ThreadingHTTPServer` + `BaseHTTPRequestHandler`

Code: [theorem_browser.py](../src/skfd/web/theorem_browser.py)

## Verification / Acceptance
MVP is accepted when:
1. Unit tests pass with required coverage.
2. `skfd serve` starts and serves the UI for a valid build unit.
3. `/api/graph` returns a consistent graph and `/api/node` resolves nodes correctly.

Tests:
- [test_theorem_browser.py](../tests/feature/test_theorem_browser.py)
- [test_theorem_browser_http.py](../tests/feature/test_theorem_browser_http.py)

## Known Limitations (MVP)
1. **No proof-step view**: dependencies are at the theorem/axiom label level only.
2. **Dependency over-approximation**: Stage 2 collects all proof labels; we filter to assertion labels but do not yet compute a minimized dependency set.
3. **No cross-project aggregation**: the graph is built per served build unit closure.
4. **Origins depend on authoring discipline**: origin info exists only when builder/origin recording is present for the symbol.

## Follow-ups (Candidates)
1. Add “depth-limited expansion” and “path finder” (e.g. find a path from theorem A to axiom B).
2. Integrate `SourceMap` to link back to `.mm` line spans and offer “open context” views similar to `skfd debug`.
3. Provide export formats: DOT / Mermaid / JSON-LD for offline visualization.
4. Improve dependency precision:
   - exclude local `$e/$f` hypotheses explicitly
   - optionally classify edges by proof-step type (if we expose proof token metadata later)
5. Add per-unit aggregation views (unit DAG vs theorem DAG) and toggles.

## Notes on Relationship to Metamath HTML
This project does not aim to replicate Metamath’s HTML generator. Instead, it leverages ProofScaffold’s IR and diagnostics infrastructure to provide a lightweight, local browsing experience that is consistent with the toolchain’s internal notion of labels, origins, and dependencies.
