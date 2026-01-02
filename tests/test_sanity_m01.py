# tests/test_sanity_m01.py
from __future__ import annotations

import pytest

from tests._sanity_utils import repo_root, run_sanity_script_for_all_verifiers


@pytest.mark.sanity_m01
def test_00_env() -> None:
    run_sanity_script_for_all_verifiers(repo_root() / "tools" / "sanity" / "check_00_env.py")


@pytest.mark.sanity_m01
def test_01_minimal_db() -> None:
    run_sanity_script_for_all_verifiers(repo_root() / "tools" / "sanity" / "check_01_minimal_db.py")


@pytest.mark.sanity_m01
def test_02_stack_machine() -> None:
    run_sanity_script_for_all_verifiers(repo_root() / "tools" / "sanity" / "check_02_stack_machine.py")


@pytest.mark.sanity_m01
def test_03_mandatory_f() -> None:
    run_sanity_script_for_all_verifiers(repo_root() / "tools" / "sanity" / "check_03_mandatory_f.py")


@pytest.mark.sanity_m01
def test_04_essential_e() -> None:
    run_sanity_script_for_all_verifiers(repo_root() / "tools" / "sanity" / "check_04_essential_e.py")
