# proof_scaffold/ir.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Minimal IR per 004 (LIR mandatory, HIR optional). This is a bootstrap, COMPAT-friendly
# representation to let the generator produce structured IR while we still render
# human-readable .mm for fixtures and tests.

SymbolKind = Literal["CONST", "VAR", "LABEL"]
LabelKind = Literal["$f", "$e", "$a", "$p"]


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


@dataclass(frozen=True)
class SymbolRef:
    # Bootstrap: refer by local name; linker will globalize/relocate later.
    name: str


# LIR statements --------------------------------------------------------------

@dataclass(frozen=True)
class ConstDecl:
    symbols: tuple[SymbolRef, ...]
    origin: Origin | None = None


@dataclass(frozen=True)
class VarDecl:
    symbols: tuple[SymbolRef, ...]
    origin: Origin | None = None


@dataclass(frozen=True)
class DisjointDecl:
    symbols: tuple[SymbolRef, ...]
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
    typecode: SymbolRef
    var: SymbolRef
    origin: Origin | None = None


@dataclass(frozen=True)
class EssentialHyp:
    label: str
    typecode: SymbolRef
    expr: tuple[SymbolRef, ...]
    origin: Origin | None = None


@dataclass(frozen=True)
class Axiom:
    label: str
    typecode: SymbolRef
    expr: tuple[SymbolRef, ...]
    origin: Origin | None = None


@dataclass(frozen=True)
class Theorem:
    label: str
    typecode: SymbolRef
    expr: tuple[SymbolRef, ...]
    proof_tokens: tuple[SymbolRef, ...]
    origin: Origin | None = None


LIRStmt = ConstDecl | VarDecl | DisjointDecl | ScopeEnter | ScopeExit | FloatingHyp | EssentialHyp | Axiom | Theorem



@dataclass
class ProofUnitIR:
    unit_id: str
    lir: list[LIRStmt] = field(default_factory=list)
    origin: Origin | None = None
    # Optional explicit export list of label names ($a/$p) for this unit.
    # When None, baseline v0 treats ALL $a/$p in this unit as exported (compat).
    # When provided (list), ONLY those listed are considered exported.
    exports: list[str] | None = None
