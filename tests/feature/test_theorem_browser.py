from __future__ import annotations

from skfd.builder_v2 import MMBuilderV2
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.names import NameResolver
from skfd.web.theorem_browser import build_theorem_graph


def test_theorem_browser_builds_dependency_graph() -> None:
    ot = OriginTable()
    interner = SymbolInterner()
    mm = MMBuilderV2(
        interner=interner,
        origin_table=ot,
        names=NameResolver(),
        unit_id="u",
        origin_module_id="m",
    )

    tc = mm.sym.const("|-")
    ph = mm.sym.var("ph")

    wph = mm.sym.label("wph")
    ax1 = mm.sym.label("ax1")
    th1 = mm.sym.label("th1")

    mm.f(wph, tc=tc, var=ph)
    mm.a(ax1, tc=tc, expr=[ph])
    mm.p(th1, tc=tc, expr=[ph], proof=[ax1])

    unit = mm.finish()
    graph = build_theorem_graph(units=[unit], origin_table=ot, interner=interner)

    sid_by_label = {n.label: n.sid for n in graph.nodes}
    assert "ax1" in sid_by_label
    assert "th1" in sid_by_label

    th1_sid = sid_by_label["th1"]
    ax1_sid = sid_by_label["ax1"]
    assert graph.edges[th1_sid] == [ax1_sid]
    assert graph.reverse_edges[ax1_sid] == [th1_sid]

