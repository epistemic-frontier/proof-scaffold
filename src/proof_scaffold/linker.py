# proof_scaffold/linker.py
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple

from .export import manifest_path
from .theorem import Theorem, TheoremDef


def _parse_fqname(fqname: str) -> Tuple[str, str]:
    """
    "a.b.c" -> ("a.b", "c")
    """
    parts = fqname.split(".")
    if len(parts) < 2:
        raise ValueError(f"invalid fqname: {fqname}")
    return ".".join(parts[:-1]), parts[-1]


@dataclass
class ResolveResult:
    ordered: List[TheoremDef]   # topo: deps first
    modules: List[str]          # module_id topo-ish (dedup)
    missing: List[str]          # missing fqnames


class Linker:
    def __init__(self, *, build_dir: str = "build/mmdb") -> None:
        self.build_dir = build_dir
        self._manifest_cache: Dict[str, Dict] = {}
        self._def_cache: Dict[str, TheoremDef] = {}

    def _load_manifest(self, module_id: str) -> Dict:
        if module_id in self._manifest_cache:
            return self._manifest_cache[module_id]
        path = manifest_path(self.build_dir, module_id)
        if not os.path.exists(path):
            raise FileNotFoundError(f"manifest not found for module '{module_id}': {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._manifest_cache[module_id] = data
        return data

    def _load_def(self, fqname: str) -> TheoremDef:
        if fqname in self._def_cache:
            return self._def_cache[fqname]

        module_id, name = _parse_fqname(fqname)
        mani = self._load_manifest(module_id)
        exports = mani.get("exports", {})
        if name not in exports:
            raise KeyError(f"export '{name}' not found in module '{module_id}'")

        rec = exports[name]
        d = TheoremDef(
            fqname=fqname,
            module_id=module_id,
            name=name,
            label=rec["label"],
            typecode=rec["typecode"],
            expr=tuple(rec["expr"]),
            requires=tuple(rec.get("requires", ())),
        )
        self._def_cache[fqname] = d
        return d

    def resolve(self, roots: Iterable[Theorem | str]) -> ResolveResult:
        """
        roots: iterable of Theorem handles or fqname strings.
        """
        root_fq = []
        for r in roots:
            root_fq.append(r.fqname if isinstance(r, Theorem) else r)

        graph: Dict[str, Tuple[str, ...]] = {}
        missing: List[str] = []

        def collect(fq: str) -> None:
            if fq in graph:
                return
            try:
                d = self._load_def(fq)
            except (FileNotFoundError, KeyError):
                missing.append(fq)
                graph[fq] = tuple()
                return
            graph[fq] = d.requires
            for dep in d.requires:
                collect(dep)

        for fq in root_fq:
            collect(fq)

        # topo sort: deps first
        indeg: Dict[str, int] = {k: 0 for k in graph.keys()}
        rev: Dict[str, List[str]] = {k: [] for k in graph.keys()}

        for u, deps in graph.items():
            for v in deps:
                if v not in indeg:
                    # if a dep is not collected due to missing, it will still be in graph already;
                    # but keep robust here
                    indeg[v] = 0
                    rev[v] = []
                indeg[u] += 1
                rev[v].append(u)

        queue = [k for k, d in indeg.items() if d == 0]
        queue.sort()

        ordered_fq: List[str] = []
        while queue:
            n = queue.pop(0)
            ordered_fq.append(n)
            for m in rev.get(n, []):
                indeg[m] -= 1
                if indeg[m] == 0:
                    queue.append(m)
                    queue.sort()

        # if cycle, fall back to deterministic order for debugging
        if len(ordered_fq) != len(indeg):
            ordered_fq = sorted(indeg.keys())

        ordered_defs: List[TheoremDef] = []
        modules: List[str] = []
        seen_mod: Set[str] = set()

        for fq in ordered_fq:
            if fq in missing:
                continue
            d = self._load_def(fq)
            ordered_defs.append(d)
            if d.module_id not in seen_mod:
                seen_mod.add(d.module_id)
                modules.append(d.module_id)

        return ResolveResult(ordered=ordered_defs, modules=modules, missing=missing)
