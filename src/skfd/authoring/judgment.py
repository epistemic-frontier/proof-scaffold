from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from ._canonical import JsonValue, canonical_digest
from .errors import AuthoringSemanticError
from .ids import AssertionSemanticId, CalculusId, Digest, JudgmentKindId, RuleId, SortId
from .language import (
    LanguageInterface,
    LanguageRequirement,
    is_semantic_subset,
)
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
    mandatory_distinct: tuple[DistinctPair, ...] = ()


@dataclass(frozen=True, slots=True)
class DistinctPair:
    left: VariableRef
    right: VariableRef

    def __post_init__(self) -> None:
        if self.left == self.right:
            raise AuthoringSemanticError("distinct-variable pair must have different endpoints")


@dataclass(frozen=True, slots=True, kw_only=True)
class AxiomDecl:
    id: AssertionSemanticId
    schema_variables: tuple[VariableRef, ...]
    conclusion: Judgment
    mandatory_distinct: tuple[DistinctPair, ...] = ()


@dataclass(frozen=True, slots=True)
class AxiomInterface:
    declaration: AxiomDecl
    digest: Digest


@dataclass(frozen=True, slots=True, kw_only=True)
class DefinitionDecl:
    id: AssertionSemanticId
    schema_variables: tuple[VariableRef, ...]
    conclusion: Judgment
    mandatory_distinct: tuple[DistinctPair, ...] = ()


@dataclass(frozen=True, slots=True)
class DefinitionInterface:
    declaration: DefinitionDecl
    digest: Digest


@dataclass(frozen=True, slots=True, kw_only=True)
class CalculusRequirement:
    id: CalculusId
    digest: Digest | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class CalculusSpec:
    id: CalculusId
    language: LanguageRequirement
    extends: tuple[CalculusRequirement, ...] = ()
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


def _variable_key(variable: VariableRef) -> tuple[str, str, str, str]:
    return (
        variable.scope,
        str(variable.owner),
        variable.local_key,
        str(variable.kind),
    )


def _variable_document(variable: VariableRef) -> JsonValue:
    return {
        "scope": variable.scope,
        "owner": str(variable.owner),
        "local_key": variable.local_key,
        "kind": str(variable.kind),
    }


def _canonical_variables(variables: tuple[VariableRef, ...]) -> tuple[VariableRef, ...]:
    return tuple(sorted(variables, key=_variable_key))


def _canonical_distinct_pair(pair: DistinctPair) -> DistinctPair:
    if _variable_key(pair.left) <= _variable_key(pair.right):
        return pair
    return DistinctPair(pair.right, pair.left)


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
    binder = language.binders.get(term.constructor)
    if binder is not None:
        for binding in binder.bindings:
            if not isinstance(term.arguments[binding.variable_argument], Var):
                raise AuthoringSemanticError(
                    f"binder {term.constructor} argument {binding.variable_argument} must be a variable"
                )
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


def resolve_calculus(
    spec: CalculusSpec,
    language: LanguageInterface,
    dependencies: Mapping[CalculusId, CalculusInterface] | None = None,
) -> CalculusInterface:
    if spec.language.id != language.id or (spec.language.semantic_digest is not None and spec.language.semantic_digest != language.semantic_digest):
        raise AuthoringSemanticError("calculus language requirement mismatch")
    judgments: dict[JudgmentKindId, JudgmentKindDecl] = {}
    rules: dict[RuleId, PrimitiveRuleDecl] = {}
    dependency_map = dependencies or {}
    for requirement in sorted(spec.extends, key=lambda item: item.id):
        dependency = dependency_map.get(requirement.id)
        if dependency is None:
            raise AuthoringSemanticError(f"missing calculus dependency: {requirement.id}")
        if requirement.digest is not None and requirement.digest != dependency.digest:
            raise AuthoringSemanticError(f"calculus digest mismatch: {requirement.id}")
        if not is_semantic_subset(dependency.language, language):
            raise AuthoringSemanticError(f"calculus dependency language mismatch: {requirement.id}")
        for judgment_declaration in dependency.judgments.values():
            old = judgments.get(judgment_declaration.id)
            if old is not None and old != judgment_declaration:
                raise AuthoringSemanticError(
                    f"conflicting inherited judgment kind: {judgment_declaration.id}"
                )
            judgments[judgment_declaration.id] = judgment_declaration
        for rule_declaration in dependency.rules.values():
            old_rule = rules.get(rule_declaration.id)
            if old_rule is not None and old_rule != rule_declaration:
                raise AuthoringSemanticError(
                    f"conflicting inherited primitive rule: {rule_declaration.id}"
                )
            rules[rule_declaration.id] = rule_declaration
    for judgment_declaration in spec.judgments:
        old = judgments.get(judgment_declaration.id)
        if old is not None and old != judgment_declaration:
            raise AuthoringSemanticError(f"conflicting judgment kind: {judgment_declaration.id}")
        if any(sort not in language.sorts for sort in judgment_declaration.arguments):
            raise AuthoringSemanticError(f"judgment {judgment_declaration.id} has unknown sort")
        judgments[judgment_declaration.id] = judgment_declaration
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
        canonical_variables = _canonical_variables(rule_declaration.schema_variables)
        if canonical_variables != rule_declaration.schema_variables:
            rule_declaration = replace(
                rule_declaration,
                schema_variables=canonical_variables,
            )
        for premise in rule_declaration.premises:
            _validate_judgment(premise, judgments, language, schema_variables)
        _validate_judgment(rule_declaration.conclusion, judgments, language, schema_variables)
        pairs: set[DistinctPair] = set()
        for pair in rule_declaration.mandatory_distinct:
            if pair.left not in schema_variables or pair.right not in schema_variables:
                raise AuthoringSemanticError(
                    f"undeclared distinct-variable endpoint in rule: {rule_declaration.id}"
                )
            pairs.add(_canonical_distinct_pair(pair))
        canonical_pairs = tuple(
            sorted(
                pairs,
                key=lambda pair: (_variable_key(pair.left), _variable_key(pair.right)),
            )
        )
        if canonical_pairs != rule_declaration.mandatory_distinct:
            rule_declaration = replace(
                rule_declaration,
                mandatory_distinct=canonical_pairs,
            )
        rules[rule_declaration.id] = rule_declaration
    digest = canonical_digest(
        {
            "version": "skfd.calculus.v3",
            "language_semantic_digest": str(language.semantic_digest),
            "judgments": [
                {"id": str(item.id), "arguments": [str(sort) for sort in item.arguments]}
                for item in sorted(judgments.values(), key=lambda item: item.id)
            ],
            "rules": [
                {
                    "id": str(item.id),
                    "schema_variables": [
                        _variable_document(variable)
                        for variable in item.schema_variables
                    ],
                    "premises": [_judgment_document(premise) for premise in item.premises],
                    "conclusion": _judgment_document(item.conclusion),
                    "mandatory_distinct": [
                        [
                            _variable_document(pair.left),
                            _variable_document(pair.right),
                        ]
                        for pair in item.mandatory_distinct
                    ],
                }
                for item in sorted(rules.values(), key=lambda item: item.id)
            ],
        }
    )
    return CalculusInterface(spec.id, language, judgments, rules, digest)


def resolve_axiom(declaration: AxiomDecl, calculus: CalculusInterface) -> AxiomInterface:
    schema_variables = frozenset(declaration.schema_variables)
    if len(schema_variables) != len(declaration.schema_variables):
        raise AuthoringSemanticError(f"duplicate schema variable in axiom: {declaration.id}")
    if any(variable.scope != "schema" for variable in schema_variables):
        raise AuthoringSemanticError(f"non-schema variable in axiom: {declaration.id}")
    for variable in schema_variables:
        if variable.kind not in calculus.language.variable_kinds:
            raise AuthoringSemanticError(
                f"unknown schema variable kind in axiom {declaration.id}: {variable.kind}"
            )
    _validate_judgment(
        declaration.conclusion,
        calculus.judgments,
        calculus.language,
        schema_variables,
    )

    pairs: set[DistinctPair] = set()
    for pair in declaration.mandatory_distinct:
        if pair.left not in schema_variables or pair.right not in schema_variables:
            raise AuthoringSemanticError(
                f"undeclared distinct-variable endpoint in axiom: {declaration.id}"
            )
        pairs.add(_canonical_distinct_pair(pair))
    canonical_pairs = tuple(
        sorted(pairs, key=lambda pair: (_variable_key(pair.left), _variable_key(pair.right)))
    )
    declaration = replace(
        declaration,
        schema_variables=_canonical_variables(declaration.schema_variables),
        mandatory_distinct=canonical_pairs,
    )
    digest = canonical_digest(
        {
            "version": "skfd.axiom.v1",
            "calculus_digest": str(calculus.digest),
            "id": str(declaration.id),
            "schema_variables": [
                _variable_document(variable) for variable in declaration.schema_variables
            ],
            "conclusion": _judgment_document(declaration.conclusion),
            "mandatory_distinct": [
                [_variable_document(pair.left), _variable_document(pair.right)]
                for pair in declaration.mandatory_distinct
            ],
        }
    )
    return AxiomInterface(declaration, digest)


def resolve_definition(
    declaration: DefinitionDecl,
    calculus: CalculusInterface,
) -> DefinitionInterface:
    """Resolve a conservative definition through the assertion validation core."""
    resolved = resolve_axiom(
        AxiomDecl(
            id=declaration.id,
            schema_variables=declaration.schema_variables,
            conclusion=declaration.conclusion,
            mandatory_distinct=declaration.mandatory_distinct,
        ),
        calculus,
    )
    canonical = DefinitionDecl(
        id=resolved.declaration.id,
        schema_variables=resolved.declaration.schema_variables,
        conclusion=resolved.declaration.conclusion,
        mandatory_distinct=resolved.declaration.mandatory_distinct,
    )
    digest = canonical_digest(
        {
            "version": "skfd.definition.v1",
            "calculus_digest": str(calculus.digest),
            "id": str(canonical.id),
            "schema_variables": [
                _variable_document(variable) for variable in canonical.schema_variables
            ],
            "conclusion": _judgment_document(canonical.conclusion),
            "mandatory_distinct": [
                [_variable_document(pair.left), _variable_document(pair.right)]
                for pair in canonical.mandatory_distinct
            ],
        }
    )
    return DefinitionInterface(canonical, digest)
