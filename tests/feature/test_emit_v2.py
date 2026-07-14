import io
from collections.abc import Mapping

import pytest

from skfd.authoring.emit import emit_axioms
from skfd.authoring.formula import Wff
from skfd.builder_v2 import MMBuilderV2
from skfd.core.diag import LinkerDiagError
from skfd.core.lir import Axiom, DisjointVar, FloatingHyp, ScopeEnter, ScopeExit
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver
from skfd.verifier import mmverify


class _Provider:
    def __init__(self, interner: SymbolInterner, axioms: Mapping[str, Wff]) -> None:
        self.interner = interner
        self._axioms = dict(axioms)

    def compile_axioms(self) -> Mapping[str, Wff]:
        return dict(self._axioms)


def test_emit_axioms_v2_uses_symbol_ids_and_auto_f() -> None:
    interner = SymbolInterner()
    mm = MMBuilderV2(
        interner=interner,
        origin_table=OriginTable(),
        names=NameResolver(),
        unit_id="u",
        origin_module_id="m",
    )
    wff = mm.sym.const("wff")
    ph = mm.sym.var("φ")

    provider = _Provider(interner, {"ax-1": Wff("wff", (ph,))})
    emit_axioms(mm, provider, typecode=wff)
    unit = mm.finish()

    assert any(isinstance(s, FloatingHyp) for s in unit.lir_stmts)
    assert any(isinstance(s, Axiom) for s in unit.lir_stmts)


def test_emit_axioms_scopes_and_normalizes_assertion_level_dv_pairs() -> None:
    interner = SymbolInterner()
    mm = MMBuilderV2(
        interner=interner,
        origin_table=OriginTable(),
        names=NameResolver(),
        unit_id="u",
        origin_module_id="m",
    )
    wff = mm.sym.const("wff")
    provable = mm.sym.const("|-")
    ph = mm.sym.var("ph")
    ps = mm.sym.var("ps")
    mm.f(mm.sym.label("wph"), tc=wff, var=ph)
    mm.f(mm.sym.label("wps"), tc=wff, var=ps)

    statement = Wff("wff", (ph, ps))
    provider = _Provider(
        interner,
        {"dv-ax": statement, "plain-ax": statement},
    )
    emit_axioms(
        mm,
        provider,
        typecode=provable,
        active_dv_pairs_by_label={"dv-ax": ((ps, ph), (ph, ps))},
    )

    stmts = mm.finish().lir_stmts
    dv_axiom = next(
        stmt
        for stmt in stmts
        if isinstance(stmt, Axiom)
        and interner.symbol_table()[stmt.label].local_name == "dv-ax"
    )
    plain_axiom = next(
        stmt
        for stmt in stmts
        if isinstance(stmt, Axiom)
        and interner.symbol_table()[stmt.label].local_name == "plain-ax"
    )
    dv_index = stmts.index(dv_axiom)
    plain_index = stmts.index(plain_axiom)

    assert isinstance(stmts[dv_index - 1], DisjointVar)
    assert stmts[dv_index - 1].vars == [ph, ps]
    assert isinstance(stmts[dv_index - 2], ScopeEnter)
    assert isinstance(stmts[dv_index + 1], ScopeExit)
    assert plain_index > dv_index + 1


def test_emit_axioms_rejects_unexpanded_dv_groups() -> None:
    interner = SymbolInterner()
    mm = MMBuilderV2(
        interner=interner,
        origin_table=OriginTable(),
        names=NameResolver(),
        unit_id="u",
        origin_module_id="m",
    )
    x = mm.sym.var("x")
    y = mm.sym.var("y")
    z = mm.sym.var("z")
    provider = _Provider(interner, {"bad": Wff("wff", (x, y, z))})

    with pytest.raises(LinkerDiagError) as excinfo:
        emit_axioms(
            mm,
            provider,
            active_dv_pairs_by_label={"bad": ((x, y, z),)},
        )
    assert excinfo.value.diag.error_code == "E_BAD_DISJOINT"


def test_emit_axioms_resolves_dv_map_by_final_remapped_label() -> None:
    interner = SymbolInterner()
    mm = MMBuilderV2(
        interner=interner,
        origin_table=OriginTable(),
        names=NameResolver(),
        unit_id="u",
        origin_module_id="m",
    )
    x = mm.sym.var("x")
    ph = mm.sym.var("ph")
    final_label = mm.sym.label("ax-5")

    emit_axioms(
        mm,
        _Provider(interner, {"AX5": Wff("wff", (x, ph))}),
        label_ids={"AX5": final_label},
        active_dv_pairs_by_label={"ax-5": ((x, ph),)},
    )

    stmts = mm.finish().lir_stmts
    assert any(isinstance(stmt, DisjointVar) for stmt in stmts)
    assert any(isinstance(stmt, Axiom) and stmt.label == final_label for stmt in stmts)


def test_emit_axioms_rejects_unconsumed_dv_map_label() -> None:
    interner = SymbolInterner()
    mm = MMBuilderV2(
        interner=interner,
        origin_table=OriginTable(),
        names=NameResolver(),
        unit_id="u",
        origin_module_id="m",
    )
    x = mm.sym.var("x")
    y = mm.sym.var("y")

    with pytest.raises(LinkerDiagError) as excinfo:
        emit_axioms(
            mm,
            _Provider(interner, {"known": Wff("wff", (x, y))}),
            active_dv_pairs_by_label={"typo": ((x, y),)},
        )

    assert excinfo.value.diag.error_code == "E_UNKNOWN_DV_LABEL"
    assert not any(isinstance(stmt, Axiom) for stmt in mm.finish().lir_stmts)


def test_setmm_predicate_dv_canary_labels_keep_their_source_contracts() -> None:
    interner = SymbolInterner()
    origin_table = OriginTable()
    mm = MMBuilderV2(
        interner=interner,
        origin_table=origin_table,
        names=NameResolver(),
        unit_id="predicate-dv-canaries",
        origin_module_id="m",
    )
    wff = mm.sym.const("wff")
    provable = mm.sym.const("|-")
    variables = {name: mm.sym.var(name) for name in ("ph", "ps", "x", "y")}
    for name, var in variables.items():
        mm.f(mm.sym.label(f"w{name}"), tc=wff, var=var)

    x = variables["x"]
    y = variables["y"]
    ph = variables["ph"]
    ps = variables["ps"]
    axioms = {
        "ax-5": Wff("wff", (x, ph)),
        "ax-11": Wff("wff", (x, y, ph)),
        "ax-12": Wff("wff", (x, y, ph)),
        "ax-13": Wff("wff", (x, y)),
        "ax6v": Wff("wff", (x, y)),
        "ax7v": Wff("wff", (x, y)),
        "ax8v": Wff("wff", (x, y)),
        "ax9v": Wff("wff", (x, y)),
        "ax12v": Wff("wff", (x, y, ph)),
        "ax5d": Wff("wff", (x, ps)),
    }
    emit_axioms(
        mm,
        _Provider(interner, axioms),
        typecode=provable,
        active_dv_pairs_by_label={
            "ax-5": ((x, ph),),
            "ax6v": ((x, y),),
            "ax7v": ((x, y),),
            "ax8v": ((x, y),),
            "ax9v": ((x, y),),
            "ax12v": ((x, y), (ph, y)),
            "ax5d": ((ps, x),),
        },
    )

    result = LinkerV1.link(
        units=[mm.finish()],
        origin_table=origin_table,
        interner=interner,
        conformance_level=1,
    )
    old_verbosity = mmverify.verbosity
    mmverify.verbosity = 0
    try:
        database = mmverify.MM()
        database.read(mmverify.toks(io.StringIO(result.mm_text)))
    finally:
        mmverify.verbosity = old_verbosity

    expected = {
        "ax-5": {("ph", "x")},
        "ax-11": set(),
        "ax-12": set(),
        "ax-13": set(),
        "ax6v": {("x", "y")},
        "ax7v": {("x", "y")},
        "ax8v": {("x", "y")},
        "ax9v": {("x", "y")},
        "ax12v": {("ph", "y"), ("x", "y")},
        "ax5d": {("ps", "x")},
    }
    for label, pairs in expected.items():
        assert database.labels[label][1][0] == pairs
