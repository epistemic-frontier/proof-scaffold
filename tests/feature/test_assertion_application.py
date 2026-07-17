from __future__ import annotations

from dataclasses import replace

import pytest

from skfd.authoring.assertion import (
    AssertionApplicationError,
    AssertionSignature,
    apply_assertion,
    finalize_proof,
    signature_from_axiom,
    signature_from_primitive_rule,
    start_draft,
)
from skfd.authoring.catalog import (
    AssertionCatalogError,
    AssertionCatalogSpec,
    AssertionProfileSpec,
    apply_assertion_by_id,
    resolve_assertion_catalog,
)
from skfd.authoring.ids import (
    AssertionCatalogId,
    AssertionProfileId,
    AssertionSemanticId,
    CalculusId,
    ConstructorId,
    Digest,
    JudgmentKindId,
    LanguageId,
    OwnerId,
    ProofId,
    RuleId,
    SortId,
    StepId,
    VariableKindId,
)
from skfd.authoring.judgment import (
    AxiomDecl,
    CalculusSpec,
    DistinctPair,
    Judgment,
    JudgmentKindDecl,
    PrimitiveRuleDecl,
    resolve_axiom,
    resolve_calculus,
)
from skfd.authoring.language import (
    BinderDecl,
    ConstructorDecl,
    LanguageRequirement,
    LanguageSpec,
    SortDecl,
    VariableKindDecl,
    resolve_language,
)
from skfd.authoring.replay import ResolvedDependency, build_semantic_replay_plan
from skfd.authoring.source import SourceBuilder, elaborate_block, start_draft_from_snapshot
from skfd.authoring.term import Var, VariableRef


def test_apply_assertion_elaborates_mp_and_preserves_failed_draft() -> None:
    wff = SortId("test#sort:wff")
    formula_kind = VariableKindId("test#variable-kind:formula")
    imp = ConstructorId("test#constructor:imp")
    language = resolve_language(
        LanguageSpec(
            id=LanguageId("test#language:prop"),
            sorts=(SortDecl(id=wff),),
            variable_kinds=(VariableKindDecl(id=formula_kind, sort=wff),),
            constructors=(ConstructorDecl(id=imp, inputs=(wff, wff), output=wff),),
        ),
        {},
    )
    provable = JudgmentKindId("test#judgment:provable")
    rule_id = RuleId("test#rule:mp")
    rule_owner = OwnerId(str(rule_id))
    phi_ref = VariableRef("schema", rule_owner, "phi", formula_kind)
    psi_ref = VariableRef("schema", rule_owner, "psi", formula_kind)
    phi, psi = language.variable(phi_ref), language.variable(psi_ref)
    rule = PrimitiveRuleDecl(
        id=rule_id,
        schema_variables=(phi_ref, psi_ref),
        premises=(
            Judgment(provable, (phi,)),
            Judgment(provable, (language.apply(imp, (phi, psi)),)),
        ),
        conclusion=Judgment(provable, (psi,)),
    )
    calculus = resolve_calculus(
        CalculusSpec(
            id=CalculusId("test#calculus:prop"),
            language=LanguageRequirement(id=language.id),
            judgments=(JudgmentKindDecl(id=provable, arguments=(wff,)),),
            rules=(rule,),
        ),
        language,
    )
    signature = signature_from_primitive_rule(
        calculus.rule(rule_id),
        assertion_id=AssertionSemanticId("test#assertion:ax-mp"),
        canonical_label="ax-mp",
    )

    actual_owner = OwnerId("test#proof:variables")
    p_ref = VariableRef("local", actual_owner, "p", formula_kind)
    q_ref = VariableRef("local", actual_owner, "q", formula_kind)
    p, q = language.variable(p_ref), language.variable(q_ref)
    draft = start_draft(
        ProofId("test#proof:mp"),
        calculus,
        (
            Judgment(provable, (p,)),
            Judgment(provable, (language.apply(imp, (p, q)),)),
        ),
    )
    applied = apply_assertion(
        draft,
        calculus,
        signature,
        tuple(step.id for step in draft.hypotheses),
    )

    assert applied.step.result == Judgment(provable, (q,))
    assert applied.step.substitution == ((phi_ref, p), (psi_ref, q))
    assert applied.draft.steps == (applied.step,)
    assert draft.steps == ()

    theorem_signature = AssertionSignature(
        id=AssertionSemanticId("test#theorem:mp-instance"),
        canonical_label="mp-instance",
        kind="theorem",
        schema_variables=rule.schema_variables,
        premises=rule.premises,
        conclusion=rule.conclusion,
    )
    theorem_source = SourceBuilder()
    with theorem_source.block() as block:
        block.assertion(theorem_signature)
    theorem_draft = start_draft_from_snapshot(
        ProofId("test#proof:mp-finalized"),
        calculus,
        elaborate_block(theorem_source.build()).assertions[0],
    )
    theorem_application = apply_assertion(
        theorem_draft,
        calculus,
        signature,
        tuple(step.id for step in theorem_draft.hypotheses),
    )
    proof = finalize_proof(
        theorem_application.draft,
        calculus,
        root=theorem_application.step.id,
    )
    assert proof.signature == theorem_signature
    assert proof.root == theorem_application.step.id
    assert proof.dependency_closure == (signature.id,)
    assert proof.replay_context.active_distinct == ()
    assert proof.semantic_digest == finalize_proof(
        theorem_application.draft,
        calculus,
        root=theorem_application.step.id,
    ).semantic_digest

    profile_id = AssertionProfileId("test#profile:mp")
    catalog = resolve_assertion_catalog(
        AssertionCatalogSpec(
            id=AssertionCatalogId("test#catalog:prop"),
            assertions=(signature,),
            profiles=(AssertionProfileSpec(id=profile_id, allowed=(signature.id,)),),
        )
    )
    with pytest.raises(AssertionCatalogError, match="duplicate assertion id"):
        resolve_assertion_catalog(
            AssertionCatalogSpec(
                id=AssertionCatalogId("test#catalog:duplicate-id"),
                assertions=(signature, signature),
                profiles=(),
            )
        )
    with pytest.raises(AssertionCatalogError, match="duplicate assertion label"):
        resolve_assertion_catalog(
            AssertionCatalogSpec(
                id=AssertionCatalogId("test#catalog:duplicate-label"),
                assertions=(
                    signature,
                    replace(theorem_signature, canonical_label="ax-mp"),
                ),
                profiles=(),
            )
        )
    with pytest.raises(AssertionCatalogError, match="unknown assertion"):
        resolve_assertion_catalog(
            AssertionCatalogSpec(
                id=AssertionCatalogId("test#catalog:missing-profile-entry"),
                assertions=(signature,),
                profiles=(
                    AssertionProfileSpec(
                        id=profile_id,
                        allowed=(theorem_signature.id,),
                    ),
                ),
            )
        )
    replay = build_semantic_replay_plan(proof, calculus, catalog, profile_id)
    assert replay.root_position == 2
    assert replay.applications[0].canonical_label == "ax-mp"
    assert replay.applications[0].premise_positions == (0, 1)
    assert replay.dependency_closure == (
        ResolvedDependency(signature.id, "primitive_rule"),
    )
    assert replay.replay_context.active_distinct == ()

    denied_profile = AssertionProfileId("test#profile:denied")
    denied_catalog = resolve_assertion_catalog(
        AssertionCatalogSpec(
            id=AssertionCatalogId("test#catalog:denied"),
            assertions=(signature,),
            profiles=(AssertionProfileSpec(id=denied_profile, allowed=()),),
        )
    )
    with pytest.raises(AssertionCatalogError, match="not allowed"):
        build_semantic_replay_plan(proof, calculus, denied_catalog, denied_profile)

    catalog_draft = start_draft(
        ProofId("test#proof:catalog-application"),
        calculus,
        theorem_signature.premises,
    )
    catalog_application = apply_assertion_by_id(
        catalog_draft,
        calculus,
        catalog,
        profile_id,
        signature.id,
        tuple(step.id for step in catalog_draft.hypotheses),
    )
    assert catalog_application.step.assertion == signature.id
    with pytest.raises(AssertionApplicationError, match="cannot cite itself"):
        apply_assertion(
            theorem_draft,
            calculus,
            theorem_signature,
            tuple(step.id for step in theorem_draft.hypotheses),
        )
    unsigned_draft = start_draft(
        ProofId("test#proof:late-signature"),
        calculus,
        theorem_signature.premises,
    )
    unsigned_self_application = apply_assertion(
        unsigned_draft,
        calculus,
        theorem_signature,
        tuple(step.id for step in unsigned_draft.hypotheses),
    )
    with pytest.raises(AssertionApplicationError, match="cannot cite itself"):
        replace(unsigned_self_application.draft, signature=theorem_signature)
    extra_application = apply_assertion(
        theorem_application.draft,
        calculus,
        signature,
        tuple(step.id for step in theorem_draft.hypotheses),
    )
    with pytest.raises(AssertionApplicationError, match="unreachable"):
        finalize_proof(
            extra_application.draft,
            calculus,
            root=theorem_application.step.id,
        )

    relabeled_signature = replace(theorem_signature, canonical_label="display-only-change")
    relabeled_draft = start_draft(
        ProofId("test#proof:different-nominal-id"),
        calculus,
        relabeled_signature.premises,
        signature=relabeled_signature,
    )
    relabeled_application = apply_assertion(
        relabeled_draft,
        calculus,
        signature,
        tuple(step.id for step in relabeled_draft.hypotheses),
    )
    relabeled_proof = finalize_proof(
        relabeled_application.draft,
        calculus,
        root=relabeled_application.step.id,
    )
    assert relabeled_proof.semantic_digest == proof.semantic_digest
    assert replace(
        proof,
        calculus_digest=Digest("0" * 64),
    ).semantic_digest != proof.semantic_digest
    with pytest.raises(AssertionApplicationError, match="must be a theorem"):
        replace(theorem_draft, signature=signature)
    with pytest.raises(AssertionApplicationError, match="does not match"):
        finalize_proof(
            theorem_application.draft,
            calculus,
            root=theorem_draft.hypotheses[0].id,
        )

    with pytest.raises(AssertionApplicationError):
        apply_assertion(
            draft,
            calculus,
            signature,
            tuple(reversed(tuple(step.id for step in draft.hypotheses))),
        )
    assert draft.steps == ()

    unused_ref = replace(psi_ref, local_key="unused")
    with pytest.raises(AssertionApplicationError, match="exactly match"):
        signature_from_primitive_rule(
            replace(rule, schema_variables=(*rule.schema_variables, unused_ref)),
            assertion_id=AssertionSemanticId("test#assertion:invalid"),
            canonical_label="invalid",
        )

    with pytest.raises(AssertionApplicationError, match="exactly match"):
        AssertionSignature(
            id=AssertionSemanticId("test#assertion:open"),
            canonical_label="open",
            kind="theorem",
            schema_variables=(),
            premises=(),
            conclusion=Judgment(provable, (phi,)),
        )
    malformed = AssertionSignature(
        id=AssertionSemanticId("test#assertion:malformed-sort"),
        canonical_label="malformed-sort",
        kind="theorem",
        schema_variables=(phi_ref,),
        premises=(),
        conclusion=Judgment(provable, (Var(phi_ref, SortId("test#sort:wrong")),)),
    )
    with pytest.raises(AssertionApplicationError, match="invalid assertion signature"):
        apply_assertion(
            start_draft(ProofId("test#proof:malformed"), calculus, ()),
            calculus,
            malformed,
            (),
            subst={phi_ref: p},
        )

    first_hypothesis = draft.hypotheses[0]
    with pytest.raises(AssertionApplicationError, match="noncanonical hypothesis"):
        replace(
            draft,
            hypotheses=(
                replace(first_hypothesis, id=StepId("test#proof:mp/step:9")),
                draft.hypotheses[1],
            ),
        )


def test_apply_assertion_checks_syntactic_dv_and_instantiates_binder_variables() -> None:
    wff = SortId("test#sort:wff")
    setvar = SortId("test#sort:setvar")
    formula_kind = VariableKindId("test#variable-kind:formula")
    setvar_kind = VariableKindId("test#variable-kind:setvar")
    imp = ConstructorId("test#constructor:imp")
    pred = ConstructorId("test#constructor:pred")
    all_ = ConstructorId("test#constructor:all")
    language = resolve_language(
        LanguageSpec(
            id=LanguageId("test#language:fol"),
            sorts=(SortDecl(id=wff), SortDecl(id=setvar)),
            variable_kinds=(
                VariableKindDecl(id=formula_kind, sort=wff),
                VariableKindDecl(id=setvar_kind, sort=setvar),
            ),
            constructors=(
                ConstructorDecl(id=imp, inputs=(wff, wff), output=wff),
                ConstructorDecl(id=pred, inputs=(setvar,), output=wff),
                ConstructorDecl(id=all_, inputs=(setvar, wff), output=wff),
            ),
            binders=(
                BinderDecl(
                    constructor=all_,
                    variable_argument=0,
                    scoped_arguments=(1,),
                ),
            ),
        ),
        {},
    )
    provable = JudgmentKindId("test#judgment:provable")
    calculus = resolve_calculus(
        CalculusSpec(
            id=CalculusId("test#calculus:fol"),
            language=LanguageRequirement(id=language.id),
            judgments=(JudgmentKindDecl(id=provable, arguments=(wff,)),),
        ),
        language,
    )
    axiom_id = AssertionSemanticId("test#axiom:ax-5")
    owner = OwnerId(str(axiom_id))
    phi_ref = VariableRef("schema", owner, "phi", formula_kind)
    x_ref = VariableRef("schema", owner, "x", setvar_kind)
    phi, x = language.variable(phi_ref), language.variable(x_ref)
    axiom = resolve_axiom(
        AxiomDecl(
            id=axiom_id,
            schema_variables=(phi_ref, x_ref),
            conclusion=Judgment(
                provable,
                (language.apply(imp, (phi, language.apply(all_, (x, phi)))),),
            ),
            mandatory_distinct=(DistinctPair(phi_ref, x_ref),),
        ),
        calculus,
    )
    signature = signature_from_axiom(axiom, canonical_label="ax-5")

    local_owner = OwnerId("test#proof:dv-variables")
    y_ref = VariableRef("local", local_owner, "y", setvar_kind)
    z_ref = VariableRef("local", local_owner, "z", setvar_kind)
    y, z = language.variable(y_ref), language.variable(z_ref)
    bound_formula = language.apply(all_, (y, language.apply(pred, (y,))))
    active = DistinctPair(y_ref, z_ref)
    draft = start_draft(
        ProofId("test#proof:ax-5"),
        calculus,
        (),
        active_distinct=(active,),
    )
    applied = apply_assertion(
        draft,
        calculus,
        signature,
        (),
        subst={phi_ref: bound_formula, x_ref: z},
    )
    expected = language.apply(
        imp,
        (bound_formula, language.apply(all_, (z, bound_formula))),
    )
    assert applied.step.result == Judgment(provable, (expected,))
    assert applied.step.satisfied_distinct == (active,)

    theorem_signature = AssertionSignature(
        id=AssertionSemanticId("test#theorem:ax-5-instance"),
        canonical_label="ax-5-instance",
        kind="theorem",
        schema_variables=(phi_ref, x_ref),
        premises=(),
        conclusion=axiom.declaration.conclusion,
    )
    theorem_source = SourceBuilder()
    with theorem_source.block() as block:
        block.d(phi_ref, x_ref)
        block.assertion(theorem_signature)
    snapshot = elaborate_block(theorem_source.build()).assertions[0]
    theorem_draft = start_draft_from_snapshot(
        ProofId("test#proof:ax-5-finalized"),
        calculus,
        snapshot,
    )
    theorem_application = apply_assertion(
        theorem_draft,
        calculus,
        signature,
        (),
        subst={phi_ref: phi, x_ref: x},
    )
    proof = finalize_proof(
        theorem_application.draft,
        calculus,
        root=theorem_application.step.id,
    )
    assert proof.replay_context.active_distinct == (DistinctPair(phi_ref, x_ref),)
    assert proof.signature.mandatory_distinct == (DistinctPair(phi_ref, x_ref),)

    reversed_draft = replace(
        draft,
        active_distinct=(DistinctPair(z_ref, y_ref),),
    )
    assert reversed_draft.active_distinct == (active,)
    assert apply_assertion(
        reversed_draft,
        calculus,
        signature,
        (),
        subst={phi_ref: bound_formula, x_ref: z},
    ).step.result == Judgment(provable, (expected,))

    no_dv_draft = start_draft(ProofId("test#proof:no-dv"), calculus, ())
    with pytest.raises(AssertionApplicationError, match="missing active"):
        apply_assertion(
            no_dv_draft,
            calculus,
            signature,
            (),
            subst={phi_ref: bound_formula, x_ref: z},
        )
    assert no_dv_draft.steps == ()

    overlapping = language.apply(all_, (z, language.apply(pred, (z,))))
    with pytest.raises(AssertionApplicationError, match="overlap"):
        apply_assertion(
            draft,
            calculus,
            signature,
            (),
            subst={phi_ref: overlapping, x_ref: z},
        )
