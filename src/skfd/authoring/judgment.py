from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from ._canonical import JsonValue, canonical_digest
from .errors import AuthoringSemanticError
from .ids import CalculusId, Digest, JudgmentKindId, RuleId, SortId
from .language import LanguageInterface, LanguageRequirement
from .term import App, Term, Var, VariableRef


@dataclass(frozen=True, slots=True, kw_only=True)
class JudgmentKindDecl:
    id: JudgmentKindId
    arguments: tuple[SortId, ...]


@dataclass(frozen=True, slots=True)
class Judgment:
    kind: JudgmentKindId
    arguments: tuple[Term, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class PrimitiveRuleDecl:
    id: RuleId
    schema_variables: tuple[VariableRef, ...]
    premises: tuple[Judgment, ...]
    conclusion: Judgment


@dataclass(frozen=True, slots=True, kw_only=True)
class CalculusSpec:
    id: CalculusId
    language: LanguageRequirement
    judgments: tuple[JudgmentKindDecl, ...] = ()
    rules: tuple[PrimitiveRuleDecl, ...] = ()


@dataclass(frozen=True, slots=True)
class CalculusInterface:
    id: CalculusId
    language: LanguageInterface = field(compare=False, hash=False, repr=False)
    judgments: Mapping[JudgmentKindId, JudgmentKindDecl] = field(compare=False, hash=False, repr=False)
    rules: Mapping[RuleId, PrimitiveRuleDecl] = field(compare=False, hash=False, repr=False)
    digest: Digest

    def __post_init__(self) -> None:
        object.__setattr__(self, "judgments", MappingProxyType(dict(self.judgments)))
        object.__setattr__(self, "rules", MappingProxyType(dict(self.rules)))

    def judgment(self, kind: JudgmentKindId, arguments: Iterable[Term]) -> Judgment:
        declaration = self.judgments.get(kind)
        if declaration is None:
            raise AuthoringSemanticError(f"unknown judgment kind: {kind}")
        args = tuple(arguments)
        if tuple(item.sort for item in args) != declaration.arguments:
            raise AuthoringSemanticError(f"judgment argument mismatch: {kind}")
        for argument in args:
            _validate_term(argument, self.language)
        return Judgment(kind, args)

    def rule(self, rule: RuleId) -> PrimitiveRuleDecl:
        declaration = self.rules.get(rule)
        if declaration is None:
            raise AuthoringSemanticError(f"unknown primitive rule: {rule}")
        return declaration


def _term_document(term: Term) -> JsonValue:
    if isinstance(term, Var):
        return {
            "variable": {
                "scope": term.variable.scope,
                "owner": str(term.variable.owner),
                "local_key": term.variable.local_key,
                "kind": str(term.variable.kind),
            },
            "sort": str(term.sort),
        }
    return {
        "constructor": str(term.constructor),
        "arguments": [_term_document(argument) for argument in term.arguments],
        "sort": str(term.sort),
    }


def _judgment_document(judgment: Judgment) -> JsonValue:
    return {
        "kind": str(judgment.kind),
        "arguments": [_term_document(argument) for argument in judgment.arguments],
    }


def _validate_term(
    term: Term,
    language: LanguageInterface,
    schema_variables: frozenset[VariableRef] | None = None,
) -> None:
    if isinstance(term, Var):
        if schema_variables is not None and term.variable not in schema_variables:
            raise AuthoringSemanticError(f"undeclared rule schema variable: {term.variable.local_key}")
        variable_declaration = language.variable_kinds.get(term.variable.kind)
        if variable_declaration is None or variable_declaration.sort != term.sort:
            raise AuthoringSemanticError(f"invalid rule schema variable: {term.variable.local_key}")
        return
    if not isinstance(term, App):
        raise AuthoringSemanticError(f"invalid term object: {type(term).__name__}")
    constructor_declaration = language.constructors.get(term.constructor)
    if constructor_declaration is None:
        raise AuthoringSemanticError(f"unknown term constructor: {term.constructor}")
    if (
        constructor_declaration.inputs != tuple(argument.sort for argument in term.arguments)
        or constructor_declaration.output != term.sort
    ):
        raise AuthoringSemanticError(f"invalid term: {term.constructor}")
    for argument in term.arguments:
        _validate_term(argument, language, schema_variables)


def _validate_judgment(
    judgment: Judgment,
    judgments: Mapping[JudgmentKindId, JudgmentKindDecl],
    language: LanguageInterface,
    schema_variables: frozenset[VariableRef],
) -> None:
    declaration = judgments.get(judgment.kind)
    if declaration is None:
        raise AuthoringSemanticError(f"unknown rule judgment kind: {judgment.kind}")
    if declaration.arguments != tuple(argument.sort for argument in judgment.arguments):
        raise AuthoringSemanticError(f"rule judgment argument mismatch: {judgment.kind}")
    for argument in judgment.arguments:
        _validate_term(argument, language, schema_variables)


def resolve_calculus(spec: CalculusSpec, language: LanguageInterface) -> CalculusInterface:
    if spec.language.id != language.id or (spec.language.semantic_digest is not None and spec.language.semantic_digest != language.semantic_digest):
        raise AuthoringSemanticError("calculus language requirement mismatch")
    judgments: dict[JudgmentKindId, JudgmentKindDecl] = {}
    for judgment_declaration in spec.judgments:
        old = judgments.get(judgment_declaration.id)
        if old is not None and old != judgment_declaration:
            raise AuthoringSemanticError(f"conflicting judgment kind: {judgment_declaration.id}")
        if any(sort not in language.sorts for sort in judgment_declaration.arguments):
            raise AuthoringSemanticError(f"judgment {judgment_declaration.id} has unknown sort")
        judgments[judgment_declaration.id] = judgment_declaration
    rules: dict[RuleId, PrimitiveRuleDecl] = {}
    for rule_declaration in spec.rules:
        if rule_declaration.id in rules:
            raise AuthoringSemanticError(f"duplicate primitive rule: {rule_declaration.id}")
        schema_variables = frozenset(rule_declaration.schema_variables)
        if len(schema_variables) != len(rule_declaration.schema_variables):
            raise AuthoringSemanticError(f"duplicate schema variable in rule: {rule_declaration.id}")
        if any(variable.scope != "schema" for variable in schema_variables):
            raise AuthoringSemanticError(f"non-schema variable in rule: {rule_declaration.id}")
        for variable in schema_variables:
            if variable.kind not in language.variable_kinds:
                raise AuthoringSemanticError(
                    f"unknown schema variable kind in rule {rule_declaration.id}: {variable.kind}"
                )
        canonical_variables = tuple(
            sorted(
                rule_declaration.schema_variables,
                key=lambda variable: (
                    variable.scope,
                    str(variable.owner),
                    variable.local_key,
                    str(variable.kind),
                ),
            )
        )
        if canonical_variables != rule_declaration.schema_variables:
            rule_declaration = replace(
                rule_declaration,
                schema_variables=canonical_variables,
            )
        for premise in rule_declaration.premises:
            _validate_judgment(premise, judgments, language, schema_variables)
        _validate_judgment(rule_declaration.conclusion, judgments, language, schema_variables)
        rules[rule_declaration.id] = rule_declaration
    digest = canonical_digest(
        {
            "version": "skfd.calculus.v2",
            "language_semantic_digest": str(language.semantic_digest),
            "judgments": [
                {"id": str(item.id), "arguments": [str(sort) for sort in item.arguments]}
                for item in sorted(judgments.values(), key=lambda item: item.id)
            ],
            "rules": [
                {
                    "id": str(item.id),
                    "schema_variables": [
                        {
                            "scope": variable.scope,
                            "owner": str(variable.owner),
                            "local_key": variable.local_key,
                            "kind": str(variable.kind),
                        }
                        for variable in item.schema_variables
                    ],
                    "premises": [_judgment_document(premise) for premise in item.premises],
                    "conclusion": _judgment_document(item.conclusion),
                }
                for item in sorted(rules.values(), key=lambda item: item.id)
            ],
        }
    )
    return CalculusInterface(spec.id, language, judgments, rules, digest)
