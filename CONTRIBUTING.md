# Contributing

## Quickstart (one command)

From a clean environment:

```bash
python -m pip install -e .[dev]
python -m proof_scaffold smoke
```

## Run the full test suite

```bash
pytest -q
ruff check .
mypy
```

## Repository conventions (M0.2)

- `src/proof_scaffold/` is the installable package.
- `src/proof_scaffold/linker_v1/` is the **v4-aligned** linker (bootstrap level).
  Only minimal public API is intended to be imported by external code.
- `examples/` are runnable scripts showing how to build IR and call the linker.
- `tests/golden/` and `tests/adversarial/` are reserved for future-proof test
  growth (determinism + failure mode regression).
- runtime artifacts (if written) must go under `build/`.

