from __future__ import annotations

import ast as _ast
import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

from skfd.core.context import Context
from skfd.core.origin import OriginRecord, OriginTable
from skfd.core.symbols import SymbolDef, SymbolId, SymbolInterner
from skfd.core.unit import ProofUnitIR
from skfd.linker.api import LinkerV1
from skfd.linker.passes.stage1_resolve import run as stage1_run
from skfd.linker.passes.stage2_contracts import run as stage2_extract
from skfd.linker.passes.stage3_disjoint import run as stage3_enrich


AssertionKind = Literal["axiom", "theorem"]


@dataclass(frozen=True)
class AssertionNode:
    sid: int
    label: str
    kind: AssertionKind
    origin_module_id: str
    origin: OriginRecord | None
    docstring: str = ""
    wiki: str = ""


@dataclass(frozen=True)
class TheoremGraph:
    nodes: list[AssertionNode]
    edges: dict[int, list[int]]
    reverse_edges: dict[int, list[int]]

    def to_jsonable(self, *, project_root: Path | None) -> dict[str, Any]:
        def origin_json(o: OriginRecord | None) -> dict[str, Any] | None:
            if o is None:
                return None
            f = o.file
            if project_root is not None:
                try:
                    f = str(Path(f).resolve().relative_to(project_root.resolve()))
                except Exception:
                    pass
            return {"module": o.module_id, "file": f, "line": o.line}

        return {
            "nodes": [
                {
                    "sid": n.sid,
                    "label": n.label,
                    "kind": n.kind,
                    "origin_module_id": n.origin_module_id,
                    "origin": origin_json(n.origin),
                }
                for n in self.nodes
            ],
            "edges": {str(k): v for k, v in self.edges.items()},
            "reverse_edges": {str(k): v for k, v in self.reverse_edges.items()},
        }


@dataclass(frozen=True)
class MmContextBundle:
    mm_lines: list[str]
    label_to_line: dict[str, int]
    line_to_origin_ref: dict[int, int]
    origin_table: OriginTable


def build_theorem_graph(
    *,
    units: list[ProofUnitIR],
    origin_table: OriginTable,
    interner: SymbolInterner,
    conformance_level: int = 0,
    project_root: Path | None = None,
    wiki_dir: Path | None = None,
) -> TheoremGraph:
    ctx = Context(
        origin_table=origin_table, interner=interner, symtab=interner.symbol_table()
    )
    units1 = stage1_run(ctx=ctx, units=units, conformance_level=conformance_level)
    contracts = stage2_extract(units1, ctx.symtab)
    contracts = stage3_enrich(units1, ctx.symtab, contracts)

    symtab: dict[SymbolId, SymbolDef] = ctx.symtab
    assertion_ids = set(contracts.contracts.keys())
    theorem_ids = set(contracts.details.keys())

    def origin_for_sid(sid: SymbolId) -> OriginRecord | None:
        d = symtab.get(sid)
        if d is None:
            return None
        try:
            return origin_table.get(d.origin_ref)
        except Exception:
            return None

    nodes: list[AssertionNode] = []
    for sid in sorted(assertion_ids):
        sym_def = symtab.get(sid)
        if sym_def is None:
            continue
        kind: AssertionKind = "theorem" if sid in theorem_ids else "axiom"
        nodes.append(
            AssertionNode(
                sid=int(sid),
                label=sym_def.local_name,
                kind=kind,
                origin_module_id=sym_def.origin_module_id,
                origin=origin_for_sid(sid),
            )
        )

    edges: dict[int, list[int]] = {}
    for sid in assertion_ids:
        if sid not in theorem_ids:
            continue
        direct_deps = contracts.details[sid].direct_dependencies
        deps_filtered = sorted(
            int(dep) for dep in direct_deps if dep in assertion_ids and dep != sid
        )
        edges[int(sid)] = deps_filtered

    reverse_edges: dict[int, list[int]] = {int(sid): [] for sid in assertion_ids}
    for src, deps_list in edges.items():
        for dep_sid in deps_list:
            if dep_sid in reverse_edges:
                reverse_edges[dep_sid].append(src)
    for k in list(reverse_edges.keys()):
        reverse_edges[k] = sorted(set(reverse_edges[k]))

    nodes_by_id = {n.sid: n for n in nodes}
    edges = {k: v for k, v in edges.items() if k in nodes_by_id}
    reverse_edges = {k: v for k, v in reverse_edges.items() if k in nodes_by_id}

    # Load wiki entries
    if wiki_dir is not None and wiki_dir.exists():
        wiki_map: dict[str, str] = {}
        for f in sorted(wiki_dir.glob("*.md")):
            if f.name == "README.md":
                continue
            try:
                wiki_map[f.stem] = f.read_text(encoding="utf-8")
            except Exception:
                pass
        # Enrich nodes with wiki content
        for i, n in enumerate(nodes):
            if n.label in wiki_map:
                nodes[i] = AssertionNode(
                    sid=n.sid,
                    label=n.label,
                    kind=n.kind,
                    origin_module_id=n.origin_module_id,
                    origin=n.origin,
                    wiki=wiki_map[n.label],
                )
                nodes_by_id[n.sid] = nodes[i]
    # Extract docstrings from Python source files
    _loaded_files: dict[str, _ast.Module] = {}
    for i, n in enumerate(nodes):
        if n.origin is None or not n.origin.file.endswith(".py"):
            continue
        try:
            if n.origin.file not in _loaded_files:
                with open(n.origin.file, encoding="utf-8") as fh:
                    _loaded_files[n.origin.file] = _ast.parse(fh.read())
            tree = _loaded_files[n.origin.file]
            for node in _ast.walk(tree):
                if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                    if node.name == f"prove_{n.label.replace('.', '_')}":
                        doc = _ast.get_docstring(node)
                        if doc:
                            nodes[i] = AssertionNode(
                                sid=n.sid,
                                label=n.label,
                                kind=n.kind,
                                origin_module_id=n.origin_module_id,
                                origin=n.origin,
                                docstring=doc,
                                wiki=n.wiki,
                            )
                            nodes_by_id[n.sid] = nodes[i]
                        break
        except Exception:
            pass
    return TheoremGraph(nodes=nodes, edges=edges, reverse_edges=reverse_edges)


def build_mm_context_bundle(
    *,
    units: list[ProofUnitIR],
    origin_table: OriginTable,
    interner: SymbolInterner,
    conformance_level: int = 0,
) -> MmContextBundle:
    res = LinkerV1.link(
        units=units,
        origin_table=origin_table,
        interner=interner,
        conformance_level=conformance_level,
    )
    mm_lines = res.mm_text.splitlines()

    label_to_line: dict[str, int] = {}
    for idx, line in enumerate(mm_lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("$("):
            continue
        first = stripped.split()[0]
        if first and first not in label_to_line:
            label_to_line[first] = idx

    line_to_origin_ref: dict[int, int] = {}
    for e in res.source_map.entries:
        line_to_origin_ref[int(e.line)] = int(e.origin)

    return MmContextBundle(
        mm_lines=mm_lines,
        label_to_line=label_to_line,
        line_to_origin_ref=line_to_origin_ref,
        origin_table=origin_table,
    )


_INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>skfd theorem browser</title>
    <style>
      body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 16px; }
      #top { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
      input { padding: 8px; min-width: 320px; }
      button { padding: 8px 10px; }
      #main { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }
      #list { border: 1px solid #ddd; border-radius: 8px; padding: 12px; height: 78vh; overflow: auto; }
      #details { border: 1px solid #ddd; border-radius: 8px; padding: 12px; height: 78vh; overflow: auto; }
      .row { display: flex; gap: 10px; align-items: baseline; padding: 4px 0; border-bottom: 1px dotted #eee; }
      .lbl { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }
      .tag { font-size: 12px; color: #555; border: 1px solid #ddd; border-radius: 999px; padding: 1px 8px; }
      .muted { color: #666; font-size: 12px; }
      .link { cursor: pointer; color: #0a58ca; text-decoration: underline; }
      h2, h3 { margin: 10px 0 6px; }
      ul { margin: 6px 0 12px 18px; }
      pre { background: #f7f7f8; border-radius: 8px; padding: 10px; overflow: auto; }
      .docstring { background: #f0f7ff; border: 1px solid #c8e1ff; border-radius: 8px; padding: 12px; margin: 10px 0; white-space: pre-wrap; font-size: 0.9em; line-height: 1.6; }
      .wiki { background: #fafbfc; border: 1px solid #e1e4e8; border-radius: 8px; padding: 12px; margin: 10px 0; max-height: 400px; overflow: auto; white-space: pre-wrap; font-size: 0.9em; line-height: 1.6; }
      mark { background: #fff3cd; padding: 0 2px; }
      #mode { margin-left: 6px; padding: 4px; }
    </style>
  </head>
  <body>
    <div id="top">
      <div><strong>skfd theorem browser</strong></div>
      <input id="q" placeholder="filter label (substring)" /><select id="mode"><option value="label">label</option><option value="fulltext">wiki</option></select>
      <button id="reload">reload</button>
      <div id="status" class="muted"></div>
    </div>
    <div id="main">
      <div id="list"></div>
      <div id="details"><div class="muted">select an assertion</div></div>
    </div>
    <script>
      let graph = null;
      let nodeBySid = new Map();

      function esc(s) {
        return (s ?? "").toString().replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
      }

      function renderSearchResults(results, q) {
        const container = document.getElementById("list");
        let html = '<div class="muted">results: ' + results.length + '</div>';
        for (const n of results) {
          const lower = (n._snippet || '').toLowerCase(); const idx = lower.indexOf(q); let s = (n._snippet || '').substring(0, 400); if (idx >= 0) { s = s.substring(0, idx) + '<mark>' + s.substring(idx, idx + q.length) + '</mark>' + s.substring(idx + q.length); }
          html += '<div class="row" style="padding:4px 0"><span class="lbl link" data-sid="' + n.sid + '">' + esc(n.label) + '</span><span class="tag">' + esc(n.kind) + '</span><span class="muted" style="font-size:0.85em;display:block">' + s + '</span></div>';
        }
        container.innerHTML = html;
        container.querySelectorAll('[data-sid]').forEach(el => el.addEventListener('click', () => showDetails(parseInt(el.getAttribute('data-sid'), 10))));
      }

      function setStatus(msg) {
        document.getElementById("status").textContent = msg;
      }

      function renderList() {
        const q = (document.getElementById("q").value || "").toLowerCase();
        const container = document.getElementById("list");
        if (!graph) {
          container.innerHTML = '<div class="muted">loading...</div>';
          return;
        }
        const mode = (document.getElementById('mode')?.value) || 'label';
        let nodes;
        if (mode === 'fulltext' && q) {
          fetch('/api/search?q=' + encodeURIComponent(q))
            .then(r => r.json())
            .then(data => {
              const sids = new Set(data.results.map(r => r.sid));
              nodes = graph.nodes.filter(n => sids.has(n.sid));
              const sorted = data.results.map(r => graph.nodes.find(x => x.sid === r.sid)).filter(Boolean);
              for (let i = 0; i < sorted.length; i++) {
                sorted[i]._snippet = data.results[i]?.snippet || '';
              }
              renderSearchResults(sorted, q);
            });
          return;
        }
        nodes = graph.nodes
          .filter(n => n.label.toLowerCase().includes(q))
          .sort((a, b) => a.label.localeCompare(b.label));

        let html = '';
        html += `<div class="muted">nodes: ${nodes.length} / ${graph.nodes.length}</div>`;
        for (const n of nodes) {
          const origin = n.origin ? `${n.origin.file}:${n.origin.line}` : '';
          html += '<div class="row">';
          html += `<span class="lbl link" data-sid="${n.sid}">${esc(n.label)}</span>`;
          html += `<span class="tag">${esc(n.kind)}</span>`;
          if (origin) html += `<span class="muted">${esc(origin)}</span>`;
          html += '</div>';
        }
        container.innerHTML = html;
        container.querySelectorAll('[data-sid]').forEach(el => {
          el.addEventListener('click', () => showDetails(parseInt(el.getAttribute('data-sid'), 10)));
        });
      }

      function formatNode(sid) {
        const n = nodeBySid.get(sid);
        if (!n) return `(unknown ${sid})`;
        return n.label;
      }

      function showDetails(sid) {
        const n = nodeBySid.get(sid);
        const container = document.getElementById("details");
        if (!n) {
          container.innerHTML = '<div class="muted">unknown node</div>';
          return;
        }
        const deps = (graph.edges[String(sid)] || []).slice();
        const rdeps = (graph.reverse_edges[String(sid)] || []).slice();
        const origin = n.origin ? `${n.origin.file}:${n.origin.line}` : '(no origin)';

        let html = '';
        html += `<h2 class="lbl">${esc(n.label)}</h2>`;
        html += `<div class="muted">sid=${sid} · ${esc(n.kind)} · ${esc(origin)}</div>`;
        html += `<h3>Direct Dependencies (${deps.length})</h3>`;
        if (deps.length === 0) {
          html += '<div class="muted">(none)</div>';
        } else {
          html += '<ul>';
          for (const d of deps) {
            html += `<li><span class="lbl link" data-sid="${d}">${esc(formatNode(d))}</span></li>`;
          }
          html += '</ul>';
        }
        html += `<h3>Reverse Dependencies (${rdeps.length})</h3>`;
        if (rdeps.length === 0) {
          html += '<div class="muted">(none)</div>';
        } else {
          html += '<ul>';
          for (const d of rdeps) {
            html += `<li><span class="lbl link" data-sid="${d}">${esc(formatNode(d))}</span></li>`;
          }
          html += '</ul>';
        }

        html += `<h3>MM Context</h3>`;
        html += `<div id="mmctx" class="muted">loading...</div>`;

        container.innerHTML = html;
        container.querySelectorAll('[data-sid]').forEach(el => {
          el.addEventListener('click', () => showDetails(parseInt(el.getAttribute('data-sid'), 10)));
        });
        history.replaceState(null, "", `#${sid}`);

        fetch(`/api/mm_context?sid=${sid}&context=6`).then(r => r.json()).then(data => {
          const slot = document.getElementById("mmctx");
          if (!slot) return;
          if (data.error) {
            slot.textContent = data.error;
            return;
          }
          const header = data.origin ? `${data.origin.file}:${data.origin.line}` : '(no origin)';
          const lines = (data.lines || []).map(x => `${String(x.no).padStart(6, ' ')}: ${x.text}`).join("\\n");
          slot.innerHTML = `<div class="muted">${esc(header)} · mm line ${data.mm_line}</div><pre>${esc(lines)}</pre>`;
        }).catch(e => {
          const slot = document.getElementById("mmctx");
          if (slot) slot.textContent = String(e);
        });
      }

      async function loadGraph() {
        setStatus("loading graph...");
        const res = await fetch("/api/graph");
        if (!res.ok) throw new Error(`GET /api/graph failed: ${res.status}`);
        graph = await res.json();
        nodeBySid = new Map(graph.nodes.map(n => [n.sid, n]));
        setStatus(`loaded ${graph.nodes.length} nodes`);
        renderList();
        const hash = (location.hash || "").slice(1);
        if (hash) {
          const sid = parseInt(hash, 10);
          if (!Number.isNaN(sid)) showDetails(sid);
        }
      }

      document.getElementById("q").addEventListener("input", renderList);
      document.getElementById("reload").addEventListener("click", loadGraph);

      loadGraph().catch(e => { setStatus(String(e)); console.error(e); });
    </script>
  </body>
</html>
"""


class _TheoremBrowserHandler(BaseHTTPRequestHandler):
    graph: TheoremGraph
    project_root: Path | None
    mm: MmContextBundle | None

    def _send_json(self, payload: Any, *, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, html: str, *, status: int = 200) -> None:
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        u = urlparse(self.path)
        if u.path == "/" or u.path == "/index.html":
            self._send_html(_INDEX_HTML)
            return

        if u.path == "/api/graph":
            self._send_json(self.graph.to_jsonable(project_root=self.project_root))
            return

        if u.path == "/api/search":
            q = parse_qs(u.query)
            query = (q.get("q") or [""])[0].lower()
            results = []
            for n in self.graph.nodes:
                score = 0
                if query and query in n.label.lower():
                    score += 10
                if n.wiki and query and query in n.wiki.lower():
                    score += 5
                if score > 0:
                    results.append(
                        {
                            "sid": n.sid,
                            "label": n.label,
                            "kind": n.kind,
                            "score": score,
                            "snippet": (n.wiki or "")[:300],
                        }
                    )
            results.sort(key=lambda x: x["score"], reverse=True)  # type: ignore[arg-type,return-value]
            self._send_json({"results": results[:50]})
            return

        if u.path == "/api/ping":
            self._send_json({"ok": True})
            return

        if u.path == "/api/node":
            q = parse_qs(u.query)
            sid_s = (q.get("sid") or [""])[0]
            try:
                sid = int(sid_s)
            except Exception:
                self._send_json({"error": "bad sid"}, status=400)
                return
            node = next((n for n in self.graph.nodes if n.sid == sid), None)
            if node is None:
                self._send_json({"error": "not found"}, status=404)
                return
            self._send_json(
                {
                    "node": {
                        "sid": node.sid,
                        "label": node.label,
                        "kind": node.kind,
                        "origin_module_id": node.origin_module_id,
                        "origin": None
                        if node.origin is None
                        else {
                            "module": node.origin.module_id,
                            "file": node.origin.file,
                            "line": node.origin.line,
                        },
                    },
                    "deps": self.graph.edges.get(sid, []),
                    "reverse_deps": self.graph.reverse_edges.get(sid, []),
                    "docstring": node.docstring,
                    "wiki": node.wiki,
                }
            )
            return

        if u.path == "/api/mm_context":
            if self.mm is None:
                self._send_json({"error": "mm context not available"}, status=404)
                return

            q = parse_qs(u.query)
            sid_s = (q.get("sid") or [""])[0]
            ctx_s = (q.get("context") or ["6"])[0]
            try:
                sid = int(sid_s)
                context = int(ctx_s)
            except Exception:
                self._send_json({"error": "bad params"}, status=400)
                return

            node = next((n for n in self.graph.nodes if n.sid == sid), None)
            if node is None:
                self._send_json({"error": "not found"}, status=404)
                return

            mm_line = self.mm.label_to_line.get(node.label)
            if mm_line is None:
                self._send_json({"error": "label not found in mm"}, status=404)
                return

            radius = max(0, min(context, 50))
            start = max(1, mm_line - radius)
            end = min(len(self.mm.mm_lines), mm_line + radius)

            origin_ref = self.mm.line_to_origin_ref.get(mm_line)
            origin = None
            if origin_ref is not None:
                try:
                    o = self.mm.origin_table.get(origin_ref)
                    origin = {"module": o.module_id, "file": o.file, "line": o.line}
                except Exception:
                    origin = None

            lines = [
                {"no": i, "text": self.mm.mm_lines[i - 1]}
                for i in range(start, end + 1)
            ]
            self._send_json(
                {
                    "sid": sid,
                    "label": node.label,
                    "mm_line": mm_line,
                    "origin": origin,
                    "start": start,
                    "end": end,
                    "lines": lines,
                }
            )
            return

        self._send_json({"error": "not found"}, status=404)


def serve(
    *,
    graph: TheoremGraph,
    mm: MmContextBundle | None = None,
    host: str,
    port: int,
    project_root: Path | None,
) -> None:
    handler = _TheoremBrowserHandler
    handler.graph = graph
    handler.project_root = project_root
    handler.mm = mm
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.serve_forever()
