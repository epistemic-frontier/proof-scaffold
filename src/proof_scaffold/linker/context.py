from __future__ import annotations

from dataclasses import dataclass, field

from ..ir import LIRStmt, Origin, ProofUnitIR


@dataclass
class UnitInfo:
    unit_id: str
    stmts: list[LIRStmt]
    symtab: tuple[str, ...]
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

    # Debug slice metadata (SPEC-0001 Path B):
    # A global linearized proof token stream (after relocation name rewriting)
    # for the linked artifact.
    proof_tokens: list[str] = field(default_factory=list)
    # Map (unit_id, theorem_label) -> (start,end) span into proof_tokens
    theorem_to_span: dict[tuple[str, str], tuple[int, int]] = field(default_factory=dict)

    # Path A sidecar mapping: emitted proof token index (1-based) -> step_id.
    # Indexing is aligned with verifier's "Step N failed" when the verifier
    # reports proof-step indices.
    emitted_step_to_step_id: dict[int, int] = field(default_factory=dict)
