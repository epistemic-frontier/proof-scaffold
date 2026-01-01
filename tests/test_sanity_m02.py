# tests/test_sanity_m02.py
"""
M0.2 progress-gated tests

Strategy:
- Tests are written as real, executable specs but initially marked as skip.
- As each capability lands, remove the skip on the corresponding test(s).
- For adversarial cases, switch to xfail(strict=True) if the negative case is expected to fail
  until a new gate is implemented; once the gate exists, flip to a normal assert.

Marker policy:
- sanity_m02: all tests for milestone M0.2
- step05/step06/step07: finer-grained grouping by sub-step

Fixture convention (to be created by implementers when unskipping tests):
- fixtures/sanity/m02/05_mp_happy.mm
- fixtures/sanity/m02/05_mp_missing_hyp.mm
- fixtures/sanity/m02/05_mp_bad_proof_tokens.mm
- fixtures/sanity/m02/06_scope_happy.mm
- fixtures/sanity/m02/06_scope_leakage.mm
- fixtures/sanity/m02/06_scope_unbalanced.mm
- fixtures/sanity/m02/07_two_units_happy.mm
- fixtures/sanity/m02/07_cycle.mm
- fixtures/sanity/m02/07_non_exported_label_ref.mm

Alternatively, you may provide tools/sanity/check_05_mp.py, check_06_scopes.py, check_07_multi_unit.py
that generate these fixtures on the fly; if so, adapt the helpers below accordingly.
"""
from pathlib import Path

import pytest

from proof_scaffold.verify import verify as mm_verify


def _mmverify_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "verifier" / "mmverify.py"


def verify_expect_ok(mm_fixture: Path) -> None:
    mmverify = _mmverify_path()
    mm_verify(mmverify, mm_fixture)


def verify_expect_fail(mm_fixture: Path) -> None:
    mmverify = _mmverify_path()
    with pytest.raises(RuntimeError):
        mm_verify(mmverify, mm_fixture)


# ------------------------------------
# Step 05 — modus ponens (mp)
# ------------------------------------


@pytest.mark.sanity_m02
@pytest.mark.step05
def test_05_mp_happy_path() -> None:
    mm = Path("fixtures/sanity/m02/05_mp_happy.mm")
    verify_expect_ok(mm)


@pytest.mark.sanity_m02
@pytest.mark.step05
def test_05_mp_missing_hyp_fails() -> None:
    mm = Path("fixtures/sanity/m02/05_mp_missing_hyp.mm")
    verify_expect_fail(mm)


@pytest.mark.sanity_m02
@pytest.mark.step05
def test_05_mp_bad_proof_tokens_fails() -> None:
    mm = Path("fixtures/sanity/m02/05_mp_bad_proof_tokens.mm")
    verify_expect_fail(mm)


# ------------------------------------
# Step 06 — scopes
# ------------------------------------


@pytest.mark.sanity_m02
@pytest.mark.step06
@pytest.mark.skip(reason="M0.2 step 06 not implemented: provide 06_scope_happy.mm and remove skip")
def test_06_scope_happy_path() -> None:
    mm = Path("fixtures/sanity/m02/06_scope_happy.mm")
    verify_expect_ok(mm)


@pytest.mark.sanity_m02
@pytest.mark.step06
@pytest.mark.skip(reason="M0.2 step 06 not implemented: provide 06_scope_leakage.mm and remove skip or switch to xfail(strict=True)")
def test_06_scope_leakage_rejected_by_verifier() -> None:
    mm = Path("fixtures/sanity/m02/06_scope_leakage.mm")
    verify_expect_fail(mm)


@pytest.mark.sanity_m02
@pytest.mark.step06
@pytest.mark.skip(reason="M0.2 step 06 not implemented: provide 06_scope_unbalanced.mm and remove skip or switch to xfail(strict=True)")
def test_06_scope_unbalanced_rejected_early() -> None:
    mm = Path("fixtures/sanity/m02/06_scope_unbalanced.mm")
    verify_expect_fail(mm)


# ------------------------------------
# Step 07 — multi-unit linkage
# ------------------------------------


@pytest.mark.sanity_m02
@pytest.mark.step07
@pytest.mark.skip(reason="M0.2 step 07 not implemented: provide 07_two_units_happy.mm and remove skip")
def test_07_two_units_link_and_verify() -> None:
    mm = Path("fixtures/sanity/m02/07_two_units_happy.mm")
    verify_expect_ok(mm)


@pytest.mark.sanity_m02
@pytest.mark.step07
@pytest.mark.skip(reason="M0.2 step 07 not implemented: provide 07_cycle.mm and remove skip or switch to xfail(strict=True)")
def test_07_cycle_is_detected() -> None:
    mm = Path("fixtures/sanity/m02/07_cycle.mm")
    verify_expect_fail(mm)


@pytest.mark.sanity_m02
@pytest.mark.step07
@pytest.mark.skip(reason="M0.2 step 07 not implemented: provide 07_non_exported_label_ref.mm and remove skip or switch to xfail(strict=True)")
def test_07_non_exported_label_reference_fails_early() -> None:
    mm = Path("fixtures/sanity/m02/07_non_exported_label_ref.mm")
    verify_expect_fail(mm)
