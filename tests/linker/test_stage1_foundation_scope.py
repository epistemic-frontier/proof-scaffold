from __future__ import annotations

import pytest

from skfd.core.diag import LinkerDiagError
from skfd.core.lir import Axiom, EssentialHyp, FloatingHyp, Theorem
from skfd.core.origin import OriginRecord, OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.api import LinkerV1


def _origins() -> tuple[OriginTable, int, int]:
    origins = OriginTable()
    orig_a = origins.intern(OriginRecord(module_id="A", file="a.py", line=1))
    orig_b = origins.intern(OriginRecord(module_id="B", file="b.py", line=1))
    return origins, orig_a, orig_b


def _base_symbols(
    interner: SymbolInterner, *, orig_ref: int
) -> tuple[int, int, int, int, int, int]:
    wff = interner.intern(
        origin_module_id="__prelude__",
        local_name="wff",
        kind="Const",
        origin_ref=orig_ref,
    )
    ph = interner.intern(
        origin_module_id="__prelude__",
        local_name="ph",
        kind="Var",
        origin_ref=orig_ref,
    )
    wph = interner.intern(
        origin_module_id="prelude",
        local_name="wph",
        kind="Label",
        origin_ref=orig_ref,
    )
    ax = interner.intern(
        origin_module_id="prelude",
        local_name="ax",
        kind="Label",
        origin_ref=orig_ref,
    )
    hyp = interner.intern(
        origin_module_id="ordinary",
        local_name="h",
        kind="Label",
        origin_ref=orig_ref,
    )
    th = interner.intern(
        origin_module_id="consumer",
        local_name="th",
        kind="Label",
        origin_ref=orig_ref,
    )
    return wff, ph, wph, ax, hyp, th


def test_foundation_floating_hypothesis_can_be_used_cross_unit() -> None:
    origins, orig_a, orig_b = _origins()
    interner = SymbolInterner()
    wff, ph, wph, ax, _hyp, th = _base_symbols(interner, orig_ref=orig_a)

    foundation = ProofUnitIR(
        unit_id="metamath-prelude",
        origin_ref=orig_a,
        origin_module_id="prelude",
        lir_stmts=[
            FloatingHyp(stmt_id=1, origin_ref=orig_a, label=wph, typecode=wff, var=ph),
            Axiom(stmt_id=2, origin_ref=orig_a, label=ax, typecode=wff, expr=[ph]),
        ],
        exports=[wph, ax],
        kind="foundation",
    )
    consumer = ProofUnitIR(
        unit_id="consumer",
        origin_ref=orig_b,
        origin_module_id="consumer",
        lir_stmts=[
            Theorem(
                stmt_id=1,
                origin_ref=orig_b,
                label=th,
                typecode=wff,
                expr=[ph],
                proof=[wph, ax],
            )
        ],
        exports=[th],
    )

    result = LinkerV1.link(
        units=[consumer, foundation],
        origin_table=origins,
        interner=interner,
        conformance_level=1,
    )

    assert result.mm_text.index("wph $f") < result.mm_text.index("th $p")


def test_unexported_foundation_floating_hypothesis_is_rejected() -> None:
    origins, orig_a, orig_b = _origins()
    interner = SymbolInterner()
    wff, ph, wph, ax, _hyp, th = _base_symbols(interner, orig_ref=orig_a)

    foundation = ProofUnitIR(
        unit_id="metamath-prelude",
        origin_ref=orig_a,
        origin_module_id="prelude",
        lir_stmts=[
            FloatingHyp(stmt_id=1, origin_ref=orig_a, label=wph, typecode=wff, var=ph),
            Axiom(stmt_id=2, origin_ref=orig_a, label=ax, typecode=wff, expr=[ph]),
        ],
        exports=[ax],
        kind="foundation",
    )
    consumer = ProofUnitIR(
        unit_id="consumer",
        origin_ref=orig_b,
        origin_module_id="consumer",
        lir_stmts=[
            Theorem(
                stmt_id=1,
                origin_ref=orig_b,
                label=th,
                typecode=wff,
                expr=[ph],
                proof=[wph, ax],
            )
        ],
        exports=[th],
    )

    with pytest.raises(LinkerDiagError) as exc_info:
        LinkerV1.link(
            units=[foundation, consumer],
            origin_table=origins,
            interner=interner,
            conformance_level=1,
        )

    assert exc_info.value.diag.error_code == "E_SYMBOL_NOT_EXPORTED"
    assert exc_info.value.diag.details["export_class"] == "foundation_hypothesis"


def test_ordinary_floating_hypothesis_export_cannot_leak_cross_unit() -> None:
    origins, orig_a, orig_b = _origins()
    interner = SymbolInterner()
    wff, ph, wph, _ax, _hyp, th = _base_symbols(interner, orig_ref=orig_a)

    provider = ProofUnitIR(
        unit_id="ordinary",
        origin_ref=orig_a,
        origin_module_id="ordinary",
        lir_stmts=[
            FloatingHyp(stmt_id=1, origin_ref=orig_a, label=wph, typecode=wff, var=ph),
        ],
        exports=[wph],
    )
    consumer = ProofUnitIR(
        unit_id="consumer",
        origin_ref=orig_b,
        origin_module_id="consumer",
        lir_stmts=[
            Theorem(
                stmt_id=1,
                origin_ref=orig_b,
                label=th,
                typecode=wff,
                expr=[ph],
                proof=[wph],
            )
        ],
        exports=[th],
    )

    with pytest.raises(LinkerDiagError) as exc_info:
        LinkerV1.link(
            units=[provider, consumer],
            origin_table=origins,
            interner=interner,
            conformance_level=1,
        )

    assert exc_info.value.diag.error_code == "E_HYPOTHESIS_LEAKAGE"
    assert exc_info.value.diag.details["export_class"] == "internal_hypothesis"


def test_ordinary_essential_hypothesis_export_cannot_leak_cross_unit() -> None:
    origins, orig_a, orig_b = _origins()
    interner = SymbolInterner()
    wff, ph, _wph, _ax, hyp, th = _base_symbols(interner, orig_ref=orig_a)

    provider = ProofUnitIR(
        unit_id="ordinary",
        origin_ref=orig_a,
        origin_module_id="ordinary",
        lir_stmts=[
            EssentialHyp(stmt_id=1, origin_ref=orig_a, label=hyp, typecode=wff, expr=[ph]),
        ],
        exports=[hyp],
    )
    consumer = ProofUnitIR(
        unit_id="consumer",
        origin_ref=orig_b,
        origin_module_id="consumer",
        lir_stmts=[
            Theorem(
                stmt_id=1,
                origin_ref=orig_b,
                label=th,
                typecode=wff,
                expr=[ph],
                proof=[hyp],
            )
        ],
        exports=[th],
    )

    with pytest.raises(LinkerDiagError) as exc_info:
        LinkerV1.link(
            units=[provider, consumer],
            origin_table=origins,
            interner=interner,
            conformance_level=1,
        )

    assert exc_info.value.diag.error_code == "E_HYPOTHESIS_LEAKAGE"
    assert exc_info.value.diag.details["stmt_class"] == "essential"


def test_multiple_foundation_units_are_rejected() -> None:
    origins, orig_a, _orig_b = _origins()
    interner = SymbolInterner()
    wff, ph, wph, _ax, _hyp, _th = _base_symbols(interner, orig_ref=orig_a)

    foundation_a = ProofUnitIR(
        unit_id="foundation-a",
        origin_ref=orig_a,
        origin_module_id="foundation_a",
        lir_stmts=[
            FloatingHyp(stmt_id=1, origin_ref=orig_a, label=wph, typecode=wff, var=ph),
        ],
        exports=[wph],
        kind="foundation",
    )
    foundation_b = ProofUnitIR(
        unit_id="foundation-b",
        origin_ref=orig_a,
        origin_module_id="foundation_b",
        lir_stmts=[],
        exports=[],
        kind="foundation",
    )

    with pytest.raises(LinkerDiagError) as exc_info:
        LinkerV1.link(
            units=[foundation_a, foundation_b],
            origin_table=origins,
            interner=interner,
            conformance_level=1,
        )

    assert exc_info.value.diag.error_code == "E_MULTIPLE_FOUNDATIONS"
