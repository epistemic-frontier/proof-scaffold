from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from skfd.authoring.assertion import (
    AssertionApplicationError,
    AssertionSignature,
    apply_assertion,
    create_proof_prefix,
    finalize_proof,
    signature_from_axiom,
    signature_from_primitive_rule,
)
from skfd.authoring.catalog import (
    AssertionCatalogError,
    AssertionCatalogRequirement,
    AssertionCatalogSpec,
    AssertionProfileSpec,
    apply_assertion_by_id,
    resolve_assertion_catalog,
)
from skfd.authoring.errors import AuthoringSemanticError
from skfd.authoring.ids import (
    AssertionCatalogId,
    AssertionId,
    AssertionProfileId,
    BackendBindingId,
    BackendVocabularyId,
    CalculusId,
    ConstructorId,
    Digest,
    FoundationId,
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
    BindingClause,
    ConstructorDecl,
    LanguageRequirement,
    LanguageSpec,
    SortDecl,
    VariableKindDecl,
    resolve_language,
)
from skfd.authoring.metamath_lowering import (
    MetamathAssertionBinding,
    MetamathProofBinding,
    MetamathProofOperation,
    lower_replay_to_metamath_proof,
)
from skfd.authoring.metamath_language import (
    ArgumentPart,
    FormationBinding,
    FoundationRequirement,
    LiteralPart,
    MetamathLanguageBinding,
    TokenRef,
    resolve_metamath_language,
)
from skfd.authoring.proof_author import ProofAuthor
from skfd.authoring.replay import ResolvedDependency, replay_proof
from skfd.authoring.source import (
    SourceBuilder,
    create_proof_prefix_from_snapshot,
    elaborate_block,
)
from skfd.authoring.term import Var, VariableRef
from skfd.core.symbols import SymbolInterner
from skfd.proof import Proof, Step

def test_renamed_api_compatibility_aliases_are_identical() -> None:
    from skfd.authoring.assertion import (
        ApplicationResult,
        AssertionApplicationResult,
        AssertionStep,
        CheckedProofPrefix,
        CompleteProof,
        ElaboratedProof,
        ElaboratedStep,
        ProofDraft,
        start_draft,
    )
    from skfd.authoring.ids import AssertionId, AssertionSemanticId
    from skfd.authoring.legacy_replay import (
        LegacyAssertionReplayBinding,
        LegacyReplayBinding,
        LegacyReplayOperation,
        lower_semantic_replay_plan,
    )
    from skfd.authoring.metamath_lowering import MetamathProofOperation
    from skfd.authoring.replay import (
        ReplaySequence,
        SemanticReplayPlan,
        build_semantic_replay_plan,
    )
    from skfd.authoring.source import start_draft_from_snapshot

    assert AssertionSemanticId is AssertionId
    assert ProofDraft is CheckedProofPrefix
    assert ElaboratedStep is AssertionStep
    assert ApplicationResult is AssertionApplicationResult
    assert ElaboratedProof is CompleteProof
    assert SemanticReplayPlan is ReplaySequence
    assert LegacyAssertionReplayBinding is MetamathAssertionBinding
    assert LegacyReplayBinding is MetamathProofBinding
    assert LegacyReplayOperation is MetamathProofOperation
    assert start_draft is create_proof_prefix
    assert start_draft_from_snapshot is create_proof_prefix_from_snapshot
    assert build_semantic_replay_plan is replay_proof
    assert lower_semantic_replay_plan is lower_replay_to_metamath_proof


def test_apply_assertion_elaborates_mp_and_preserves_failed_prefix() -> None:
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
        assertion_id=AssertionId("test#assertion:ax-mp"),
        canonical_label="ax-mp",
    )

    actual_owner = OwnerId("test#proof:variables")
    p_ref = VariableRef("local", actual_owner, "p", formula_kind)
    q_ref = VariableRef("local", actual_owner, "q", formula_kind)
    p, q = language.variable(p_ref), language.variable(q_ref)
    prefix = create_proof_prefix(
        ProofId("test#proof:mp"),
        calculus,
        (
            Judgment(provable, (p,)),
            Judgment(provable, (language.apply(imp, (p, q)),)),
        ),
    )
    applied = apply_assertion(
        prefix,
        calculus,
        signature,
        tuple(step.id for step in prefix.hypotheses),
    )

    assert applied.step.result == Judgment(provable, (q,))
    assert applied.step.substitution == ((phi_ref, p), (psi_ref, q))
    assert applied.prefix.steps == (applied.step,)
    assert prefix.steps == ()
    assert applied.draft is applied.prefix

    theorem_signature = AssertionSignature(
        id=AssertionId("test#theorem:mp-instance"),
        canonical_label="mp-instance",
        kind="theorem",
        schema_variables=rule.schema_variables,
        premises=rule.premises,
        conclusion=rule.conclusion,
    )
    theorem_source = SourceBuilder()
    with theorem_source.block() as block:
        block.assertion(theorem_signature)
    theorem_prefix = create_proof_prefix_from_snapshot(
        ProofId("test#proof:mp-finalized"),
        calculus,
        elaborate_block(theorem_source.build()).assertions[0],
    )
    theorem_application = apply_assertion(
        theorem_prefix,
        calculus,
        signature,
        tuple(step.id for step in theorem_prefix.hypotheses),
    )
    proof = finalize_proof(
        theorem_application.prefix,
        calculus,
        root=theorem_application.step.id,
    )
    assert proof.signature == theorem_signature
    assert proof.root == theorem_application.step.id
    assert proof.dependency_closure == (signature.id,)
    assert proof.replay_context.active_distinct == ()
    assert proof.semantic_digest == finalize_proof(
        theorem_application.prefix,
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
    extended_profile = AssertionProfileId("test#profile:extended")
    extended_catalog = resolve_assertion_catalog(
        AssertionCatalogSpec(
            id=AssertionCatalogId("test#catalog:extended"),
            assertions=(theorem_signature,),
            profiles=(
                AssertionProfileSpec(
                    id=extended_profile,
                    allowed=(signature.id, theorem_signature.id),
                ),
            ),
            extends=(
                AssertionCatalogRequirement(id=catalog.id, digest=catalog.digest),
            ),
        ),
        {catalog.id: catalog},
    )
    assert extended_catalog.assertion(signature.id, profile=extended_profile) == signature
    assert extended_catalog.assertion(
        theorem_signature.id,
        profile=extended_profile,
    ) == theorem_signature
    assert profile_id in extended_catalog.profiles
    with pytest.raises(AssertionCatalogError, match="digest mismatch"):
        resolve_assertion_catalog(
            replace(
                AssertionCatalogSpec(
                    id=AssertionCatalogId("test#catalog:bad-dependency"),
                    assertions=(),
                    profiles=(),
                ),
                extends=(
                    AssertionCatalogRequirement(
                        id=catalog.id,
                        digest=Digest("0" * 64),
                    ),
                ),
            ),
            {catalog.id: catalog},
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
    replay = replay_proof(proof, calculus, catalog, profile_id)
    assert replay.root_position == 2
    assert replay.applications[0].canonical_label == "ax-mp"
    assert replay.applications[0].premise_positions == (0, 1)
    assert replay.dependency_closure == (
        ResolvedDependency(signature.id, "primitive_rule"),
    )
    assert replay.replay_context.active_distinct == ()

    author = ProofAuthor(
        theorem_signature,
        proof_id=ProofId("test#proof:authored-mp"),
        calculus=calculus,
        catalog=catalog,
        profile=profile_id,
    )
    authored_step = author.use(signature, *author.hypotheses)
    authored_proof = author.qed(authored_step)
    assert authored_proof.semantic_digest == proof.semantic_digest
    foreign_author = ProofAuthor(
        theorem_signature,
        proof_id=ProofId("test#proof:foreign-author"),
        calculus=calculus,
        catalog=catalog,
        profile=profile_id,
    )
    with pytest.raises(AssertionApplicationError, match="ProofAuthor arguments"):
        author.use(signature, *foreign_author.hypotheses)
    with pytest.raises(AssertionApplicationError, match="positions are not canonical"):
        replace(
            replay,
            applications=(replace(replay.applications[0], position=3),),
        )
    with pytest.raises(AuthoringSemanticError, match="unsupported Metamath proof"):
        MetamathAssertionBinding(
            assertion=signature.id,
            backend_label="ax-mp",
            operation=cast(MetamathProofOperation, "raw"),
        )
    with pytest.raises(AuthoringSemanticError, match="only supports the mp"):
        MetamathAssertionBinding(
            assertion=signature.id,
            backend_label="other",
            operation="apply",
            legacy_rule="other",
        )

    vocabulary = BackendVocabularyId("test#vocabulary:mm")
    left_token = TokenRef(vocabulary, "(")
    imp_token = TokenRef(vocabulary, "->")
    right_token = TokenRef(vocabulary, ")")
    backend = resolve_metamath_language(
        MetamathLanguageBinding(
            id=BackendBindingId("test#binding:mm"),
            language=LanguageRequirement(
                id=language.id,
                semantic_digest=language.semantic_digest,
            ),
            foundation=FoundationRequirement(id=FoundationId("test#foundation:mm")),
            formations=(
                FormationBinding(
                    constructor=imp,
                    syntax_assertion=AssertionId("test#formation:imp"),
                    syntax_assertion_label="wi",
                    template=(
                        LiteralPart(left_token),
                        ArgumentPart(0),
                        LiteralPart(imp_token),
                        ArgumentPart(1),
                        LiteralPart(right_token),
                    ),
                ),
            ),
        ),
        language,
        {},
    )
    interner = SymbolInterner()
    token_symbols = {
        token: interner.intern(
            origin_module_id="test",
            local_name=token.local_name,
            kind="Const",
            origin_ref=0,
        )
        for token in (left_token, imp_token, right_token)
    }
    variable_symbols = {
        variable: interner.intern(
            origin_module_id="test",
            local_name=variable.local_key,
            kind="Var",
            origin_ref=0,
        )
        for variable in theorem_signature.schema_variables
    }
    legacy = lower_replay_to_metamath_proof(
        replay,
        MetamathProofBinding(
            language=backend,
            provable_judgment=provable,
            assertions=(
                MetamathAssertionBinding(
                    assertion=signature.id,
                    backend_label="ax-mp",
                    operation="apply",
                    legacy_rule="mp",
                ),
            ),
            token_symbols=token_symbols,
            variable_symbols=variable_symbols,
            legacy_sorts={wff: "wff"},
            symbol_table=interner.symbol_table(),
        ),
        proof_name="mp-instance",
    )
    phi_symbol = variable_symbols[phi_ref]
    psi_symbol = variable_symbols[psi_ref]
    implication = (
        token_symbols[left_token],
        phi_symbol,
        token_symbols[imp_token],
        psi_symbol,
        token_symbols[right_token],
    )
    assert legacy == Proof(
        "mp-instance",
        legacy.statement,
        (
            Step("mp-instance.1", legacy.steps[0].wff, "Hypothesis", op="hyp"),
            Step("mp-instance.2", legacy.steps[1].wff, "Hypothesis", op="hyp"),
            Step(
                "res",
                legacy.statement,
                "ax-mp",
                op="apply",
                args=("mp-instance.1", "mp-instance.2"),
                ref="mp",
            ),
        ),
    )
    assert legacy.steps[0].wff.tokens == (phi_symbol,)
    assert legacy.steps[1].wff.tokens == implication

    hypothesis_root_signature = AssertionSignature(
        id=AssertionId("test#theorem:hypothesis-root"),
        canonical_label="hypothesis-root",
        kind="theorem",
        schema_variables=(phi_ref, psi_ref),
        premises=(Judgment(provable, (phi,)), Judgment(provable, (psi,))),
        conclusion=Judgment(provable, (phi,)),
    )
    hypothesis_root_prefix = create_proof_prefix(
        ProofId("test#proof:hypothesis-root"),
        calculus,
        hypothesis_root_signature.premises,
        signature=hypothesis_root_signature,
    )
    hypothesis_root_proof = finalize_proof(
        hypothesis_root_prefix,
        calculus,
        root=hypothesis_root_prefix.hypotheses[0].id,
    )
    hypothesis_root_replay = replay_proof(
        hypothesis_root_proof,
        calculus,
        catalog,
        profile_id,
    )
    with pytest.raises(AuthoringSemanticError, match="root to be the final"):
        lower_replay_to_metamath_proof(
            hypothesis_root_replay,
            MetamathProofBinding(
                language=backend,
                provable_judgment=provable,
                assertions=(),
                token_symbols=token_symbols,
                variable_symbols=variable_symbols,
                legacy_sorts={wff: "wff"},
                symbol_table=interner.symbol_table(),
            ),
            proof_name="hypothesis-root",
        )

    denied_profile = AssertionProfileId("test#profile:denied")
    denied_catalog = resolve_assertion_catalog(
        AssertionCatalogSpec(
            id=AssertionCatalogId("test#catalog:denied"),
            assertions=(signature,),
            profiles=(AssertionProfileSpec(id=denied_profile, allowed=()),),
        )
    )
    with pytest.raises(AssertionCatalogError, match="not allowed"):
        replay_proof(proof, calculus, denied_catalog, denied_profile)

    catalog_prefix = create_proof_prefix(
        ProofId("test#proof:catalog-application"),
        calculus,
        theorem_signature.premises,
    )
    catalog_application = apply_assertion_by_id(
        catalog_prefix,
        calculus,
        catalog,
        profile_id,
        signature.id,
        tuple(step.id for step in catalog_prefix.hypotheses),
    )
    assert catalog_application.step.assertion == signature.id
    with pytest.raises(AssertionApplicationError, match="cannot cite itself"):
        apply_assertion(
            theorem_prefix,
            calculus,
            theorem_signature,
            tuple(step.id for step in theorem_prefix.hypotheses),
        )
    unsigned_prefix = create_proof_prefix(
        ProofId("test#proof:late-signature"),
        calculus,
        theorem_signature.premises,
    )
    unsigned_self_application = apply_assertion(
        unsigned_prefix,
        calculus,
        theorem_signature,
        tuple(step.id for step in unsigned_prefix.hypotheses),
    )
    with pytest.raises(AssertionApplicationError, match="cannot cite itself"):
        replace(unsigned_self_application.prefix, signature=theorem_signature)
    extra_application = apply_assertion(
        theorem_application.prefix,
        calculus,
        signature,
        tuple(step.id for step in theorem_prefix.hypotheses),
    )
    with pytest.raises(AssertionApplicationError, match="unreachable"):
        finalize_proof(
            extra_application.prefix,
            calculus,
            root=theorem_application.step.id,
        )

    relabeled_signature = replace(theorem_signature, canonical_label="display-only-change")
    relabeled_prefix = create_proof_prefix(
        ProofId("test#proof:different-nominal-id"),
        calculus,
        relabeled_signature.premises,
        signature=relabeled_signature,
    )
    relabeled_application = apply_assertion(
        relabeled_prefix,
        calculus,
        signature,
        tuple(step.id for step in relabeled_prefix.hypotheses),
    )
    relabeled_proof = finalize_proof(
        relabeled_application.prefix,
        calculus,
        root=relabeled_application.step.id,
    )
    assert relabeled_proof.semantic_digest == proof.semantic_digest
    assert replace(
        proof,
        calculus_digest=Digest("0" * 64),
    ).semantic_digest != proof.semantic_digest
    with pytest.raises(AssertionApplicationError, match="must be a theorem"):
        replace(theorem_prefix, signature=signature)
    with pytest.raises(AssertionApplicationError, match="does not match"):
        finalize_proof(
            theorem_application.prefix,
            calculus,
            root=theorem_prefix.hypotheses[0].id,
        )

    with pytest.raises(AssertionApplicationError):
        apply_assertion(
            prefix,
            calculus,
            signature,
            tuple(reversed(tuple(step.id for step in prefix.hypotheses))),
        )
    assert prefix.steps == ()

    unused_ref = replace(psi_ref, local_key="unused")
    with pytest.raises(AssertionApplicationError, match="exactly match"):
        signature_from_primitive_rule(
            replace(rule, schema_variables=(*rule.schema_variables, unused_ref)),
            assertion_id=AssertionId("test#assertion:invalid"),
            canonical_label="invalid",
        )

    with pytest.raises(AssertionApplicationError, match="exactly match"):
        AssertionSignature(
            id=AssertionId("test#assertion:open"),
            canonical_label="open",
            kind="theorem",
            schema_variables=(),
            premises=(),
            conclusion=Judgment(provable, (phi,)),
        )
    malformed = AssertionSignature(
        id=AssertionId("test#assertion:malformed-sort"),
        canonical_label="malformed-sort",
        kind="theorem",
        schema_variables=(phi_ref,),
        premises=(),
        conclusion=Judgment(provable, (Var(phi_ref, SortId("test#sort:wrong")),)),
    )
    with pytest.raises(AssertionApplicationError, match="invalid assertion signature"):
        apply_assertion(
            create_proof_prefix(ProofId("test#proof:malformed"), calculus, ()),
            calculus,
            malformed,
            (),
            subst={phi_ref: p},
        )

    first_hypothesis = prefix.hypotheses[0]
    with pytest.raises(AssertionApplicationError, match="noncanonical hypothesis"):
        replace(
            prefix,
            hypotheses=(
                replace(first_hypothesis, id=StepId("test#proof:mp/step:9")),
                prefix.hypotheses[1],
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
                    bindings=(
                        BindingClause(variable_argument=0, scoped_arguments=(1,)),
                    ),
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
    axiom_id = AssertionId("test#axiom:ax-5")
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
    prefix = create_proof_prefix(
        ProofId("test#proof:ax-5"),
        calculus,
        (),
        active_distinct=(active,),
    )
    applied = apply_assertion(
        prefix,
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
        id=AssertionId("test#theorem:ax-5-instance"),
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
    theorem_prefix = create_proof_prefix_from_snapshot(
        ProofId("test#proof:ax-5-finalized"),
        calculus,
        snapshot,
    )
    theorem_application = apply_assertion(
        theorem_prefix,
        calculus,
        signature,
        (),
        subst={phi_ref: phi, x_ref: x},
    )
    proof = finalize_proof(
        theorem_application.prefix,
        calculus,
        root=theorem_application.step.id,
    )
    assert proof.replay_context.active_distinct == (DistinctPair(phi_ref, x_ref),)
    assert proof.signature.mandatory_distinct == (DistinctPair(phi_ref, x_ref),)

    reversed_prefix = replace(
        prefix,
        active_distinct=(DistinctPair(z_ref, y_ref),),
    )
    assert reversed_prefix.active_distinct == (active,)
    assert apply_assertion(
        reversed_prefix,
        calculus,
        signature,
        (),
        subst={phi_ref: bound_formula, x_ref: z},
    ).step.result == Judgment(provable, (expected,))

    no_dv_prefix = create_proof_prefix(ProofId("test#proof:no-dv"), calculus, ())
    with pytest.raises(AssertionApplicationError, match="missing active"):
        apply_assertion(
            no_dv_prefix,
            calculus,
            signature,
            (),
            subst={phi_ref: bound_formula, x_ref: z},
        )
    assert no_dv_prefix.steps == ()

    overlapping = language.apply(all_, (z, language.apply(pred, (z,))))
    with pytest.raises(AssertionApplicationError, match="overlap"):
        apply_assertion(
            prefix,
            calculus,
            signature,
            (),
            subst={phi_ref: overlapping, x_ref: z},
        )
