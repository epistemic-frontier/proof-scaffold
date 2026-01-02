# ProofScaffold

A layered, sanity-checked scaffold for building modular Metamath artifacts.

This repository treats Python as the builder (compiler/linker) and Metamath as the verifier (semantic authority). Documents capture design intent first; code implements passes with explicit invariants; tests provide the non-negotiable gates.

## Quickstart

- Python >= 3.10
- Install dev deps and run tests:

```
python3 -m pip install -e .[dev]
pytest -q -ra
```

The default test suite contains always-on sanity checks (00–04). See `docs/sanity/` for the associated specs and `tools/sanity/` for the generators.

## Milestone M0.2: Progress-Gated Tests

We use a "document-first + test-first + don’t break CI" approach. Instead of commenting out tests, we commit executable tests that are initially marked as `skip` (or `xfail(strict=True)` for negative cases). As each capability lands, we remove the gate on a per-test basis.

- New file: `tests/test_sanity_m02.py`
- Markers:
  - `sanity_m02`: all M0.2 tests
  - `step05`, `step06`, `step07`: per-step groupings
- Run just the M0.2 suite:

```
pytest -q -ra -m sanity_m02
```

### Unskip workflow

1) Land a minimal implementation for a step (e.g., 05 mp) and add/replace the corresponding fixture(s) under `fixtures/sanity/`.
2) Remove the `@pytest.mark.skip` on the happy-path test.
3) For adversarial tests, switch from `skip` to `xfail(strict=True)` until the early gate exists; then remove `xfail` and assert the precise diagnostic.

### Fixture conventions (to keep deltas small)

- `fixtures/sanity/05_mp_happy.mm`
- `fixtures/sanity/05_mp_missing_hyp.mm`
- `fixtures/sanity/05_mp_bad_proof_tokens.mm`
- `fixtures/sanity/06_scope_happy.mm`
- `fixtures/sanity/06_scope_leakage.mm`
- `fixtures/sanity/06_scope_unbalanced.mm`
- `fixtures/sanity/07_two_units_happy.mm`
- `fixtures/sanity/07_cycle.mm`
- `fixtures/sanity/07_non_exported_label_ref.mm`

These are placeholders initially; replace them with minimal, verifiable `.mm` snippets (or generator scripts in `tools/sanity/` that emit them) as you implement each step.

## References

- `references/001_arch-design.md` — Design notes (Rev. 2)
- `references/002_link-model_v3.md` — Linker model v3 (contracts, relocation, scopes)
- `references/003_roadmap-methodology_v2.md` — Roadmap & methodology (document-first plan)

## Project Hygiene

- Always keep sanity checks green.
- Treat interface contracts as public API.
- Prefer small ProofUnits with clear exports.
- Determinism and explicitness are first-class constraints.
