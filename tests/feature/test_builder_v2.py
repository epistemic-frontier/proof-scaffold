import pytest

from skfd.builder_v2 import MMBuilderV2
from skfd.core.diag import LinkerDiagError
from skfd.core.lir import FloatingHyp
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.names import NameResolver


def _mk_mm(*, unit_id: str = "u", module_id: str = "m") -> MMBuilderV2:
    return MMBuilderV2(
        interner=SymbolInterner(),
        origin_table=OriginTable(),
        names=NameResolver(),
        unit_id=unit_id,
        origin_module_id=module_id,
    )


def test_builder_v2_auto_f_emits_single_floating_per_scope() -> None:
    mm = _mk_mm()
    wff = mm.sym.const("wff")
    ph = mm.sym.var("φ")

    ax1 = mm.sym.label("ax-1")
    ax2 = mm.sym.label("ax-2")
    mm.a(ax1, tc=wff, expr=[ph])
    mm.a(ax2, tc=wff, expr=[ph])

    unit: ProofUnitIR = mm.finish()
    floatings = [st for st in unit.lir_stmts if isinstance(st, FloatingHyp)]
    assert len(floatings) == 1


def test_builder_v2_auto_f_avoids_label_collision_with_statement_label() -> None:
    mm = _mk_mm()
    wff = mm.sym.const("wff")
    ph = mm.sym.var("φ")

    mm.a(mm.sym.label("wph"), tc=wff, expr=[ph])
    unit = mm.finish()
    floating_labels = [
        mm.interner.symbol_table()[st.label].local_name
        for st in unit.lir_stmts
        if isinstance(st, FloatingHyp)
    ]
    assert floating_labels == ["wph0"]


def test_builder_v2_rejects_bad_math_token_kind() -> None:
    mm = _mk_mm()
    wff = mm.sym.const("wff")
    bad = mm.sym.label("ax-1")
    with pytest.raises(LinkerDiagError) as e:
        mm.a(mm.sym.label("ax-2"), tc=wff, expr=[bad])
    assert e.value.diag.error_code == "E_BAD_MATH_TOKEN"


def test_builder_v2_duplicate_label_reports_first_origin() -> None:
    """Issue #3: E_DUPLICATE_LABEL must carry the first occurrence's origin ref."""
    mm = _mk_mm()
    wff = mm.sym.const("wff")
    ph = mm.sym.var("φ")

    # First definition
    mm.e(mm.sym.label("myhyp"), tc=wff, expr=[ph])

    # Duplicate — must report the first origin
    with pytest.raises(LinkerDiagError) as exc:
        mm.e(mm.sym.label("myhyp"), tc=wff, expr=[ph])
    diag = exc.value.diag
    assert diag.error_code == "E_DUPLICATE_LABEL"
    assert diag.primary_origin_ref >= 0, f"expected origin ref >=0, got {diag.primary_origin_ref}"
    assert len(diag.origin_chain) == 2
    assert diag.origin_chain[0]["role"] == "first_definition"
    assert diag.origin_chain[1]["role"] == "duplicate"
    assert diag.details["label"] == "myhyp"
    assert "first_origin_ref" in diag.details


def test_builder_v2_duplicate_label_includes_current_origin() -> None:
    """E_DUPLICATE_LABEL related_origin_refs must include the current call site."""
    mm = _mk_mm()
    wff = mm.sym.const("wff")
    ph = mm.sym.var("φ")

    mm.e(mm.sym.label("step1"), tc=wff, expr=[ph])
    with pytest.raises(LinkerDiagError) as exc:
        mm.e(mm.sym.label("step1"), tc=wff, expr=[ph])
    diag = exc.value.diag
    assert len(diag.related_origin_refs) >= 1


def test_builder_v2_suspect_label_warns_on_hyp() -> None:
    """Issue #4: lb.hyp(label='hyp') must emit RuntimeWarning."""
    import warnings
    mm = _mk_mm()
    wff = mm.sym.const("wff")
    ph = mm.sym.var("φ")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        mm.e(mm.sym.label("hyp"), tc=wff, expr=[ph])
    assert len(w) == 1
    assert "generic" in str(w[0].message)
    assert "hyp" in str(w[0].message)


def test_builder_v2_suspect_label_warns_on_h1_h2_h3() -> None:
    """Suspect labels 'h1', 'h2', 'h3' must also warn."""
    import warnings

    for name in ("h1", "h2", "h3"):
        mm = _mk_mm()
        wff = mm.sym.const("wff")
        ph = mm.sym.var("φ")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mm.e(mm.sym.label(name), tc=wff, expr=[ph])
        assert len(w) == 1, f"expected warning for {name!r}"


def test_builder_v2_scoped_label_does_not_warn() -> None:
    """Labels with scoping delimiter (e.g. 'pm2_37.1') must not warn."""
    import warnings
    mm = _mk_mm()
    wff = mm.sym.const("wff")
    ph = mm.sym.var("φ")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        mm.e(mm.sym.label("pm2_37.1"), tc=wff, expr=[ph])
    assert len(w) == 0, f"scoped label should not warn, got {[str(m.message) for m in w]}"
