from __future__ import annotations

from pathlib import Path

import pytest

from skfd.verifier import mmverify


def _write_mm(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_mmverify_minimal_proof(tmp_path: Path) -> None:
    mm_file = tmp_path / "t.mm"
    _write_mm(
        mm_file,
        """
$c wff $. 
$v ph $. 
wph $f wff ph $. 
ax1 $a wff ph $. 
th1 $p wff ph $= wph ax1 $. 
""",
    )

    mm = mmverify.MM()
    with mm_file.open() as f:
        mm.read(mmverify.toks(f))

    assert "th1" in mm.labels


def test_mmverify_error_stack_underflow(tmp_path: Path) -> None:
    mm_file = tmp_path / "bad.mm"
    _write_mm(
        mm_file,
        """
$c wff $. 
$v ph $. 
wph $f wff ph $. 
ax1 $a wff ph $. 
th1 $p wff ph $= ax1 $. 
""",
    )

    mm = mmverify.MM()
    with mm_file.open() as f:
        with pytest.raises(mmverify.MMError):
            mm.read(mmverify.toks(f))


def test_mmverify_disjoint_violation(tmp_path: Path) -> None:
    mm_file = tmp_path / "disj.mm"
    _write_mm(
        mm_file,
        """
$c wff |- ( ) -> $. 
$v ph ps $. 
wph $f wff ph $. 
wps $f wff ps $. 
$d ph ps $. 
ax1 $a wff ( ph -> ps ) $. 
# violate disjoint by substituting same var
th1 $p wff ( ph -> ph ) $= wph wph ax1 $. 
""",
    )

    mm = mmverify.MM()
    with mm_file.open() as f:
        with pytest.raises(mmverify.MMError):
            mm.read(mmverify.toks(f))


def test_mmverify_include_reads_file_once(tmp_path: Path) -> None:
    inc = tmp_path / "inc.mm"
    _write_mm(
        inc,
        """
$c wff $. 
""",
    )
    mm_file = tmp_path / "main.mm"
    _write_mm(
        mm_file,
        f"""
$[ {inc} $] 
$[ {inc} $] 
$v ph $. 
wph $f wff ph $. 
ax1 $a wff ph $. 
th1 $p wff ph $= wph ax1 $. 
""",
    )
    mm = mmverify.MM()
    with mm_file.open() as f:
        t = mmverify.toks(f)
        mm.read(t)
    assert len(t.imported_files) == 1


def test_mmverify_include_not_terminated_raises(tmp_path: Path) -> None:
    mm_file = tmp_path / "badinc.mm"
    _write_mm(
        mm_file,
        """
$[ x.mm $. 
""",
    )
    mm = mmverify.MM()
    with mm_file.open() as f:
        with pytest.raises(mmverify.MMError):
            mm.read(mmverify.toks(f))


def test_mmverify_eof_before_dot_raises(tmp_path: Path) -> None:
    mm_file = tmp_path / "eof.mm"
    _write_mm(
        mm_file,
        """
$c wff
""",
    )
    mm = mmverify.MM()
    with mm_file.open() as f:
        with pytest.raises(mmverify.MMError):
            mm.read(mmverify.toks(f))


def test_mmverify_const_redefined_raises(tmp_path: Path) -> None:
    mm_file = tmp_path / "redef.mm"
    _write_mm(
        mm_file,
        """
$c wff $. 
$c wff $. 
""",
    )
    mm = mmverify.MM()
    with mm_file.open() as f:
        with pytest.raises(mmverify.MMError):
            mm.read(mmverify.toks(f))


def test_mmverify_var_redefined_as_const_raises(tmp_path: Path) -> None:
    mm_file = tmp_path / "var_conflict.mm"
    _write_mm(
        mm_file,
        """
$c ph $. 
$v ph $. 
""",
    )
    mm = mmverify.MM()
    with mm_file.open() as f:
        with pytest.raises(mmverify.MMError):
            mm.read(mmverify.toks(f))


def test_mmverify_f_missing_label_raises(tmp_path: Path) -> None:
    mm_file = tmp_path / "f_nolabel.mm"
    _write_mm(
        mm_file,
        """
$c wff $. 
$v ph $. 
$f wff ph $. 
""",
    )
    mm = mmverify.MM()
    with mm_file.open() as f:
        with pytest.raises(mmverify.MMError):
            mm.read(mmverify.toks(f))


def test_mmverify_f_wrong_length_raises(tmp_path: Path) -> None:
    mm_file = tmp_path / "f_len.mm"
    _write_mm(
        mm_file,
        """
$c wff $. 
$v ph $. 
wph $f wff ph extra $. 
""",
    )
    mm = mmverify.MM()
    with mm_file.open() as f:
        with pytest.raises(mmverify.MMError):
            mm.read(mmverify.toks(f))


def test_mmverify_p_missing_proof_after_equals_raises(tmp_path: Path) -> None:
    mm_file = tmp_path / "p_missing_proof.mm"
    _write_mm(
        mm_file,
        """
$c wff $. 
$v ph $. 
wph $f wff ph $. 
ax1 $a wff ph $. 
th1 $p wff ph $. 
""",
    )
    mm = mmverify.MM()
    with mm_file.open() as f:
        with pytest.raises(mmverify.MMError):
            mm.read(mmverify.toks(f))


def test_mmverify_stack_has_more_than_one_entry_raises(tmp_path: Path) -> None:
    mm_file = tmp_path / "stack2.mm"
    _write_mm(
        mm_file,
        """
$c wff $. 
$v ph ps $. 
wph $f wff ph $. 
wps $f wff ps $. 
ax1 $a wff ph $. 
th1 $p wff ph $= wph wps $. 
""",
    )
    mm = mmverify.MM()
    with mm_file.open() as f:
        with pytest.raises(mmverify.MMError):
            mm.read(mmverify.toks(f))


def test_mmverify_compressed_proof(tmp_path: Path) -> None:
    mm_file = tmp_path / "compressed.mm"
    _write_mm(
        mm_file,
        """
$( a comment that should be skipped $)
$c wff $. 
$v ph $. 
wph $f wff ph $. 
ax1 $a wff ph $. 
th1 $p wff ph $= ( ax1 ) AB $. 
""",
    )
    mm = mmverify.MM()
    with mm_file.open() as f:
        mm.read(mmverify.toks(f))
    assert "th1" in mm.labels
