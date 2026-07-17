from __future__ import annotations

from typing import cast

import pytest

from skfd.authoring.assertion import AssertionSignature
from skfd.authoring.errors import AuthoringSemanticError
from skfd.authoring.ids import (
    AssertionSemanticId,
    JudgmentKindId,
    OwnerId,
    SortId,
    VariableKindId,
)
from skfd.authoring.judgment import DistinctPair, Judgment
from skfd.authoring.source import (
    AssertionSource,
    AssertionSourceSnapshot,
    DistinctStatement,
    SourceBlock,
    SourceBuilder,
    SourceStatement,
    elaborate_block,
)
from skfd.authoring.term import Var, VariableRef


WFF = SortId("test#sort:wff")
FORMULA = VariableKindId("test#variable-kind:formula")
PROVABLE_MANY = JudgmentKindId("test#judgment:provable-many")
OWNER = OwnerId("test#source:variables")
X_REF = VariableRef("schema", OWNER, "x", FORMULA)
Y_REF = VariableRef("schema", OWNER, "y", FORMULA)
Z_REF = VariableRef("schema", OWNER, "z", FORMULA)


def _signature(name: str, *variables: VariableRef) -> AssertionSignature:
    return AssertionSignature(
        id=AssertionSemanticId(f"test#assertion:{name}"),
        canonical_label=name,
        kind="axiom",
        schema_variables=tuple(variables),
        premises=(),
        conclusion=Judgment(
            PROVABLE_MANY,
            tuple(Var(variable, WFF) for variable in variables),
        ),
    )


def test_nested_blocks_inherit_distinct_relations_without_leaking_on_exit() -> None:
    source = SourceBuilder()
    with source.block() as outer:
        outer.d(X_REF, Y_REF)
        outer.assertion(_signature("outer-before", X_REF, Y_REF, Z_REF))
        with outer.block() as inner:
            inner.d(Y_REF, Z_REF)
            inner.assertion(_signature("inner", X_REF, Y_REF, Z_REF))
        outer.assertion(_signature("outer-after", X_REF, Y_REF, Z_REF))

    snapshots = elaborate_block(source.build()).assertions
    xy = DistinctPair(X_REF, Y_REF)
    yz = DistinctPair(Y_REF, Z_REF)
    assert snapshots[0].active_distinct == (xy,)
    assert snapshots[1].active_distinct == (xy, yz)
    assert snapshots[2].active_distinct == (xy,)


def test_distinct_groups_expand_exact_pairs_without_transitive_closure() -> None:
    grouped = SourceBuilder()
    with grouped.block() as block:
        block.d(X_REF, Y_REF, Z_REF)
        block.assertion(_signature("grouped", X_REF, Y_REF, Z_REF))
    grouped_snapshot = elaborate_block(grouped.build()).assertions[0]
    assert grouped_snapshot.active_distinct == (
        DistinctPair(X_REF, Y_REF),
        DistinctPair(X_REF, Z_REF),
        DistinctPair(Y_REF, Z_REF),
    )

    chain = SourceBuilder()
    with chain.block() as block:
        block.d(X_REF, Y_REF)
        block.d(Y_REF, Z_REF)
        block.assertion(_signature("chain", X_REF, Y_REF, Z_REF))
    chain_snapshot = elaborate_block(chain.build()).assertions[0]
    assert chain_snapshot.active_distinct == (
        DistinctPair(X_REF, Y_REF),
        DistinctPair(Y_REF, Z_REF),
    )


def test_assertion_snapshot_separates_full_active_and_mandatory_relations() -> None:
    source = SourceBuilder()
    with source.block() as block:
        block.d(X_REF, Y_REF, Z_REF)
        block.assertion(_signature("xy-only", X_REF, Y_REF))

    snapshot = elaborate_block(source.build()).assertions[0]
    assert snapshot.active_distinct == (
        DistinctPair(X_REF, Y_REF),
        DistinctPair(X_REF, Z_REF),
        DistinctPair(Y_REF, Z_REF),
    )
    assert snapshot.declaration.mandatory_distinct == (DistinctPair(X_REF, Y_REF),)


def test_source_grouping_changes_source_digest_but_not_semantic_digest() -> None:
    grouped = SourceBuilder()
    with grouped.block() as block:
        block.d(X_REF, Y_REF, Z_REF)
        block.assertion(_signature("same", X_REF, Y_REF, Z_REF))

    split = SourceBuilder()
    with split.block() as block:
        block.d(X_REF, Y_REF)
        block.d(X_REF, Z_REF)
        block.d(Y_REF, Z_REF)
        block.assertion(_signature("same", X_REF, Y_REF, Z_REF))

    grouped_result = elaborate_block(grouped.build())
    split_result = elaborate_block(split.build())
    assert grouped_result.source_digest != split_result.source_digest
    assert grouped_result.semantic_digest == split_result.semantic_digest


def test_digests_include_assertion_content_not_only_nominal_identity() -> None:
    original = _signature("same-id", X_REF, Y_REF)
    changed = AssertionSignature(
        id=original.id,
        canonical_label=original.canonical_label,
        kind=original.kind,
        schema_variables=original.schema_variables,
        premises=(),
        conclusion=Judgment(
            PROVABLE_MANY,
            (Var(Y_REF, WFF), Var(X_REF, WFF)),
        ),
    )
    first = elaborate_block(SourceBlock((AssertionSource(original),)))
    second = elaborate_block(SourceBlock((AssertionSource(changed),)))
    assert first.source_digest != second.source_digest
    assert first.semantic_digest != second.semantic_digest


def test_source_ir_rejects_mutable_or_malformed_payloads() -> None:
    with pytest.raises(AuthoringSemanticError, match="tuple of variables"):
        DistinctStatement(cast(tuple[VariableRef, ...], [X_REF, Y_REF]))
    with pytest.raises(AuthoringSemanticError, match="tuple of variables"):
        DistinctStatement(cast(tuple[VariableRef, ...], (X_REF, object())))
    with pytest.raises(AuthoringSemanticError, match="invalid statement"):
        SourceBlock(cast(tuple[SourceStatement, ...], [DistinctStatement((X_REF, Y_REF))]))
    with pytest.raises(AuthoringSemanticError, match="invalid statement"):
        SourceBlock(cast(tuple[SourceStatement, ...], (object(),)))
    with pytest.raises(AuthoringSemanticError, match="mandatory distinct"):
        AssertionSourceSnapshot(
            _signature("snapshot-mismatch", X_REF, Y_REF),
            (DistinctPair(X_REF, Y_REF),),
        )


def test_block_contexts_are_single_use_and_respect_parent_lifetime() -> None:
    source = SourceBuilder()
    parent = source.block()
    parent.__enter__()
    with pytest.raises(AuthoringSemanticError, match="cannot be reused"):
        parent.__enter__()
    child = parent.block()
    child.__enter__()
    with pytest.raises(AuthoringSemanticError, match="active nested"):
        parent.__exit__(None, None, None)
    child.__exit__(None, None, None)
    parent.__exit__(None, None, None)
    with pytest.raises(AuthoringSemanticError, match="not active"):
        parent.__exit__(None, None, None)

    closed_parent = source.block()
    closed_parent.__enter__()
    orphan = closed_parent.block()
    closed_parent.__exit__(None, None, None)
    with pytest.raises(AuthoringSemanticError, match="parent is not active"):
        orphan.__enter__()
