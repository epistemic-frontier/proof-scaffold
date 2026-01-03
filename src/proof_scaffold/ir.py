# proof_scaffold/ir.py
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

# Compatibility shim for existing tests and manual IR construction.
# Preferred representation is int ids; SymbolRef is tolerated by passes.
@dataclass(frozen=True)
class SymbolRef:
    name: str

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
    symbols: tuple[int | SymbolRef, ...]  # TokenSeq of CONST ids (compat: SymbolRef)
    origin: Origin | None = None


@dataclass(frozen=True)
class VarDecl:
    symbols: tuple[int | SymbolRef, ...]  # TokenSeq of VAR ids (compat: SymbolRef)
    origin: Origin | None = None


@dataclass(frozen=True)
class DisjointDecl:
    symbols: tuple[int | SymbolRef, ...]  # TokenSeq of VAR ids (compat: SymbolRef)
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
    typecode: int | SymbolRef  # CONST id
    var: int | SymbolRef       # VAR id
    origin: Origin | None = None


@dataclass(frozen=True)
class EssentialHyp:
    label: str
    typecode: int | SymbolRef
    expr: tuple[int | SymbolRef, ...]  # TokenSeq of ids (compat: SymbolRef)
    origin: Origin | None = None


@dataclass(frozen=True)
class Axiom:
    label: str
    typecode: int | SymbolRef
    expr: tuple[int | SymbolRef, ...]
    origin: Origin | None = None


@dataclass(frozen=True)
class Theorem:
    label: str
    typecode: int | SymbolRef
    expr: tuple[int | SymbolRef, ...]
    proof_tokens: tuple[int | SymbolRef, ...]  # TokenSeq of LABEL ids (compat)
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
    # When None, baseline v0 treats ALL $a/$p in this unit as exported (compat).
    # When provided (list), ONLY those listed are considered exported.
    exports: list[str] | None = None

    def name_of(self, tok_id: int) -> str:
        return self.symtab[tok_id]
