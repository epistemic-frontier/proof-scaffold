from __future__ import annotations

import pytest

from skfd.core.diag import LinkerDiagError
from skfd.examples import minimal_diag, minimal_ok


def test_skfd_examples_minimal_ok_run_emits_mm() -> None:
    mm_text = minimal_ok.run()
    assert isinstance(mm_text, str)
    assert "th1 $p" in mm_text


def test_skfd_examples_minimal_diag_raises_reserved_token() -> None:
    with pytest.raises(LinkerDiagError) as e:
        minimal_diag.run()
    assert e.value.diag.error_code == "E_RESERVED_TOKEN_NAME"

