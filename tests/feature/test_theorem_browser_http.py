from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from contextlib import closing

from skfd.builder_v2 import MMBuilderV2
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.names import NameResolver
from skfd.web import theorem_browser


def _http_get_json(url: str) -> dict:
    try:
        with closing(urllib.request.urlopen(url, timeout=5)) as resp:
            data = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        data = e.read().decode("utf-8")
    return json.loads(data)


def _http_get_text(url: str) -> str:
    with closing(urllib.request.urlopen(url, timeout=5)) as resp:
        return resp.read().decode("utf-8")


def test_theorem_browser_http_endpoints() -> None:
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
    ax1 = mm.sym.label("ax1")
    th1 = mm.sym.label("th1")
    wph = mm.sym.label("wph")

    mm.f(wph, tc=tc, var=ph)
    mm.a(ax1, tc=tc, expr=[ph])
    mm.p(th1, tc=tc, expr=[ph], proof=[ax1])
    unit = mm.finish()

    graph = theorem_browser.build_theorem_graph(
        units=[unit], origin_table=ot, interner=interner
    )
    mm = theorem_browser.build_mm_context_bundle(
        units=[unit], origin_table=ot, interner=interner
    )

    handler = theorem_browser._TheoremBrowserHandler
    handler.graph = graph
    handler.project_root = None
    handler.mm = mm

    def quiet(self, *_a, **_k):
        return None

    handler.log_message = quiet  # type: ignore[method-assign]

    httpd = theorem_browser.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    host, port = httpd.server_address
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    try:
        base = f"http://{host}:{port}"
        html = _http_get_text(base + "/")
        assert "skfd theorem browser" in html

        g = _http_get_json(base + "/api/graph")
        assert "nodes" in g and "edges" in g and "reverse_edges" in g
        assert any(n["label"] == "th1" for n in g["nodes"])

        sid_by_label = {n["label"]: n["sid"] for n in g["nodes"]}
        th1_sid = sid_by_label["th1"]
        ax1_sid = sid_by_label["ax1"]

        n = _http_get_json(base + f"/api/node?sid={th1_sid}")
        assert n["node"]["label"] == "th1"
        assert n["deps"] == [ax1_sid]

        ctx = _http_get_json(base + f"/api/mm_context?sid={th1_sid}&context=2")
        assert ctx["label"] == "th1"
        assert isinstance(ctx["mm_line"], int)
        assert any("th1" in ln["text"] for ln in ctx["lines"])

        err = _http_get_json(base + "/api/node?sid=not-an-int")
        assert err["error"] == "bad sid"

        nf = _http_get_json(base + "/does-not-exist")
        assert nf["error"] == "not found"
    finally:
        httpd.shutdown()
        httpd.server_close()
