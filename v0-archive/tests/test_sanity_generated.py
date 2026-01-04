from __future__ import annotations

from pathlib import Path

import pytest

from proof_scaffold.dsl import MMBuilder, MMDSLError
from proof_scaffold.verify import verify
from tests._sanity_utils import semantic_verifiers


def _write_and_verify(tmp_path: Path, mm_src: str, should_pass: bool) -> None:
    mm_file = tmp_path / "gen.mm"
    mm_file.write_text(mm_src, encoding="utf-8")
    for v in semantic_verifiers():
        if should_pass:
            verify(v, mm_file)
        else:
            with pytest.raises(RuntimeError):
                verify(v, mm_file)


# 00_env: minimal environment + a trivial theorem using ax-id
@pytest.mark.generated
def test_gen_00_env(tmp_path: Path) -> None:
    mm = MMBuilder()
    mm.c("wff", "(", ")", "->", "|-")
    mm.v("ph")
    mm.f("wph", "wff", "ph")
    mm.a("ax-id", "|-", "( ph -> ph )")
    with mm.block():
        mm.p("t", "|-", "( ph -> ph )", proof=["wph", "ax-id"])
    _write_and_verify(tmp_path, mm.render(), should_pass=True)


# 01_minimal_db: same as 00
@pytest.mark.generated
def test_gen_01_minimal_db(tmp_path: Path) -> None:
    mm = MMBuilder()
    mm.c("wff", "(", ")", "->", "|-")
    mm.v("ph")
    mm.f("wph", "wff", "ph")
    mm.a("ax-id", "|-", "( ph -> ph )")
    with mm.block():
        mm.p("t", "|-", "( ph -> ph )", proof=["wph", "ax-id"])
    _write_and_verify(tmp_path, mm.render(), should_pass=True)


# 02_stack_machine: ax-1 then a one-step theorem
@pytest.mark.generated
def test_gen_02_stack_machine(tmp_path: Path) -> None:
    mm = MMBuilder()
    mm.c("wff", "(", ")", "->", "|-")
    mm.v("ph", "ps")
    mm.f("wph", "wff", "ph")
    mm.f("wps", "wff", "ps")
    mm.a("ax-1", "|-", "( ph -> ( ps -> ph ) )")
    with mm.block():
        mm.p("t", "|-", "( ph -> ( ps -> ph ) )", proof=["wph", "wps", "ax-1"])
    _write_and_verify(tmp_path, mm.render(), should_pass=True)


# 03_mandatory_f: structure only (no $p needed)
@pytest.mark.generated
def test_gen_03_mandatory_f(tmp_path: Path) -> None:
    mm = MMBuilder()
    mm.c("wff", "(", ")", "->", "|-")
    mm.v("ph", "ps")
    mm.f("wph", "wff", "ph")
    mm.f("wps", "wff", "ps")
    mm.a("ax-1", "|-", "( ph -> ( ps -> ph ) )")
    # just verify database parses
    _write_and_verify(tmp_path, mm.render(), should_pass=True)


# 04_essential_e: local $e hypothesis used in a theorem
@pytest.mark.generated
def test_gen_04_essential_e(tmp_path: Path) -> None:
    mm = MMBuilder()
    mm.c("wff", "|-")
    mm.v("ph")
    mm.f("wph", "wff", "ph")
    with mm.block():
        mm.e("hph", "|-", ("ph",))
        mm.a("id-e", "|-", ("ph",))
        mm.p("sanity.e1", "|-", ("ph",), proof=["wph", "hph", "id-e"])
    _write_and_verify(tmp_path, mm.render(), should_pass=True)


# 05 MP family
@pytest.mark.generated
def test_gen_05_mp_happy(tmp_path: Path) -> None:
    mm = MMBuilder()
    mm.c("wff", "->", "(", ")")
    mm.v("ph", "ps")
    mm.f("wph", "wff", "ph")
    mm.f("wps", "wff", "ps")
    with mm.block():
        mm.e("h1", "wff", ("ph",))
        mm.e("h2", "wff", ("(", "ph", "->", "ps", ")"))
        mm.a("ax-mp", "wff", ("ps",))
        mm.p("th_mp", "wff", ("ps",), proof=["wph", "wps", "h1", "h2", "ax-mp"])
    _write_and_verify(tmp_path, mm.render(), should_pass=True)


@pytest.mark.generated
def test_gen_05_mp_missing_hyp_fails_semantic(tmp_path: Path) -> None:
    mm = MMBuilder()
    mm.c("wff", "->", "(", ")")
    mm.v("ph", "ps")
    mm.f("wph", "wff", "ph")
    mm.f("wps", "wff", "ps")
    with mm.block():
        mm.e("h1", "wff", ("ph",))
        mm.e("h2", "wff", ("(", "ph", "->", "ps", ")"))
        mm.a("ax-mp", "wff", ("ps",))
        # missing h2 in proof
        mm.p("th_mp", "wff", ("ps",), proof=["wph", "wps", "h1", "ax-mp"])
    _write_and_verify(tmp_path, mm.render(), should_pass=False)


@pytest.mark.generated
def test_gen_05_mp_bad_proof_tokens_fails_semantic(tmp_path: Path) -> None:
    mm = MMBuilder()
    mm.c("wff", "->", "(", ")")
    mm.v("ph", "ps")
    mm.f("wph", "wff", "ph")
    mm.f("wps", "wff", "ps")
    with mm.block():
        mm.e("h1", "wff", ("ph",))
        mm.e("h2", "wff", ("(", "ph", "->", "ps", ")"))
        mm.a("ax-mp", "wff", ("ps",))
        # swapped order of essentials
        mm.p("th_mp", "wff", ("ps",), proof=["wph", "wps", "h2", "h1", "ax-mp"])
    _write_and_verify(tmp_path, mm.render(), should_pass=False)


# 06 scope happy/leakage/unbalanced
@pytest.mark.generated
def test_gen_06_scope_happy(tmp_path: Path) -> None:
    mm = MMBuilder()
    mm.c("wff", "(", ")", "->")
    mm.v("ph", "ps")
    mm.f("wph", "wff", "ph")
    mm.f("wps", "wff", "ps")
    with mm.block():
        mm.e("l1", "wff", ("ph",))
        mm.e("l2", "wff", ("(", "ph", "->", "ps", ")"))
        mm.a("ax-mp-local", "wff", ("ps",))
        mm.p("tlocal", "wff", ("ps",), proof=["wph", "wps", "l1", "l2", "ax-mp-local"])
    with mm.block():
        mm.e("g1", "wff", ("ph",))
        mm.e("g2", "wff", ("(", "ph", "->", "ps", ")"))
        mm.a("ax-mp", "wff", ("ps",))
        mm.p("th_out", "wff", ("ps",), proof=["wph", "wps", "g1", "g2", "ax-mp"])
    _write_and_verify(tmp_path, mm.render(), should_pass=True)


@pytest.mark.generated
def test_gen_06_scope_leakage_is_generator_error() -> None:
    mm = MMBuilder()
    mm.c("wff", "(", ")", "->")
    mm.v("ph", "ps")
    mm.f("wph", "wff", "ph")
    mm.f("wps", "wff", "ps")
    with mm.block():
        mm.e("l1", "wff", ("ph",))
        mm.e("l2", "wff", ("(", "ph", "->", "ps", ")"))
        mm.a("ax-mp-local", "wff", ("ps",))
        mm.p("tlocal", "wff", ("ps",), proof=["wph", "wps", "l1", "l2", "ax-mp-local"])
    # Using tlocal out of scope must raise at generator time
    with pytest.raises(MMDSLError):
        mm.p("th_bad", "wff", ("ps",), proof=["tlocal"])  # not visible


@pytest.mark.generated
def test_gen_06_scope_unbalanced_is_generator_error() -> None:
    mm = MMBuilder()
    mm.c("wff", "(", ")", "->")
    mm.v("ph", "ps")
    mm.f("wph", "wff", "ph")
    mm.f("wps", "wff", "ps")
    # simulate unbalanced scopes: push without pop then render
    mm._push_scope()
    with pytest.raises(MMDSLError):
        _ = mm.render()


# 07 linking-like cases (without a real linker)
@pytest.mark.generated
def test_gen_07_two_units_happy(tmp_path: Path) -> None:
    mm = MMBuilder()
    mm.c("wff", "(", ")", "->")
    mm.v("ph", "ps")
    mm.f("wph", "wff", "ph")
    mm.f("wps", "wff", "ps")
    # unit mp
    mm.a("ax-mp", "wff", ("ps",))
    # unit thm
    with mm.block():
        mm.p("t_from_units", "wff", ("ps",), proof=["wps", "ax-mp"])
    _write_and_verify(tmp_path, mm.render(), should_pass=True)


@pytest.mark.generated
def test_gen_07_cycle_is_generator_error() -> None:
    mm = MMBuilder()
    mm.c("wff")
    # forward reference to an invisible label must raise at generation time
    with mm.block():
        with pytest.raises(MMDSLError):
            mm.p("a_thm", "wff", ("ps",), proof=["b_thm"])  # b_thm not defined/visible here



@pytest.mark.generated
def test_gen_07_non_exported_label_ref_is_generator_error() -> None:
    mm = MMBuilder()
    mm.c("wff")
    mm.v("ps")
    mm.f("wps", "wff", "ps")
    with mm.block():
        mm.a("priv_helper", "wff", ("ps",))
    with pytest.raises(MMDSLError):
        mm.p("use_private", "wff", ("ps",), proof=["priv_helper"])  # not visible
