from __future__ import annotations

from dataclasses import dataclass, field

from ..ir import LIRStmt, Origin, ProofUnitIR


@dataclass
class UnitInfo:
    unit_id: str
    stmts: list[LIRStmt]
    labels: dict[str, str]  # name -> kind ("$f","$e","$a","$p")
    label_origin: dict[str, Origin | None]  # name -> origin
    uses_assertions: set[str]
    f_label_of_var: dict[str, str]
    f_order: list[str]
    assertion_stmt: dict[str, list[str]]
    exports: set[str] | None  # None means all exported
    unit_origin: Origin | None


@dataclass
class LinkContext:
    # Inputs
    units: list[ProofUnitIR]

    # Stage1_collect outputs
    infos: list[UnitInfo] = field(default_factory=list)
    global_consts: set[str] = field(default_factory=set)
    global_vars: set[str] = field(default_factory=set)
    label_owners: dict[str, set[str]] = field(default_factory=dict)  # label -> owners
    label_kind_by_unit: dict[tuple[str, str], str] = field(default_factory=dict)  # (unit,label)->kind
    exports_by_unit: dict[str, set[str] | None] = field(default_factory=dict)

    # Stage4 outputs
    ordered_infos: list[UnitInfo] = field(default_factory=list)

    # Stage6 outputs
    relabel: dict[tuple[str, str], str] = field(default_factory=dict)
