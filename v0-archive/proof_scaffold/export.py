# scaffold/export.py
from __future__ import annotations

import json
import os
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from .theorem import Theorem


def _safe_module_filename(module_id: str) -> str:
    # "number_theory.sqrt2" -> "number_theory__sqrt2"
    return module_id.replace("/", "__").replace("\\", "__").replace(".", "__")


def manifest_path(build_dir: str, module_id: str) -> str:
    os.makedirs(build_dir, exist_ok=True)
    return os.path.join(build_dir, f"{_safe_module_filename(module_id)}.mm.json")


@dataclass
class ExportRecord:
    label: str
    typecode: str
    expr: tuple[str, ...]
    requires: tuple[str, ...]


def export(
    *,
    module_id: str,
    name: str,
    label: str,
    typecode: str,
    expr: Sequence[str],
    requires: Iterable[str] = (),
    build_dir: str = "build/mmdb",
) -> Theorem:
    """
    Export a theorem interface into a manifest JSON and return a Python handle.

    - module_id: namespace, e.g. "number_theory.sqrt2"
    - name: public name within module, e.g. "sqrt2_irrational"
    - label: Metamath label, e.g. "sqrt2irr"
    - requires: iterable of theorem fqnames this theorem depends on
    """
    fqname = f"{module_id}.{name}"
    rec = ExportRecord(
        label=label,
        typecode=typecode,
        expr=tuple(expr),
        requires=tuple(requires),
    )

    path = manifest_path(build_dir, module_id)
    data: dict[str, Any]
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("module") != module_id:
            raise ValueError(f"manifest module mismatch: {data.get('module')} vs {module_id}")
        # ensure format_version exists
        if "format_version" not in data:
            data["format_version"] = "mmdb@2"
    else:
        data = {"module": module_id, "format_version": "mmdb@2", "exports": {}}


    exports: dict[str, Any] = data.setdefault("exports", {})
    exports[name] = asdict(rec)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)

    return Theorem(fqname=fqname, module_id=module_id, name=name, label=label)
