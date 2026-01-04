from __future__ import annotations

from dataclasses import dataclass, field

from proof_scaffold.ir import LIRStmt, Origin, ProofUnitIR


@dataclass(frozen=True)
class FrameStmt:
    """A statement inside a planned scope frame.

    We keep stmt itself as LIRStmt (tokens remain int ids), and add a
    synthetic_tag for debug/traceability (e.g. "ScopeEnter", "ScopeExit").
    """

    stmt: LIRStmt
    origin: Origin | None
    synthetic_tag: str | None = None


@dataclass(frozen=True)
class ScopeFramePlan:
    frame_id: int
    unit_id: str
    origin_ref: Origin | None
    context_hash: int
    stmts: tuple[FrameStmt, ...]


@dataclass(frozen=True)
class LinearPlan:
    prologue_stmts: tuple[FrameStmt, ...] = ()
    frames: tuple[ScopeFramePlan, ...] = ()


@dataclass(frozen=True)
class UseEdgeProvenance:
    """Provenance for an edge induced by a proof token.

    This is intentionally minimal for M1.3: enough to make missing-dep/cycle
    diagnostics actionable.
    """

    used_label: str
    ref_origin: Origin | None
    ref_stmt_label: str | None = None
    proof_step_idx: int | None = None


@dataclass
class UnitInfo:
    unit_id: str
    stmts: list[LIRStmt]
    symtab: tuple[str, ...]
    labels: dict[str, str]  # name -> kind ("$f","$e","$a","$p")
    label_origin: dict[str, Origin | None]  # name -> origin
    # Extracted from resolved proof tokens ($a/$p only). Stored as a stable,
    # sorted list to guarantee determinism.
    uses_assertions: tuple[str, ...]
    f_label_of_var: dict[str, str]
    f_order: list[str]
    assertion_stmt: dict[str, list[str]]
    exports: set[str] | None  # None means all exported
    unit_origin: Origin | None
    # For each used label, retain at least one provenance record.
    # Must come after non-default fields to satisfy dataclass init ordering.
    uses_provenance: dict[str, UseEdgeProvenance] = field(default_factory=dict)


@dataclass
class LinkContext:
    # Inputs
    units: list[ProofUnitIR]

    # Policy flags
    compat: bool = False

    # Stage1_collect outputs
    infos: list[UnitInfo] = field(default_factory=list)
    global_consts: set[str] = field(default_factory=set)
    global_vars: set[str] = field(default_factory=set)
    label_owners: dict[str, set[str]] = field(default_factory=dict)  # label -> owners
    label_kind_by_unit: dict[tuple[str, str], str] = field(default_factory=dict)  # (unit,label)->kind
    exports_by_unit: dict[str, set[str] | None] = field(default_factory=dict)

    # Stage4 outputs
    ordered_infos: list[UnitInfo] = field(default_factory=list)

    # Stage5 outputs
    linear_plan: LinearPlan | None = None

    # Stage5 notes (non-fatal diagnostics)
    lint_notes: list[dict[str, object]] = field(default_factory=list)

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
