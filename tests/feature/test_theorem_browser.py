from __future__ import annotations

import tempfile
from pathlib import Path

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


def test_build_with_wiki_dir_enriches_nodes() -> None:
    """wiki_dir should load .md files and attach content to matching nodes."""
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
    mm.f(wph, tc=tc, var=ph)
    mm.a(ax1, tc=tc, expr=[ph])
    unit = mm.finish()

    with tempfile.TemporaryDirectory() as td:
        wiki_dir = Path(td)
        (wiki_dir / "README.md").write_text("readme")
        (wiki_dir / "ax1.md").write_text("# Axiom 1\nBasic axiom.")
        (wiki_dir / "nonexistent.md").write_text("orphan wiki")

        graph = build_theorem_graph(
            units=[unit], origin_table=ot, interner=interner, wiki_dir=wiki_dir
        )

        for n in graph.nodes:
            if n.label == "ax1":
                assert "# Axiom 1" in n.wiki
                break
        else:
            raise AssertionError("ax1 wiki not loaded")


def test_empty_wiki_dir_does_not_crash() -> None:
    """Missing or empty wiki_dir should not break the build."""
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
    mm.f(mm.sym.label("wph"), tc=tc, var=ph)
    mm.a(mm.sym.label("ax1"), tc=tc, expr=[ph])
    unit = mm.finish()

    # wiki_dir that doesn't exist
    graph = build_theorem_graph(
        units=[unit],
        origin_table=ot,
        interner=interner,
        wiki_dir=Path("/nonexistent/path"),
    )
    assert len(graph.nodes) >= 1

    # wiki_dir is None
    graph2 = build_theorem_graph(
        units=[unit],
        origin_table=ot,
        interner=interner,
        wiki_dir=None,
    )
    assert len(graph2.nodes) >= 1


def test_build_without_wiki_dir_still_works() -> None:
    """Backward compat: calling without wiki_dir should work."""
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
    mm.f(mm.sym.label("wph"), tc=tc, var=ph)
    mm.a(mm.sym.label("ax1"), tc=tc, expr=[ph])
    unit = mm.finish()

    graph = build_theorem_graph(units=[unit], origin_table=ot, interner=interner)
    for n in graph.nodes:
        assert n.wiki == ""  # no wiki without wiki_dir


def test_assertion_node_has_docstring_and_wiki_fields() -> None:
    """AssertionNode must have docstring and wiki fields initialized empty."""
    from skfd.web.theorem_browser import AssertionNode

    n = AssertionNode(
        sid=1, label="test", kind="axiom", origin_module_id="m", origin=None
    )
    assert n.docstring == ""
    assert n.wiki == ""
