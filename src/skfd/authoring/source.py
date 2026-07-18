from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from types import TracebackType
from typing import TypeAlias

from ._canonical import JsonValue, canonical_digest
from .assertion import (
    AssertionSignature,
    ProofDraft,
    normalize_distinct_pairs,
    start_draft,
)
from .errors import AuthoringSemanticError
from .ids import Digest, ProofId
from .judgment import CalculusInterface, DistinctPair, Judgment
from .term import Term, Var, VariableRef


@dataclass(frozen=True, slots=True)
class DistinctStatement:
    variables: tuple[VariableRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.variables, tuple) or any(
            not isinstance(variable, VariableRef) for variable in self.variables
        ):
            raise AuthoringSemanticError("distinct statement requires a tuple of variables")
        if len(self.variables) < 2:
            raise AuthoringSemanticError("distinct statement requires at least two variables")
        if len(frozenset(self.variables)) != len(self.variables):
            raise AuthoringSemanticError("distinct statement variables must be unique")


@dataclass(frozen=True, slots=True)
class AssertionSource:
    declaration: AssertionSignature

    def __post_init__(self) -> None:
        if not isinstance(self.declaration, AssertionSignature):
            raise AuthoringSemanticError("assertion source requires an assertion signature")


@dataclass(frozen=True, slots=True)
class SourceBlock:
    statements: tuple[DistinctStatement | AssertionSource | SourceBlock, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.statements, tuple) or any(
            not isinstance(statement, (DistinctStatement, AssertionSource, SourceBlock))
            for statement in self.statements
        ):
            raise AuthoringSemanticError("source block contains an invalid statement")


SourceStatement: TypeAlias = DistinctStatement | AssertionSource | SourceBlock


@dataclass(frozen=True, slots=True)
class AssertionSourceSnapshot:
    declaration: AssertionSignature
    active_distinct: tuple[DistinctPair, ...]

    def __post_init__(self) -> None:
        normalized = normalize_distinct_pairs(self.active_distinct)
        object.__setattr__(self, "active_distinct", normalized)
        mandatory_variables = frozenset(self.declaration.schema_variables)
        expected_mandatory = tuple(
            pair
            for pair in normalized
            if pair.left in mandatory_variables and pair.right in mandatory_variables
        )
        if self.declaration.mandatory_distinct != expected_mandatory:
            raise AuthoringSemanticError(
                "source snapshot mandatory distinct relation does not match its active scope"
            )


@dataclass(frozen=True, slots=True)
class ElaboratedSourceBlock:
    source: SourceBlock
    assertions: tuple[AssertionSourceSnapshot, ...]
    source_digest: Digest
    semantic_digest: Digest


def _variable_document(variable: VariableRef) -> JsonValue:
    return {
        "scope": variable.scope,
        "owner": str(variable.owner),
        "local_key": variable.local_key,
        "kind": str(variable.kind),
    }


def _pair_document(pair: DistinctPair) -> JsonValue:
    return [_variable_document(pair.left), _variable_document(pair.right)]


def _term_document(term: Term) -> JsonValue:
    if isinstance(term, Var):
        return {
            "variable": _variable_document(term.variable),
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


def _assertion_document(
    assertion: AssertionSignature,
    *,
    include_label: bool,
) -> JsonValue:
    document: dict[str, JsonValue] = {
        "id": str(assertion.id),
        "kind": assertion.kind,
        "schema_variables": [
            _variable_document(variable) for variable in assertion.schema_variables
        ],
        "premises": [_judgment_document(premise) for premise in assertion.premises],
        "conclusion": _judgment_document(assertion.conclusion),
        "mandatory_distinct": [
            _pair_document(pair) for pair in assertion.mandatory_distinct
        ],
    }
    if include_label:
        document["canonical_label"] = assertion.canonical_label
    return document


def _expand_distinct(statement: DistinctStatement) -> tuple[DistinctPair, ...]:
    return tuple(
        DistinctPair(statement.variables[left], statement.variables[right])
        for left in range(len(statement.variables))
        for right in range(left + 1, len(statement.variables))
    )


def _source_document(block: SourceBlock) -> JsonValue:
    statements: list[JsonValue] = []
    for statement in block.statements:
        if isinstance(statement, DistinctStatement):
            statements.append(
                {
                    "distinct": [
                        _variable_document(variable) for variable in statement.variables
                    ]
                }
            )
        elif isinstance(statement, SourceBlock):
            statements.append({"block": _source_document(statement)})
        elif isinstance(statement, AssertionSource):
            statements.append(
                {
                    "assertion": _assertion_document(
                        statement.declaration,
                        include_label=True,
                    )
                }
            )
        else:
            raise AuthoringSemanticError("source block contains an invalid statement")
    return {"statements": statements}


def _elaborate_statements(
    block: SourceBlock,
    inherited_distinct: tuple[DistinctPair, ...],
) -> tuple[AssertionSourceSnapshot, ...]:
    active = inherited_distinct
    snapshots: list[AssertionSourceSnapshot] = []
    for statement in block.statements:
        if isinstance(statement, DistinctStatement):
            active = normalize_distinct_pairs((*active, *_expand_distinct(statement)))
            continue
        if isinstance(statement, SourceBlock):
            snapshots.extend(_elaborate_statements(statement, active))
            continue
        if not isinstance(statement, AssertionSource):
            raise AuthoringSemanticError("source block contains an invalid statement")
        mandatory_variables = frozenset(statement.declaration.schema_variables)
        mandatory = tuple(
            pair
            for pair in active
            if pair.left in mandatory_variables and pair.right in mandatory_variables
        )
        declaration = replace(statement.declaration, mandatory_distinct=mandatory)
        snapshots.append(AssertionSourceSnapshot(declaration, active))
    return tuple(snapshots)


def elaborate_block(
    block: SourceBlock,
    *,
    inherited_distinct: tuple[DistinctPair, ...] = (),
) -> ElaboratedSourceBlock:
    inherited = normalize_distinct_pairs(inherited_distinct)
    assertions = _elaborate_statements(block, inherited)
    source_digest = canonical_digest(
        {
            "version": "skfd.source-block.v1",
            "source": _source_document(block),
        }
    )
    semantic_digest = canonical_digest(
        {
            "version": "skfd.elaborated-source-block.v1",
            "inherited_distinct": [_pair_document(pair) for pair in inherited],
            "assertions": [
                {
                    "assertion": _assertion_document(
                        snapshot.declaration,
                        include_label=False,
                    ),
                    "active_distinct": [
                        _pair_document(pair) for pair in snapshot.active_distinct
                    ],
                    "mandatory_distinct": [
                        _pair_document(pair)
                        for pair in snapshot.declaration.mandatory_distinct
                    ],
                }
                for snapshot in assertions
            ],
        }
    )
    return ElaboratedSourceBlock(block, assertions, source_digest, semantic_digest)


def start_draft_from_snapshot(
    proof_id: ProofId,
    calculus: CalculusInterface,
    snapshot: AssertionSourceSnapshot,
) -> ProofDraft:
    return start_draft(
        proof_id,
        calculus,
        snapshot.declaration.premises,
        active_distinct=snapshot.active_distinct,
        signature=snapshot.declaration,
    )


class _BlockContext(AbstractContextManager["_BlockContext"]):
    def __init__(
        self,
        sink: list[SourceStatement],
        parent: _BlockContext | None = None,
    ) -> None:
        self._sink = sink
        self._parent = parent
        self._statements: list[SourceStatement] = []
        self._state = "new"
        self._active_children = 0

    def __enter__(self) -> _BlockContext:
        if self._state != "new":
            raise AuthoringSemanticError("source block context cannot be reused")
        if self._parent is not None:
            if self._parent._state != "active":
                raise AuthoringSemanticError("nested source block parent is not active")
            self._parent._active_children += 1
        self._state = "active"
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        if self._state != "active":
            raise AuthoringSemanticError("source block context is not active")
        if self._active_children:
            raise AuthoringSemanticError("source block has an active nested block")
        self._state = "closed"
        if self._parent is not None:
            self._parent._active_children -= 1
        if exc_type is None:
            self._sink.append(SourceBlock(tuple(self._statements)))
        return None

    def d(self, *variables: VariableRef) -> None:
        self._ensure_open()
        self._statements.append(DistinctStatement(tuple(variables)))

    def assertion(self, declaration: AssertionSignature) -> None:
        self._ensure_open()
        self._statements.append(AssertionSource(declaration))

    def block(self) -> _BlockContext:
        self._ensure_open()
        return _BlockContext(self._statements, self)

    def _ensure_open(self) -> None:
        if self._state != "active":
            raise AuthoringSemanticError("source block context is closed")


class SourceBuilder:
    def __init__(self) -> None:
        self._statements: list[SourceStatement] = []

    def block(self) -> _BlockContext:
        return _BlockContext(self._statements)

    def build(self) -> SourceBlock:
        return SourceBlock(tuple(self._statements))
