# proof_scaffold/export.py
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, Sequence, Tuple

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
    expr: Tuple[str, ...]
    requires: Tuple[str, ...]


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
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data: Dict = json.load(f)
        if data.get("module") != module_id:
            raise ValueError(f"manifest module mismatch: {data.get('module')} vs {module_id}")
    else:
        data = {"module": module_id, "exports": {}}

    exports: Dict = data.setdefault("exports", {})
    exports[name] = asdict(rec)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)

    return Theorem(fqname=fqname, module_id=module_id, name=name, label=label)
