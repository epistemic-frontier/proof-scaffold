# Project 016: Python-to-Metamath Proof Lowering

**Status:** Implemented for the current lowered-proof path; legacy raw fallback remains.

## 1. Current State

ProofScaffold now has a real lowering path for proof objects whose steps use the
supported lowered operations:

- `hyp`
- `ref`
- `mp`
- `apply` with `ref="mp"`

The implementation is [emit_lowered_lemmas](/Users/mingli/MetaMath/proof-scaffold/src/skfd/authoring/emit.py).
It emits ordinary Metamath `$p` proof token sequences, not synthetic `_ax`
trust shortcuts, for supported proofs.

The script runner uses this path when verifying standalone proof scripts:
[script_runner.py](/Users/mingli/MetaMath/proof-scaffold/src/skfd/driver/script_runner.py).

## 2. What Is Actually Lowered

The lowered path:

1. Builds theorem hypotheses from `hyp` steps.
2. Resolves references through supplied label ids or local labels.
3. Unifies referenced theorem/axiom templates with target step formulas.
4. Emits mandatory wff construction proof tokens.
5. Emits RPN proof tokens for referenced hypotheses, referenced assertions, and
   modus ponens applications.
6. Topologically orders lowered lemmas by internal lemma dependencies.

It supports a focused propositional lowering subset. Current logic package usage
verifies the emitted proof tokens with `mmverify`, `metamath`, and
`metamath-knife`.

## 3. Raw Fallback

The old trust-based behavior is not the primary lowered path anymore, but a raw
fallback still exists for proof objects containing unsupported operations.

Behavior:

- If unsupported operations are present and `BuildConfig.forbid_raw` is false,
  the lemma is emitted as an axiom and a warning is produced when `warn_raw` is
  true.
- If `BuildConfig.forbid_raw` is true, unsupported operations raise
  `E_RAW_NOT_ALLOWED`.

This means strict/conformance builds should set `forbid_raw=True` when they must
guarantee no proof falls back to axiom emission.

## 4. Acceptance Status

Implemented:

- Supported lowered proofs emit `$p` statements with real RPN proof tokens.
- Lowered proofs are covered by verifier-backed tests.
- Missing floating hypotheses, unknown labels, circular dependencies,
  self-references, and unsupported raw operations have explicit failure paths.

Still open:

- Broader connective support, especially complete `∨` lowering via `df-or`.
- Richer HIR/debug mapping from Python proof steps to emitted proof-token spans.
- Removal or stricter gating of the legacy `emit_lemmas` axiom fallback.

## 5. References

- [emit.py](/Users/mingli/MetaMath/proof-scaffold/src/skfd/authoring/emit.py)
- [test_emit_lowered_v2.py](/Users/mingli/MetaMath/proof-scaffold/tests/feature/test_emit_lowered_v2.py)
- [script_runner.py](/Users/mingli/MetaMath/proof-scaffold/src/skfd/driver/script_runner.py)
