# scaffold/ir.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, NewType, Protocol, runtime_checkable

# Minimal IR per 004/005 (LIR mandatory, HIR optional).
# ADR-0001 enforces: tokens are integer IDs, payloads are contiguous sequences,
# and passes must be layout-agnostic.

SymbolKind = Literal["CONST", "VAR", "LABEL"]
LabelKind = Literal["$f", "$e", "$a", "$p"]

# Runtime type for all tokens: int. We keep SymbolId alias for clarity.
SymbolId = NewType("SymbolId", int)

# NOTE: ADR-0001 requires tokens to be integer IDs.
# The old SymbolRef(name: str) compatibility shim is removed as part of the
# refactor towards layout-agnostic, contiguous, id-based token payloads.

@runtime_checkable
class TokenSeq(Protocol):
    def __len__(self) -> int: ...
    def __getitem__(self, idx: int) -> int: ...


@dataclass(frozen=True)
class Origin:
    module: str | None = None
    file: str | None = None
    line: int | None = None


@dataclass(frozen=True)
class SymbolDef:
    local_name: str
    kind: SymbolKind
    origin: Origin | None = None


# LIR statements --------------------------------------------------------------

@dataclass(frozen=True)
class ConstDecl:
    symbols: tuple[int, ...]  # TokenSeq of CONST ids
    origin: Origin | None = None


@dataclass(frozen=True)
class VarDecl:
    symbols: tuple[int, ...]  # TokenSeq of VAR ids
    origin: Origin | None = None


@dataclass(frozen=True)
class DisjointDecl:
    symbols: tuple[int, ...]  # TokenSeq of VAR ids
    origin: Origin | None = None


@dataclass(frozen=True)
class ScopeEnter:
    origin: Origin | None = None


@dataclass(frozen=True)
class ScopeExit:
    origin: Origin | None = None


@dataclass(frozen=True)
class FloatingHyp:
    label: str
    typecode: int  # CONST id
    var: int       # VAR id
    origin: Origin | None = None


@dataclass(frozen=True)
class EssentialHyp:
    label: str
    typecode: int
    expr: tuple[int, ...]  # TokenSeq of ids
    origin: Origin | None = None


@dataclass(frozen=True)
class Axiom:
    label: str
    typecode: int
    expr: tuple[int, ...]
    origin: Origin | None = None


@dataclass(frozen=True)
class Theorem:
    label: str
    typecode: int
    expr: tuple[int, ...]
    proof_tokens: tuple[int, ...]  # TokenSeq of LABEL ids
    # Debug Slice Path A support:
    # For each proof token, record the (stable) step_id it belongs to.
    # Length must equal len(proof_tokens) when present.
    proof_step_ids: tuple[int, ...] = ()
    origin: Origin | None = None


LIRStmt = ConstDecl | VarDecl | DisjointDecl | ScopeEnter | ScopeExit | FloatingHyp | EssentialHyp | Axiom | Theorem


@dataclass
class ProofUnitIR:
    unit_id: str
    lir: list[LIRStmt] = field(default_factory=list)
    origin: Origin | None = None
    # String table (contiguous) for id -> token name mapping (shared id space).
    # Index is the integer token id used in LIR payloads.
    symtab: tuple[str, ...] = field(default_factory=tuple)
    # Optional explicit export list of label names ($a/$p) for this unit.
    # When None, baseline v0-archive treats ALL $a/$p in this unit as exported (compat).
    # When provided (list), ONLY those listed are considered exported.
    exports: list[str] | None = None

    # -----------------
    # COMPAT (M1.3 Stage 4.5 bootstrap)
    # -----------------
    # In explicit COMPAT builds, when proof closure cannot be computed,
    # the generator may provide a coarse unit-level dependency hint.
    # This must never become default-on behavior.
    dependencies_hint_unit_ids: list[str] | None = None

    # Optional debug metadata for SPEC-0001 (Debug Slice MVP)
    # For a theorem label L, theorem_proof_span[L] provides the (start,end)
    # span of its proof tokens within the *linearized proof token stream*.
    # In current Linker v0-archive, each theorem is emitted once and we treat the proof
    # token index (1-based) reported by the verifier as indexing into this
    # linear stream. This enables a usable debug slice without introducing HIR.
    theorem_proof_span: dict[str, tuple[int, int]] = field(default_factory=dict)

    def name_of(self, tok_id: int) -> str:
        return self.symtab[tok_id]
