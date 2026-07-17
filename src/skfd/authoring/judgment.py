from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from ._canonical import canonical_digest
from .errors import AuthoringSemanticError
from .ids import CalculusId, Digest, JudgmentKindId, SortId
from .language import LanguageInterface, LanguageRequirement
from .term import Term


@dataclass(frozen=True, slots=True, kw_only=True)
class JudgmentKindDecl:
    id: JudgmentKindId
    arguments: tuple[SortId, ...]


@dataclass(frozen=True, slots=True)
class Judgment:
    kind: JudgmentKindId
    arguments: tuple[Term, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CalculusSpec:
    id: CalculusId
    language: LanguageRequirement
    judgments: tuple[JudgmentKindDecl, ...] = ()


@dataclass(frozen=True, slots=True)
class CalculusInterface:
    id: CalculusId
    language: LanguageInterface = field(compare=False, hash=False, repr=False)
    judgments: Mapping[JudgmentKindId, JudgmentKindDecl] = field(compare=False, hash=False, repr=False)
    digest: Digest

    def __post_init__(self) -> None:
        object.__setattr__(self, "judgments", MappingProxyType(dict(self.judgments)))

    def judgment(self, kind: JudgmentKindId, arguments: Iterable[Term]) -> Judgment:
        declaration = self.judgments.get(kind)
        if declaration is None:
            raise AuthoringSemanticError(f"unknown judgment kind: {kind}")
        args = tuple(arguments)
        if tuple(item.sort for item in args) != declaration.arguments:
            raise AuthoringSemanticError(f"judgment argument mismatch: {kind}")
        return Judgment(kind, args)


def resolve_calculus(spec: CalculusSpec, language: LanguageInterface) -> CalculusInterface:
    if spec.language.id != language.id or (spec.language.semantic_digest is not None and spec.language.semantic_digest != language.semantic_digest):
        raise AuthoringSemanticError("calculus language requirement mismatch")
    judgments: dict[JudgmentKindId, JudgmentKindDecl] = {}
    for declaration in spec.judgments:
        old = judgments.get(declaration.id)
        if old is not None and old != declaration:
            raise AuthoringSemanticError(f"conflicting judgment kind: {declaration.id}")
        if any(sort not in language.sorts for sort in declaration.arguments):
            raise AuthoringSemanticError(f"judgment {declaration.id} has unknown sort")
        judgments[declaration.id] = declaration
    digest = canonical_digest(
        {
            "version": "skfd.calculus.v1",
            "language_semantic_digest": str(language.semantic_digest),
            "judgments": [
                {"id": str(item.id), "arguments": [str(sort) for sort in item.arguments]}
                for item in sorted(judgments.values(), key=lambda item: item.id)
            ],
        }
    )
    return CalculusInterface(spec.id, language, judgments, digest)
