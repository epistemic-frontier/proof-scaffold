# tests/test_sanity_m02.py
from __future__ import annotations

import pytest

from tests._sanity_utils import fixture, verify_expect_fail, verify_expect_ok


@pytest.mark.sanity_m02
@pytest.mark.step05
def test_05_mp_happy_path() -> None:
    verify_expect_ok(fixture("fixtures/sanity/05_mp_happy.mm"))


@pytest.mark.sanity_m02
@pytest.mark.step05
def test_05_mp_missing_hyp_fails() -> None:
    verify_expect_fail(fixture("fixtures/sanity/05_mp_missing_hyp.mm"))


@pytest.mark.sanity_m02
@pytest.mark.step05
def test_05_mp_bad_proof_tokens_fails() -> None:
    verify_expect_fail(fixture("fixtures/sanity/05_mp_bad_proof_tokens.mm"))


@pytest.mark.sanity_m02
@pytest.mark.step06
def test_06_scope_happy_path() -> None:
    verify_expect_ok(fixture("fixtures/sanity/06_scope_happy.mm"))


@pytest.mark.sanity_m02
@pytest.mark.step06
def test_06_scope_leakage_rejected_by_verifier() -> None:
    verify_expect_fail(fixture("fixtures/sanity/06_scope_leakage.mm"))


@pytest.mark.sanity_m02
@pytest.mark.step06
def test_06_scope_unbalanced_rejected_early() -> None:
    verify_expect_fail(fixture("fixtures/sanity/06_scope_unbalanced.mm"))


@pytest.mark.sanity_m02
@pytest.mark.step07
def test_07_two_units_link_and_verify() -> None:
    verify_expect_ok(fixture("fixtures/sanity/07_two_units_happy.mm"))


@pytest.mark.sanity_m02
@pytest.mark.step07
def test_07_cycle_is_detected() -> None:
    verify_expect_fail(fixture("fixtures/sanity/07_cycle.mm"))


@pytest.mark.sanity_m02
@pytest.mark.step07
def test_07_non_exported_label_reference_fails_early() -> None:
    verify_expect_fail(fixture("fixtures/sanity/07_non_exported_label_ref.mm"))
