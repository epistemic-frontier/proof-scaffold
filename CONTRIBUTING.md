# Contributing

## Quickstart (one command)

From a clean environment:

```bash
uv pip install -e .[dev]
python -m skfd.cli smoke
```

## Run the full test suite

```bash
pytest -q
ruff check .
mypy
```

## Dev mode vs. user mode

**Dev mode (multi-repo / local path deps)**
- Repos live side-by-side; dependencies are pulled via local path (`uv` sources).
- You may need to set `PYTHONPATH` so sibling packages can be imported.
- Use the dev-only helper:
  ```bash
  scripts/verify.sh <project-name>
  ```
  This script wires `PYTHONPATH` for sibling repos and runs `skfd verify`.

**User mode (installed via pyproject)**
- Dependencies are installed packages; no `PYTHONPATH` needed.
- Run verification directly:
  ```bash
  python -m skfd.cli verify <project-name>
  ```

## Repository conventions (M0.2)

- `src/skfd/` is the installable package.
- `src/skfd/linker/` hosts the linker implementation (bootstrap level).
  Only minimal public API is intended to be imported by external code.
- `examples/` are runnable scripts showing how to build IR and call the linker.
- `tests/golden/` and `tests/adversarial/` are reserved for future-proof test
  growth (determinism + failure mode regression).
- runtime artifacts (if written) must go under `build/`.
