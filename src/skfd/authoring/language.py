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
class BinderDecl:
    constructor: ConstructorId
    variable_argument: int
    scoped_arguments: tuple[int, ...]


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
    binders: tuple[BinderDecl, ...] = ()


@dataclass(frozen=True, slots=True)
class LanguageInterface:
    id: LanguageId
    semantic_digest: Digest
    sorts: Mapping[SortId, SortDecl] = field(compare=False, hash=False, repr=False)
    variable_kinds: Mapping[VariableKindId, VariableKindDecl] = field(compare=False, hash=False, repr=False)
    constructors: Mapping[ConstructorId, ConstructorDecl] = field(compare=False, hash=False, repr=False)
    binders: Mapping[ConstructorId, BinderDecl] = field(
        default_factory=dict,
        compare=False,
        hash=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "sorts", MappingProxyType(dict(self.sorts)))
        object.__setattr__(self, "variable_kinds", MappingProxyType(dict(self.variable_kinds)))
        object.__setattr__(self, "constructors", MappingProxyType(dict(self.constructors)))
        object.__setattr__(self, "binders", MappingProxyType(dict(self.binders)))

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
        binder = self.binders.get(constructor)
        if binder is not None and not isinstance(args[binder.variable_argument], Var):
            raise AuthoringSemanticError(
                f"binder {constructor} argument {binder.variable_argument} must be a variable"
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


def _digest(
    sorts: Mapping[SortId, SortDecl],
    kinds: Mapping[VariableKindId, VariableKindDecl],
    constructors: Mapping[ConstructorId, ConstructorDecl],
    binders: Mapping[ConstructorId, BinderDecl],
) -> Digest:
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
        "binders": [
            {
                "constructor": str(item.constructor),
                "variable_argument": item.variable_argument,
                "scoped_arguments": list(item.scoped_arguments),
            }
            for item in sorted(binders.values(), key=lambda item: item.constructor)
        ],
        "version": "skfd.language.semantic.v2",
    }
    return canonical_digest(document)


def is_semantic_subset(candidate: LanguageInterface, target: LanguageInterface) -> bool:
    """Return whether every semantic declaration in candidate exists identically in target."""
    return (
        all(target.sorts.get(key) == value for key, value in candidate.sorts.items())
        and all(target.variable_kinds.get(key) == value for key, value in candidate.variable_kinds.items())
        and all(target.constructors.get(key) == value for key, value in candidate.constructors.items())
        and all(
            target.binders.get(key) == candidate.binders.get(key)
            for key in candidate.constructors
        )
    )


def resolve_language(spec: LanguageSpec, dependencies: Mapping[LanguageId, LanguageInterface]) -> LanguageInterface:
    sorts: dict[SortId, SortDecl] = {}
    kinds: dict[VariableKindId, VariableKindDecl] = {}
    constructors: dict[ConstructorId, ConstructorDecl] = {}
    binders: dict[ConstructorId, BinderDecl] = {}
    resolved_dependencies: list[LanguageInterface] = []
    for requirement in sorted(spec.extends, key=lambda item: item.id):
        dependency = dependencies.get(requirement.id)
        if dependency is None:
            raise AuthoringSemanticError(f"missing language dependency: {requirement.id}")
        if requirement.semantic_digest is not None and requirement.semantic_digest != dependency.semantic_digest:
            raise AuthoringSemanticError(f"language digest mismatch: {requirement.id}")
        resolved_dependencies.append(dependency)
        _merge(sorts, dependency.sorts.values(), lambda item: item.id)
        _merge(kinds, dependency.variable_kinds.values(), lambda item: item.id)
        _merge(constructors, dependency.constructors.values(), lambda item: item.id)
        _merge(binders, dependency.binders.values(), lambda item: item.constructor)
    _merge(sorts, spec.sorts, lambda item: item.id)
    _merge(kinds, spec.variable_kinds, lambda item: item.id)
    _merge(constructors, spec.constructors, lambda item: item.id)
    _merge(binders, spec.binders, lambda item: item.constructor)
    for dependency in resolved_dependencies:
        for constructor_id in dependency.constructors:
            if dependency.binders.get(constructor_id) != binders.get(constructor_id):
                raise AuthoringSemanticError(
                    f"inherited binder semantics changed: {constructor_id}"
                )
    for kind in kinds.values():
        if kind.sort not in sorts:
            raise AuthoringSemanticError(f"variable kind {kind.id} has unknown sort: {kind.sort}")
    for constructor in constructors.values():
        for sort in (*constructor.inputs, constructor.output):
            if sort not in sorts:
                raise AuthoringSemanticError(f"constructor {constructor.id} has unknown sort: {sort}")
    for binder in binders.values():
        binder_constructor = constructors.get(binder.constructor)
        indexes = (binder.variable_argument, *binder.scoped_arguments)
        if binder_constructor is None:
            raise AuthoringSemanticError(f"binder has unknown constructor: {binder.constructor}")
        if (
            binder.variable_argument < 0
            or not binder.scoped_arguments
            or len(set(indexes)) != len(indexes)
            or any(index < 0 or index >= len(binder_constructor.inputs) for index in indexes)
        ):
            raise AuthoringSemanticError(f"invalid binder arguments: {binder.constructor}")
        bound_sort = binder_constructor.inputs[binder.variable_argument]
        if not any(kind.sort == bound_sort for kind in kinds.values()):
            raise AuthoringSemanticError(f"binder variable has no variable kind: {binder.constructor}")
    return LanguageInterface(
        spec.id,
        _digest(sorts, kinds, constructors, binders),
        sorts,
        kinds,
        constructors,
        binders,
    )
