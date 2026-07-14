from __future__ import annotations

import io

import pytest

from skfd.builder_v2 import MMBuilderV2
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver
from skfd.verifier import mmverify


def _build_cross_unit_dv_example(
    *, consumer_has_local_dv: bool
) -> tuple[str, int, int, int, int]:
    """Link two ordinary units whose variables intentionally share local names."""
    interner = SymbolInterner()
    origin_table = OriginTable()
    names = NameResolver()

    provider = MMBuilderV2(
        interner=interner,
        origin_table=origin_table,
        names=names,
        unit_id="provider:dv",
        origin_module_id="provider",
    )
    wff = provider.sym.const("wff")
    provider_x = provider.sym.var("x")
    provider_y = provider.sym.var("y")
    provider_axiom = provider.sym.label("ax-dv")
    with provider.block():
        provider.d(provider_x, provider_y)
        provider.a(provider_axiom, tc=wff, expr=[provider_x, provider_y])
    provider.export(provider_axiom)

    consumer = MMBuilderV2(
        interner=interner,
        origin_table=origin_table,
        names=names,
        unit_id="consumer:dv",
        origin_module_id="consumer",
    )
    consumer_x = consumer.sym.var("x")
    consumer_y = consumer.sym.var("y")
    consumer_fx = consumer.sym.label("wx")
    consumer_fy = consumer.sym.label("wy")
    consumer.f(consumer_fx, tc=wff, var=consumer_x)
    consumer.f(consumer_fy, tc=wff, var=consumer_y)
    if consumer_has_local_dv:
        consumer.d(consumer_x, consumer_y)
    consumer_theorem = consumer.sym.label("th-dv")
    consumer.p(
        consumer_theorem,
        tc=wff,
        expr=[consumer_x, consumer_y],
        proof=[consumer_fx, consumer_fy, provider_axiom],
    )
    consumer.export(consumer_theorem)

    result = LinkerV1.link(
        # Reverse dependency order to ensure this exercises module ordering too.
        units=[consumer.finish(), provider.finish()],
        origin_table=origin_table,
        interner=interner,
        conformance_level=1,
    )
    return (
        result.mm_text,
        provider_x,
        provider_y,
        consumer_x,
        consumer_y,
    )


def _read_mm(mm_text: str) -> mmverify.MM:
    old_verbosity = mmverify.verbosity
    mmverify.verbosity = 0
    try:
        database = mmverify.MM()
        database.read(mmverify.toks(io.StringIO(mm_text)))
        return database
    finally:
        mmverify.verbosity = old_verbosity


def test_cross_unit_dv_contract_accepts_consumer_local_disjoint() -> None:
    mm_text, *_ = _build_cross_unit_dv_example(consumer_has_local_dv=True)

    database = _read_mm(mm_text)

    assert "ax-dv" in database.labels
    assert "th-dv" in database.labels


def test_cross_unit_dv_contract_rejects_missing_consumer_local_disjoint() -> None:
    mm_text, *_ = _build_cross_unit_dv_example(consumer_has_local_dv=False)

    with pytest.raises(mmverify.MMError, match="disjoint violation"):
        _read_mm(mm_text)


def test_cross_unit_dv_relocation_keeps_formula_and_dv_endpoints_aligned() -> None:
    mm_text, provider_x, provider_y, consumer_x, consumer_y = (
        _build_cross_unit_dv_example(consumer_has_local_dv=True)
    )

    # Equal local names in different modules must remain distinct before linking.
    assert provider_x != consumer_x
    assert provider_y != consumer_y

    # Relocation applies identically to formula tokens and `$d` endpoints.
    assert "$d x y $." in mm_text
    assert "ax-dv $a wff x y $." in mm_text
    assert "$d x0 y0 $." in mm_text
    assert "th-dv $p wff x0 y0 $=" in mm_text

    database = _read_mm(mm_text)
    provider_contract = database.labels["ax-dv"][1]
    consumer_contract = database.labels["th-dv"][1]

    assert provider_contract[0] == {("x", "y")}
    assert provider_contract[3] == ["wff", "x", "y"]
    assert consumer_contract[0] == {("x0", "y0")}
    assert consumer_contract[3] == ["wff", "x0", "y0"]
