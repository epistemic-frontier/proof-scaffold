# skfd/core/lir.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from .origin import OriginRef
from .symbols import SymbolId

StmtId = int
TokenSeq = list[int]


LIRStmt: TypeAlias = "ConstDecl | VarDecl | FloatingHyp | EssentialHyp | Axiom | Theorem | DisjointVar | Comment | ScopeEnter | ScopeExit"


@dataclass(frozen=True)
class ConstDecl:
    stmt_id: StmtId
    origin_ref: OriginRef
    tokens: TokenSeq


@dataclass(frozen=True)
class VarDecl:
    stmt_id: StmtId
    origin_ref: OriginRef
    tokens: TokenSeq


@dataclass(frozen=True)
class FloatingHyp:
    stmt_id: StmtId
    origin_ref: OriginRef
    label: SymbolId
    typecode: SymbolId
    var: SymbolId


@dataclass(frozen=True)
class EssentialHyp:
    stmt_id: StmtId
    origin_ref: OriginRef
    label: SymbolId
    typecode: SymbolId
    expr: TokenSeq


@dataclass(frozen=True)
class Axiom:
    stmt_id: StmtId
    origin_ref: OriginRef
    label: SymbolId
    typecode: SymbolId
    expr: TokenSeq


@dataclass(frozen=True)
class Theorem:
    stmt_id: StmtId
    origin_ref: OriginRef
    label: SymbolId
    typecode: SymbolId
    expr: TokenSeq
    proof: TokenSeq


@dataclass(frozen=True)
class DisjointVar:
    stmt_id: StmtId
    origin_ref: OriginRef
    vars: TokenSeq


@dataclass(frozen=True)
class Comment:
    stmt_id: StmtId
    origin_ref: OriginRef
    text: str


@dataclass(frozen=True)
class ScopeEnter:
    stmt_id: StmtId
    origin_ref: OriginRef
    kind: Literal["ScopeEnter"] = "ScopeEnter"


@dataclass(frozen=True)
class ScopeExit:
    stmt_id: StmtId
    origin_ref: OriginRef
    kind: Literal["ScopeExit"] = "ScopeExit"
