from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TypeAlias

from ._canonical import JsonValue, canonical_digest
from .errors import AuthoringSemanticError
from .ids import (
    AssertionSemanticId,
    BackendBindingId,
    BackendVocabularyId,
    ConstructorId,
    Digest,
    FoundationId,
    SortId,
)
from .language import LanguageInterface, LanguageRequirement, is_semantic_subset
from .term import App, Term, VariableRef


@dataclass(frozen=True, slots=True)
class TokenRef:
    owner: BackendVocabularyId
    local_name: str

    def __post_init__(self) -> None:
        if not self.local_name:
            raise ValueError("token local_name must be non-empty")


@dataclass(frozen=True, slots=True)
class LiteralPart:
    token: TokenRef


@dataclass(frozen=True, slots=True)
class ArgumentPart:
    index: int


TemplatePart: TypeAlias = LiteralPart | ArgumentPart


@dataclass(frozen=True, slots=True, kw_only=True)
class FormationBinding:
    constructor: ConstructorId
    syntax_assertion: AssertionSemanticId
    syntax_assertion_label: str
    template: tuple[TemplatePart, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SortTypecodeBinding:
    sort: SortId
    typecode: TokenRef


@dataclass(frozen=True, slots=True, kw_only=True)
class FoundationRequirement:
    id: FoundationId
    interface_digest: Digest | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class MetamathLanguageRequirement:
    id: BackendBindingId
    digest: Digest | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class MetamathLanguageBinding:
    id: BackendBindingId
    language: LanguageRequirement
    foundation: FoundationRequirement
    extends: tuple[MetamathLanguageRequirement, ...] = ()
    formations: tuple[FormationBinding, ...] = ()
    sort_typecodes: tuple[SortTypecodeBinding, ...] = ()


@dataclass(frozen=True, slots=True)
class LiteralAtom:
    token: TokenRef


@dataclass(frozen=True, slots=True)
class VariableAtom:
    variable: VariableRef


MetamathAtom: TypeAlias = LiteralAtom | VariableAtom


@dataclass(frozen=True, slots=True)
class ResolvedMetamathLanguageBinding:
    id: BackendBindingId
    language: LanguageInterface = field(compare=False, hash=False, repr=False)
    foundation: FoundationRequirement = field(compare=False, hash=False)
    formations: Mapping[ConstructorId, FormationBinding] = field(compare=False, hash=False, repr=False)
    sort_typecodes: tuple[SortTypecodeBinding, ...] = field(compare=False, hash=False)
    digest: Digest

    def __post_init__(self) -> None:
        object.__setattr__(self, "formations", MappingProxyType(dict(self.formations)))

    def lower(self, term: Term) -> tuple[MetamathAtom, ...]:
        if not isinstance(term, App):
            return (VariableAtom(term.variable),)
        formation = self.formations.get(term.constructor)
        if formation is None:
            raise AuthoringSemanticError(f"no Metamath formation for: {term.constructor}")
        atoms: list[MetamathAtom] = []
        for part in formation.template:
            if isinstance(part, LiteralPart):
                atoms.append(LiteralAtom(part.token))
            else:
                atoms.extend(self.lower(term.arguments[part.index]))
        return tuple(atoms)

    def parse(
        self,
        atoms: Sequence[MetamathAtom],
        *,
        expected_sort: SortId,
    ) -> Term:
        """Invert formation templates into one uniquely typed semantic term."""
        source = tuple(atoms)
        memo: dict[tuple[SortId, int, int], frozenset[Term]] = {}
        formations_by_sort: dict[
            SortId, list[tuple[FormationBinding, tuple[SortId, ...]]]
        ] = {}
        for formation in self.formations.values():
            constructor = self.language.constructors[formation.constructor]
            formations_by_sort.setdefault(constructor.output, []).append(
                (formation, constructor.inputs)
            )

        def terms(sort: SortId, start: int, end: int) -> frozenset[Term]:
            key = (sort, start, end)
            cached = memo.get(key)
            if cached is not None:
                return cached
            found: set[Term] = set()
            atom = source[start] if end == start + 1 else None
            if isinstance(atom, VariableAtom):
                variable = atom.variable
                declaration = self.language.variable_kinds.get(variable.kind)
                if declaration is not None and declaration.sort == sort:
                    found.add(self.language.variable(variable))
            memo[key] = frozenset()
            for formation, input_sorts in formations_by_sort.get(sort, ()):
                template = formation.template
                if len(template) > end - start:
                    continue
                first = template[0]
                if isinstance(first, LiteralPart) and source[start] != LiteralAtom(
                    first.token
                ):
                    continue
                last = template[-1]
                if isinstance(last, LiteralPart) and source[end - 1] != LiteralAtom(
                    last.token
                ):
                    continue
                for arguments in match_template(
                    template,
                    input_sorts,
                    start,
                    end,
                ):
                    found.add(self.language.apply(formation.constructor, arguments))
            result = frozenset(found)
            memo[key] = result
            return result

        def match_template(
            template: tuple[TemplatePart, ...],
            input_sorts: tuple[SortId, ...],
            start: int,
            end: int,
        ) -> tuple[tuple[Term, ...], ...]:
            matches: list[tuple[Term, ...]] = []

            def visit(
                part_index: int,
                position: int,
                arguments: dict[int, Term],
            ) -> None:
                if part_index == len(template):
                    if position == end and len(arguments) == len(input_sorts):
                        matches.append(
                            tuple(arguments[index] for index in range(len(input_sorts)))
                        )
                    return
                part = template[part_index]
                if isinstance(part, LiteralPart):
                    if position < end and source[position] == LiteralAtom(part.token):
                        visit(part_index + 1, position + 1, arguments)
                    return
                remaining_parts = len(template) - part_index - 1
                maximum = end - remaining_parts
                next_part = (
                    template[part_index + 1]
                    if part_index + 1 < len(template)
                    else None
                )
                argument_ends: Iterator[int]
                if isinstance(next_part, LiteralPart):
                    separator = LiteralAtom(next_part.token)
                    argument_ends = (
                        index
                        for index in range(position + 1, maximum + 1)
                        if source[index] == separator
                    )
                elif next_part is None:
                    argument_ends = iter((end,))
                else:
                    argument_ends = iter(range(position + 1, maximum + 1))
                for argument_end in argument_ends:
                    for argument in terms(
                        input_sorts[part.index], position, argument_end
                    ):
                        visit(
                            part_index + 1,
                            argument_end,
                            {**arguments, part.index: argument},
                        )

            visit(0, start, {})
            return tuple(matches)

        parsed = terms(expected_sort, 0, len(source))
        if not parsed:
            raise AuthoringSemanticError(
                f"Metamath atoms do not parse as sort {expected_sort}"
            )
        if len(parsed) != 1:
            raise AuthoringSemanticError(
                f"ambiguous Metamath term for sort {expected_sort}: {len(parsed)} parses"
            )
        term = next(iter(parsed))
        if self.lower(term) != source:
            raise AuthoringSemanticError("Metamath term parse/lower round-trip mismatch")
        return term


def resolve_metamath_language(binding: MetamathLanguageBinding, language: LanguageInterface, dependencies: Mapping[BackendBindingId, ResolvedMetamathLanguageBinding]) -> ResolvedMetamathLanguageBinding:
    if binding.language.id != language.id or (binding.language.semantic_digest is not None and binding.language.semantic_digest != language.semantic_digest):
        raise AuthoringSemanticError("Metamath binding language requirement mismatch")
    formations: dict[ConstructorId, FormationBinding] = {}
    typecodes: dict[SortId, SortTypecodeBinding] = {}
    for requirement in sorted(binding.extends, key=lambda item: item.id):
        dependency = dependencies.get(requirement.id)
        if dependency is None:
            raise AuthoringSemanticError(f"missing Metamath binding dependency: {requirement.id}")
        if requirement.digest is not None and requirement.digest != dependency.digest:
            raise AuthoringSemanticError(f"Metamath binding digest mismatch: {requirement.id}")
        if not is_semantic_subset(dependency.language, language):
            raise AuthoringSemanticError(f"Metamath binding dependency language mismatch: {requirement.id}")
        if dependency.foundation != binding.foundation:
            raise AuthoringSemanticError(f"Metamath binding foundation mismatch: {requirement.id}")
        for formation in dependency.formations.values():
            old = formations.get(formation.constructor)
            if old is not None and old != formation:
                raise AuthoringSemanticError(f"conflicting Metamath formation: {formation.constructor}")
            formations[formation.constructor] = formation
        for typecode in dependency.sort_typecodes:
            old_typecode = typecodes.get(typecode.sort)
            if old_typecode is not None and old_typecode != typecode:
                raise AuthoringSemanticError(f"conflicting sort typecode: {typecode.sort}")
            typecodes[typecode.sort] = typecode
    for formation in binding.formations:
        old = formations.get(formation.constructor)
        if old is not None and old != formation:
            raise AuthoringSemanticError(f"conflicting Metamath formation: {formation.constructor}")
        formations[formation.constructor] = formation
    for typecode in binding.sort_typecodes:
        old_typecode = typecodes.get(typecode.sort)
        if old_typecode is not None and old_typecode != typecode:
            raise AuthoringSemanticError(f"conflicting sort typecode: {typecode.sort}")
        typecodes[typecode.sort] = typecode
    for sort in typecodes:
        if sort not in language.sorts:
            raise AuthoringSemanticError(f"unknown sort typecode: {sort}")
    for constructor_id, formation in formations.items():
        constructor = language.constructors.get(constructor_id)
        if constructor is None:
            raise AuthoringSemanticError(f"unknown formation constructor: {constructor_id}")
        if not formation.syntax_assertion_label:
            raise AuthoringSemanticError(f"empty syntax assertion label: {constructor_id}")
        indexes = [part.index for part in formation.template if isinstance(part, ArgumentPart)]
        if sorted(indexes) != list(range(len(constructor.inputs))):
            raise AuthoringSemanticError(f"formation argument coverage mismatch: {constructor_id}")
    ordered = tuple(sorted(formations.values(), key=lambda item: item.constructor))
    ordered_typecodes = tuple(sorted(typecodes.values(), key=lambda item: item.sort))
    formation_json: list[JsonValue] = []
    for formation in ordered:
        parts: list[JsonValue] = []
        for part in formation.template:
            if isinstance(part, ArgumentPart):
                parts.append({"argument": part.index})
            else:
                parts.append({"token_owner": str(part.token.owner), "token_name": part.token.local_name})
        formation_json.append(
            {
                "constructor": str(formation.constructor),
                "syntax_assertion": str(formation.syntax_assertion),
                "syntax_assertion_label": formation.syntax_assertion_label,
                "template": parts,
            }
        )
    digest = canonical_digest(
        {
            "version": "skfd.metamath-language.v1",
            "language_semantic_digest": str(language.semantic_digest),
            "foundation": {
                "id": str(binding.foundation.id),
                "interface_digest": (
                    str(binding.foundation.interface_digest)
                    if binding.foundation.interface_digest is not None
                    else None
                ),
            },
            "formations": formation_json,
            "sort_typecodes": [
                {"sort": str(item.sort), "token_owner": str(item.typecode.owner), "token_name": item.typecode.local_name}
                for item in ordered_typecodes
            ],
        }
    )
    return ResolvedMetamathLanguageBinding(
        binding.id,
        language,
        binding.foundation,
        formations,
        ordered_typecodes,
        digest,
    )
