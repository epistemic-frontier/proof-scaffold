from __future__ import annotations

from dataclasses import replace

import pytest

from skfd.authoring.assertion import (
    AssertionApplicationError,
    AssertionSignature,
    apply_assertion,
    signature_from_primitive_rule,
)
from skfd.authoring.catalog import (
    AssertionCatalogSpec,
    AssertionProfileSpec,
    resolve_assertion_catalog,
)
from skfd.authoring.ids import (
    AssertionCatalogId,
    AssertionProfileId,
    AssertionSemanticId,
    CalculusId,
    JudgmentKindId,
    LanguageId,
    OwnerId,
    ProofId,
    RuleId,
    SortId,
    VariableKindId,
)
from skfd.authoring.judgment import (
    CalculusInterface,
    CalculusSpec,
    Judgment,
    JudgmentKindDecl,
    PrimitiveRuleDecl,
    resolve_calculus,
)
from skfd.authoring.language import (
    LanguageRequirement,
    LanguageSpec,
    SortDecl,
    VariableKindDecl,
    resolve_language,
)
from skfd.authoring.proof_author import ProofAuthor
from skfd.authoring.term import VariableRef


def _identity_author(
    proof_id: ProofId,
) -> tuple[ProofAuthor, AssertionSignature, CalculusInterface]:
    wff = SortId("test#sort:fast-author-wff")
    formula_kind = VariableKindId("test#variable-kind:fast-author-formula")
    language = resolve_language(
        LanguageSpec(
            id=LanguageId("test#language:fast-author"),
            sorts=(SortDecl(id=wff),),
            variable_kinds=(VariableKindDecl(id=formula_kind, sort=wff),),
            constructors=(),
        ),
        {},
    )
    provable = JudgmentKindId("test#judgment:fast-author-provable")
    rule_id = RuleId("test#rule:fast-author-identity")
    phi_ref = VariableRef(
        "schema",
        OwnerId(str(rule_id)),
        "phi",
        formula_kind,
    )
    phi = language.variable(phi_ref)
    rule = PrimitiveRuleDecl(
        id=rule_id,
        schema_variables=(phi_ref,),
        premises=(Judgment(provable, (phi,)),),
        conclusion=Judgment(provable, (phi,)),
    )
    calculus = resolve_calculus(
        CalculusSpec(
            id=CalculusId("test#calculus:fast-author"),
            language=LanguageRequirement(id=language.id),
            judgments=(JudgmentKindDecl(id=provable, arguments=(wff,)),),
            rules=(rule,),
        ),
        language,
    )
    identity = signature_from_primitive_rule(
        calculus.rule(rule_id),
        assertion_id=AssertionSemanticId("test#assertion:fast-author-identity"),
        canonical_label="fast-author-identity",
    )
    theorem = AssertionSignature(
        id=AssertionSemanticId("test#theorem:fast-author"),
        canonical_label="fast-author-theorem",
        kind="theorem",
        schema_variables=(phi_ref,),
        premises=rule.premises,
        conclusion=rule.conclusion,
    )
    profile = AssertionProfileId("test#profile:fast-author")
    catalog = resolve_assertion_catalog(
        AssertionCatalogSpec(
            id=AssertionCatalogId("test#catalog:fast-author"),
            assertions=(identity,),
            profiles=(AssertionProfileSpec(id=profile, allowed=(identity.id,)),),
        )
    )
    return (
        ProofAuthor(
            theorem,
            proof_id=proof_id,
            calculus=calculus,
            catalog=catalog,
            profile=profile,
        ),
        identity,
        calculus,
    )


def test_proof_author_caches_drafts_and_keeps_prior_snapshots_immutable() -> None:
    author, identity, _ = _identity_author(ProofId("test#proof:fast-author-cache"))

    initial = author.draft
    assert author.draft is initial

    first = author.use(identity, author.hypotheses[0])
    assert initial.steps == ()
    first_snapshot = author.draft
    assert first_snapshot.steps == (first,)
    assert author.draft is first_snapshot

    second = author.use(identity, first)
    assert first_snapshot.steps == (first,)
    second_snapshot = author.draft
    assert second_snapshot.steps == (first, second)
    assert second_snapshot is author.draft
    assert second_snapshot is not first_snapshot


def test_proof_author_accepts_only_steps_created_by_that_author() -> None:
    proof_id = ProofId("test#proof:fast-author-identity-only")
    author, identity, _ = _identity_author(proof_id)
    cloned_hypothesis = replace(author.hypotheses[0])
    assert cloned_hypothesis == author.hypotheses[0]
    assert cloned_hypothesis is not author.hypotheses[0]

    with pytest.raises(AssertionApplicationError, match="created by this author"):
        author.use(identity, cloned_hypothesis)

    own_root = author.use(identity, author.hypotheses[0])
    foreign_author, foreign_identity, _ = _identity_author(proof_id)
    foreign_root = foreign_author.use(
        foreign_identity,
        foreign_author.hypotheses[0],
    )
    assert foreign_root == own_root
    assert foreign_root is not own_root

    with pytest.raises(AssertionApplicationError, match="created by this author"):
        author.qed(foreign_root)
    with pytest.raises(AssertionApplicationError, match="created by this author"):
        author.qed(replace(own_root))


def test_failed_use_is_atomic_and_matches_public_apply_assertion() -> None:
    author, identity, calculus = _identity_author(
        ProofId("test#proof:fast-author-atomic")
    )
    before = author.draft

    with pytest.raises(AssertionApplicationError, match="premise count mismatch"):
        author.use(identity)

    assert author.draft is before
    expected = apply_assertion(
        before,
        calculus,
        identity,
        (author.hypotheses[0].id,),
    )
    actual = author.use(identity, author.hypotheses[0])

    assert actual == expected.step
    assert author.draft == expected.draft
