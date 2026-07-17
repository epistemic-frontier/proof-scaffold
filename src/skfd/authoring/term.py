from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from .ids import ConstructorId, OwnerId, SortId, VariableKindId

VariableScope: TypeAlias = Literal["declared", "schema", "local"]


@dataclass(frozen=True, slots=True)
class VariableRef:
    scope: VariableScope
    owner: OwnerId
    local_key: str
    kind: VariableKindId

    def __post_init__(self) -> None:
        if not self.local_key:
            raise ValueError("variable local_key must be non-empty")


@dataclass(frozen=True, slots=True)
class Var:
    variable: VariableRef
    sort: SortId


@dataclass(frozen=True, slots=True)
class App:
    constructor: ConstructorId
    arguments: tuple[Term, ...]
    sort: SortId


Term: TypeAlias = Var | App
