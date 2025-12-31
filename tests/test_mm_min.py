# tests/test_mm_min.py
from pathlib import Path

from proof_scaffold.mm_min import load_mm_min, required_f_labels


def test_required_f_labels_order():
    db = load_mm_min(Path("fixtures/sanity/03_mandatory_f.mm"))
    assert required_f_labels(db, "ax-1") == ["wph", "wps"]
