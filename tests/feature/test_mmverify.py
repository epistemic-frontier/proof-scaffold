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
