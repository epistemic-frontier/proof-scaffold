# scaffold/theorem.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theorem:
    """
    Python-side handle for an exported theorem.

    - fqname: fully-qualified name, e.g. "number_theory.sqrt2.sqrt2_irrational"
    - label: the Metamath label used in proof steps, e.g. "sqrt2irr"
    """

    fqname: str
    module_id: str
    name: str
    label: str

    def __repr__(self) -> str:
        return f"Theorem({self.fqname} -> {self.label})"


@dataclass(frozen=True)
class TheoremDef:
    """
    Resolved theorem definition loaded from mmdb manifests.
    """

    fqname: str
    module_id: str
    name: str
    label: str
    typecode: str
    expr: tuple[str, ...]
    requires: tuple[str, ...]
