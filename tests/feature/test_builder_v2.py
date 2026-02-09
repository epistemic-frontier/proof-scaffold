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
