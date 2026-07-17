from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TypeVar

from ._canonical import JsonValue, canonical_digest
from .errors import AuthoringSemanticError
from .ids import ConstructorId, Digest, LanguageId, SortId, VariableKindId
from .term import App, Term, Var, VariableRef


@dataclass(frozen=True, slots=True, kw_only=True)
class SortDecl:
    id: SortId


@dataclass(frozen=True, slots=True, kw_only=True)
class VariableKindDecl:
    id: VariableKindId
    sort: SortId


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructorDecl:
    id: ConstructorId
    inputs: tuple[SortId, ...]
    output: SortId


@dataclass(frozen=True, slots=True, kw_only=True)
class LanguageRequirement:
    id: LanguageId
    semantic_digest: Digest | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class LanguageSpec:
    id: LanguageId
    extends: tuple[LanguageRequirement, ...] = ()
    sorts: tuple[SortDecl, ...] = ()
    variable_kinds: tuple[VariableKindDecl, ...] = ()
    constructors: tuple[ConstructorDecl, ...] = ()


@dataclass(frozen=True, slots=True)
class LanguageInterface:
    id: LanguageId
    semantic_digest: Digest
    sorts: Mapping[SortId, SortDecl] = field(compare=False, hash=False, repr=False)
    variable_kinds: Mapping[VariableKindId, VariableKindDecl] = field(compare=False, hash=False, repr=False)
    constructors: Mapping[ConstructorId, ConstructorDecl] = field(compare=False, hash=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sorts", MappingProxyType(dict(self.sorts)))
        object.__setattr__(self, "variable_kinds", MappingProxyType(dict(self.variable_kinds)))
        object.__setattr__(self, "constructors", MappingProxyType(dict(self.constructors)))

    def variable(self, variable: VariableRef) -> Var:
        kind = self.variable_kinds.get(variable.kind)
        if kind is None:
            raise AuthoringSemanticError(f"unknown variable kind: {variable.kind}")
        return Var(variable, kind.sort)

    def apply(self, constructor: ConstructorId, arguments: Iterable[Term]) -> App:
        declaration = self.constructors.get(constructor)
        if declaration is None:
            raise AuthoringSemanticError(f"unknown constructor: {constructor}")
        args = tuple(arguments)
        if len(args) != len(declaration.inputs):
            raise AuthoringSemanticError(
                f"constructor {constructor} expects {len(declaration.inputs)} arguments, got {len(args)}"
            )
        for index, (argument, expected) in enumerate(zip(args, declaration.inputs)):
            if argument.sort != expected:
                raise AuthoringSemanticError(
                    f"constructor {constructor} argument {index} expects {expected}, got {argument.sort}"
                )
        return App(constructor, args, declaration.output)


K = TypeVar("K")
V = TypeVar("V")


def _merge(target: dict[K, V], values: Iterable[V], key: Callable[[V], K]) -> None:
    for value in values:
        item_key = key(value)
        old = target.get(item_key)
        if old is not None and old != value:
            raise AuthoringSemanticError(f"conflicting declaration: {item_key}")
        target[item_key] = value


def _digest(sorts: Mapping[SortId, SortDecl], kinds: Mapping[VariableKindId, VariableKindDecl], constructors: Mapping[ConstructorId, ConstructorDecl]) -> Digest:
    document: dict[str, JsonValue] = {
        "constructors": [
            {
                "inputs": [str(item) for item in declaration.inputs],
                "id": str(declaration.id),
                "output": str(declaration.output),
            }
            for declaration in sorted(constructors.values(), key=lambda item: item.id)
        ],
        "sorts": [str(item) for item in sorted(sorts)],
        "variable_kinds": [
            {"id": str(item.id), "sort": str(item.sort)}
            for item in sorted(kinds.values(), key=lambda item: item.id)
        ],
        "version": "skfd.language.semantic.v1",
    }
    return canonical_digest(document)


def is_semantic_subset(candidate: LanguageInterface, target: LanguageInterface) -> bool:
    """Return whether every semantic declaration in candidate exists identically in target."""
    return (
        all(target.sorts.get(key) == value for key, value in candidate.sorts.items())
        and all(target.variable_kinds.get(key) == value for key, value in candidate.variable_kinds.items())
        and all(target.constructors.get(key) == value for key, value in candidate.constructors.items())
    )


def resolve_language(spec: LanguageSpec, dependencies: Mapping[LanguageId, LanguageInterface]) -> LanguageInterface:
    sorts: dict[SortId, SortDecl] = {}
    kinds: dict[VariableKindId, VariableKindDecl] = {}
    constructors: dict[ConstructorId, ConstructorDecl] = {}
    for requirement in sorted(spec.extends, key=lambda item: item.id):
        dependency = dependencies.get(requirement.id)
        if dependency is None:
            raise AuthoringSemanticError(f"missing language dependency: {requirement.id}")
        if requirement.semantic_digest is not None and requirement.semantic_digest != dependency.semantic_digest:
            raise AuthoringSemanticError(f"language digest mismatch: {requirement.id}")
        _merge(sorts, dependency.sorts.values(), lambda item: item.id)
        _merge(kinds, dependency.variable_kinds.values(), lambda item: item.id)
        _merge(constructors, dependency.constructors.values(), lambda item: item.id)
    _merge(sorts, spec.sorts, lambda item: item.id)
    _merge(kinds, spec.variable_kinds, lambda item: item.id)
    _merge(constructors, spec.constructors, lambda item: item.id)
    for kind in kinds.values():
        if kind.sort not in sorts:
            raise AuthoringSemanticError(f"variable kind {kind.id} has unknown sort: {kind.sort}")
    for constructor in constructors.values():
        for sort in (*constructor.inputs, constructor.output):
            if sort not in sorts:
                raise AuthoringSemanticError(f"constructor {constructor.id} has unknown sort: {sort}")
    return LanguageInterface(spec.id, _digest(sorts, kinds, constructors), sorts, kinds, constructors)
