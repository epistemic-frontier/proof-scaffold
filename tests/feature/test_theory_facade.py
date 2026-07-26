from __future__ import annotations

import io
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import cast

import pytest

from skfd.api_v2 import BuildConfig
from skfd.authoring._canonical import JsonValue, canonical_digest
from skfd.authoring.assertion import (
    CompleteProof,
    assertion_signature_document,
    signature_from_primitive_rule,
)
from skfd.authoring.ids import (
    AssertionId,
    BackendBindingId,
    BackendVocabularyId,
    CalculusId,
    ConstructorId,
    Digest,
    FoundationId,
    JudgmentKindId,
    LanguageId,
    NotationId,
    OwnerId,
    RuleId,
    SortId,
    StepId,
    VariableKindId,
)
from skfd.authoring.judgment import (
    CalculusSpec,
    DistinctPair,
    Judgment,
    JudgmentKindDecl,
    PrimitiveRuleDecl,
    resolve_calculus,
)
from skfd.authoring.language import (
    ConstructorDecl,
    LanguageRequirement,
    LanguageSpec,
    SortDecl,
    VariableKindDecl,
    resolve_language,
)
from skfd.authoring.metamath_emission import (
    MetamathEmissionBinding,
    MetamathEmissionContext,
    MetamathEmissionEntry,
    MetamathEmissionError,
    MetamathFloatingEmission,
    MetamathFormationEmission,
    emit_semantic_metamath_theory,
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
from skfd.authoring.notation import (
    InfixForm,
    NotationDecl,
    NotationSpec,
    PrefixForm,
    resolve_notation,
)
from skfd.authoring.term import VariableRef
from skfd.authoring.term_ops import variables
from skfd.authoring.theory import (
    AssertionHandle,
    Theory,
    TheoryError,
    TheoryProofAuthor,
    UpstreamPin,
)
from skfd.builder_v2 import MMBuilderV2
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver
from skfd.verifier import mmverify

_NAMESPACE = "test-theory"
_WFF = SortId(f"{_NAMESPACE}#sort:wff")
_WFF_KIND = VariableKindId(f"{_NAMESPACE}#variable-kind:wff")
_IMP = ConstructorId(f"{_NAMESPACE}#constructor:imp")
_NOT = ConstructorId(f"{_NAMESPACE}#constructor:not")
_PROVABLE = JudgmentKindId(f"{_NAMESPACE}#judgment:provable")
_MP_RULE = RuleId(f"{_NAMESPACE}#rule:mp")


@dataclass(frozen=True)
class _Fixture:
    theory: Theory


def _make_theory(
    namespace: str = _NAMESPACE,
    *,
    mp_distinct: bool = False,
    declaration_order: tuple[str, ...] | None = None,
) -> Theory:
    language = resolve_language(
        LanguageSpec(
            id=LanguageId(f"{_NAMESPACE}#language:prop"),
            sorts=(SortDecl(id=_WFF),),
            variable_kinds=(VariableKindDecl(id=_WFF_KIND, sort=_WFF),),
            constructors=(
                ConstructorDecl(id=_IMP, inputs=(_WFF, _WFF), output=_WFF),
                ConstructorDecl(id=_NOT, inputs=(_WFF,), output=_WFF),
            ),
        ),
        {},
    )
    mp_owner = OwnerId(str(_MP_RULE))
    mp_phi = VariableRef("schema", mp_owner, "φ", _WFF_KIND)
    mp_psi = VariableRef("schema", mp_owner, "ψ", _WFF_KIND)
    phi = language.variable(mp_phi)
    psi = language.variable(mp_psi)
    calculus = resolve_calculus(
        CalculusSpec(
            id=CalculusId(f"{_NAMESPACE}#calculus:prop"),
            language=LanguageRequirement(
                id=language.id, semantic_digest=language.semantic_digest
            ),
            judgments=(JudgmentKindDecl(id=_PROVABLE, arguments=(_WFF,)),),
            rules=(
                PrimitiveRuleDecl(
                    id=_MP_RULE,
                    schema_variables=(mp_phi, mp_psi),
                    premises=(
                        Judgment(_PROVABLE, (phi,)),
                        Judgment(_PROVABLE, (language.apply(_IMP, (phi, psi)),)),
                    ),
                    conclusion=Judgment(_PROVABLE, (psi,)),
                    mandatory_distinct=(
                        (DistinctPair(mp_phi, mp_psi),) if mp_distinct else ()
                    ),
                ),
            ),
        ),
        language,
    )
    notation = resolve_notation(
        NotationSpec(
            id=NotationId(f"{_NAMESPACE}#notation:prop"),
            language=LanguageRequirement(
                id=language.id, semantic_digest=language.semantic_digest
            ),
            declarations=(
                NotationDecl(
                    constructor=_IMP,
                    form=InfixForm(token="→", precedence=25, associativity="right"),
                ),
                NotationDecl(
                    constructor=_NOT,
                    form=PrefixForm(token="¬", precedence=40),
                ),
            ),
        ),
        language,
        {},
    )
    return Theory.create(
        theory_id=f"{namespace}#theory:main",
        namespace=namespace,
        language=language,
        calculus=calculus,
        notation=notation,
        provable_judgment=_PROVABLE,
        variable_kinds={"wff": _WFF_KIND},
        declaration_order=declaration_order,
    )


def _declare_a1i(
    theory: Theory, ax_1: AssertionHandle, mp: AssertionHandle
) -> tuple[AssertionHandle, list[str]]:
    calls: list[str] = []
    a1i = theory.theorem(
        "a1i",
        schema=("φ:wff", "ψ:wff"),
        premises=("φ",),
        conclusion="ψ → φ",
    )

    @a1i.proof
    def prove_a1i(proof: TheoryProofAuthor) -> CompleteProof:
        calls.append("a1i")
        (h1,) = proof.hypotheses
        s1 = proof.use(ax_1, subst={"φ": "φ", "ψ": "ψ"})
        s2 = proof.use(mp, h1, s1)
        return proof.qed(s2)

    return a1i, calls


def test_theorem_lazy_elaboration_and_caching() -> None:
    theory = _make_theory()
    ax_1 = theory.axiom(
        "ax-1",
        schema=("φ:wff", "ψ:wff"),
        conclusion="φ → (ψ → φ)",
    )
    mp = theory.primitive_rule("mp")
    a1i, calls = _declare_a1i(theory, ax_1, mp)

    assert calls == []  # registration never elaborates
    proof = a1i.implementation
    assert calls == ["a1i"]
    assert isinstance(proof, CompleteProof)
    assert proof.signature is a1i.signature
    assert a1i.implementation is proof
    assert calls == ["a1i"]  # elaboration happens exactly once

    report = theory.verify_all()
    assert report.ok
    assert [entry.label for entry in report.entries] == ["ax-1", "mp", "a1i"]


def test_concise_proof_author_call_surface() -> None:
    theory = _make_theory()
    ax_1 = theory.axiom(
        "ax-1",
        schema=("φ:wff", "ψ:wff"),
        conclusion="φ → (ψ → φ)",
    )
    mp = theory.primitive_rule("mp")
    a1i = theory.theorem(
        "a1i",
        schema=("φ:wff", "ψ:wff"),
        premises=("φ",),
        conclusion="ψ → φ",
    )

    @a1i.proof
    def prove_a1i(p: TheoryProofAuthor) -> CompleteProof:
        (h1,) = p.hyps
        axiom = p(ax_1, φ="φ", ψ="ψ")
        return p.qed(p(mp, h1, axiom))

    assert a1i.implementation.signature is a1i.signature
    assert theory.verify_all().ok


def test_predeclared_order_is_independent_of_registration_order() -> None:
    theory = _make_theory(declaration_order=("ax-first", "ax-middle", "ax-last"))
    last = theory.axiom(
        "ax-last",
        schema=("φ:wff",),
        conclusion="φ → φ",
    )
    first = theory.axiom(
        "ax-first",
        schema=("φ:wff",),
        conclusion="φ → φ",
    )

    live_view = theory.assertions
    assert tuple(live_view) == ("ax-first", "ax-last")
    assert theory.assertions["ax-first"] is first
    assert theory.assertions["ax-last"] is last
    assert not theory.assertions_complete
    with pytest.raises(TheoryError, match="missing predeclared assertion: ax-middle"):
        theory.verify_all()

    middle = theory.axiom(
        "ax-middle",
        schema=("φ:wff",),
        conclusion="φ → φ",
    )
    assert theory.assertions_complete
    assert tuple(live_view) == ("ax-first", "ax-middle", "ax-last")
    assert theory.declaration_order == (
        "ax-first",
        "ax-middle",
        "ax-last",
    )
    assert tuple(theory.assertions.values()) == (first, middle, last)
    assert [entry.label for entry in theory.verify_all().entries] == [
        "ax-first",
        "ax-middle",
        "ax-last",
    ]


def test_predeclared_order_rejects_invalid_or_unknown_labels() -> None:
    with pytest.raises(TheoryError, match="sequence of assertion labels"):
        _make_theory(declaration_order=cast(tuple[str, ...], "ax-1"))
    with pytest.raises(TheoryError, match="non-empty strings"):
        _make_theory(declaration_order=("ax-1", ""))
    with pytest.raises(TheoryError, match="duplicate assertion labels"):
        _make_theory(declaration_order=("ax-1", "ax-1"))

    theory = _make_theory(declaration_order=("ax-1",))
    with pytest.raises(TheoryError, match="absent from declaration_order"):
        theory.axiom(
            "ax-unexpected",
            schema=("φ:wff",),
            conclusion="φ → φ",
        )


def test_schema_order_is_preserved_on_handles() -> None:
    theory = _make_theory()
    ax = theory.axiom(
        "ax-order",
        schema=("ψ:wff", "φ:wff"),
        conclusion="ψ → (φ → ψ)",
    )
    assert [variable.local_key for variable in ax.schema_variables] == ["ψ", "φ"]
    reversed_occurrence = theory.definition(
        "df-order",
        schema=("φ:wff", "ψ:wff"),
        conclusion="ψ → φ",
    )
    assert [
        variable.local_key for variable in reversed_occurrence.schema_variables
    ] == [
        "φ",
        "ψ",
    ]


def test_explicit_assertion_id_is_used_by_all_declaration_kinds() -> None:
    theory = _make_theory()
    axiom_id = AssertionId("urn:uuid:00000000-0000-4000-8000-000000000001")
    definition_id = "urn:uuid:00000000-0000-4000-8000-000000000002"
    theorem_id = "urn:uuid:00000000-0000-4000-8000-000000000003"
    primitive_id = "urn:uuid:00000000-0000-4000-8000-000000000004"

    axiom = theory.axiom(
        "ax-stable",
        assertion_id=axiom_id,
        schema=("φ:wff",),
        conclusion="φ → φ",
    )
    definition = theory.definition(
        "df-stable",
        assertion_id=definition_id,
        schema=("φ:wff",),
        conclusion="φ → φ",
    )
    theorem = theory.theorem(
        "th-stable",
        assertion_id=theorem_id,
        schema=("φ:wff",),
        premises=("φ",),
        conclusion="φ",
    )
    primitive = theory.primitive_rule("mp", assertion_id=primitive_id)

    @theorem.proof
    def prove_th_stable(proof: TheoryProofAuthor) -> CompleteProof:
        return proof.qed(proof.hypotheses[0])

    assert tuple(handle.id for handle in (axiom, definition, theorem, primitive)) == (
        axiom_id,
        AssertionId(definition_id),
        AssertionId(theorem_id),
        AssertionId(primitive_id),
    )
    for handle in (axiom, definition, theorem, primitive):
        expected_owner = OwnerId(str(handle.id))
        assert all(
            variable.owner == expected_owner for variable in handle.schema_variables
        )
    assert theorem.implementation.root == StepId(f"{_NAMESPACE}#proof:th-stable/step:0")


def test_default_primitive_rule_signature_remains_compatible() -> None:
    theory = _make_theory()
    rule = theory.calculus.rule(_MP_RULE)
    expected = signature_from_primitive_rule(
        rule,
        assertion_id=AssertionId(f"{_NAMESPACE}#assertion:mp"),
        canonical_label="mp",
    )

    handle = theory.primitive_rule("mp")

    assert handle.signature == expected
    assert canonical_digest(
        cast(
            Mapping[str, JsonValue],
            assertion_signature_document(handle.signature),
        )
    ) == canonical_digest(
        cast(Mapping[str, JsonValue], assertion_signature_document(expected))
    )
    assert all(
        variable.owner == OwnerId(str(_MP_RULE)) for variable in handle.schema_variables
    )


def test_explicit_primitive_rule_rebinds_complete_schema_and_applies() -> None:
    theory = _make_theory()
    ax_1 = theory.axiom(
        "ax-1",
        schema=("φ:wff", "ψ:wff"),
        conclusion="φ → (ψ → φ)",
    )
    assertion_id = AssertionId("urn:uuid:00000000-0000-4000-8000-000000000005")
    mp = theory.primitive_rule("mp", assertion_id=assertion_id)
    owner = OwnerId(str(assertion_id))
    referenced = set(mp.schema_variables)
    for judgment in (*mp.premises, mp.conclusion):
        for argument in judgment.arguments:
            referenced.update(variables(argument))
    for pair in mp.signature.mandatory_distinct:
        referenced.update((pair.left, pair.right))

    assert referenced == set(mp.schema_variables)
    assert all(variable.owner == owner for variable in referenced)

    a1i, _ = _declare_a1i(theory, ax_1, mp)
    assert a1i.implementation.signature is a1i.signature


def test_explicit_primitive_rule_rebinds_distinct_endpoints() -> None:
    theory = _make_theory(mp_distinct=True)
    assertion_id = AssertionId("urn:uuid:00000000-0000-4000-8000-000000000011")

    mp = theory.primitive_rule("mp", assertion_id=assertion_id)

    (pair,) = mp.signature.mandatory_distinct
    assert pair.left in mp.schema_variables
    assert pair.right in mp.schema_variables
    assert pair.left.owner == OwnerId(str(assertion_id))
    assert pair.right.owner == OwnerId(str(assertion_id))


@pytest.mark.parametrize("assertion_id", ("", "not a canonical id"))
def test_invalid_explicit_assertion_id_fails_closed(assertion_id: str) -> None:
    theory = _make_theory()
    with pytest.raises(TheoryError, match="invalid assertion identifier"):
        theory.axiom(
            "ax-invalid-id",
            assertion_id=assertion_id,
            schema=("φ:wff",),
            conclusion="φ → φ",
        )


def test_non_string_explicit_assertion_id_fails_closed() -> None:
    theory = _make_theory()
    with pytest.raises(TheoryError, match="must be an AssertionId or string"):
        theory.axiom(
            "ax-invalid-type",
            assertion_id=cast(str, object()),
            schema=("φ:wff",),
            conclusion="φ → φ",
        )


def test_explicit_assertion_id_does_not_bypass_label_validation() -> None:
    theory = _make_theory()
    with pytest.raises(TheoryError, match="invalid assertion label"):
        theory.axiom(
            "not a canonical label",
            assertion_id="urn:uuid:00000000-0000-4000-8000-000000000006",
            schema=("φ:wff",),
            conclusion="φ → φ",
        )


def test_duplicate_explicit_assertion_id_fails_closed() -> None:
    theory = _make_theory()
    assertion_id = "urn:uuid:00000000-0000-4000-8000-000000000007"
    theory.axiom(
        "ax-first",
        assertion_id=assertion_id,
        schema=("φ:wff",),
        conclusion="φ → φ",
    )

    with pytest.raises(TheoryError, match="duplicate assertion identifier"):
        theory.theorem(
            "th-second",
            assertion_id=assertion_id,
            schema=("φ:wff",),
            premises=("φ",),
            conclusion="φ",
        )


def test_duplicate_label_fails_closed() -> None:
    theory = _make_theory()
    theory.axiom("ax-1", schema=("φ:wff", "ψ:wff"), conclusion="φ → (ψ → φ)")
    with pytest.raises(TheoryError, match="duplicate assertion label"):
        theory.axiom(
            "ax-1",
            assertion_id="urn:uuid:00000000-0000-4000-8000-000000000008",
            schema=("φ:wff",),
            conclusion="φ → φ",
        )


def test_undeclared_variable_fails_closed() -> None:
    theory = _make_theory()
    with pytest.raises(TheoryError, match="ax-bad"):
        theory.axiom("ax-bad", schema=("φ:wff",), conclusion="φ → χ")


def test_unknown_schema_kind_and_shape_fail_closed() -> None:
    theory = _make_theory()
    with pytest.raises(TheoryError, match="unknown schema variable kind"):
        theory.axiom("ax-kind", schema=("x:setvar",), conclusion="x → x")
    with pytest.raises(TheoryError, match="schema entries"):
        theory.axiom("ax-shape", schema=("φ",), conclusion="φ → φ")
    with pytest.raises(TheoryError, match="duplicate schema variable"):
        theory.axiom("ax-dup", schema=("φ:wff", "φ:wff"), conclusion="φ → φ")


def test_distinct_endpoint_must_be_declared() -> None:
    theory = _make_theory()
    with pytest.raises(TheoryError, match="distinct endpoint"):
        theory.axiom(
            "ax-dv",
            schema=("φ:wff",),
            conclusion="φ → φ",
            distinct=(("φ", "ψ"),),
        )


def test_subst_with_unknown_variable_fails_closed() -> None:
    theory = _make_theory()
    ax_1 = theory.axiom("ax-1", schema=("φ:wff", "ψ:wff"), conclusion="φ → (ψ → φ)")
    bad = theory.theorem(
        "bad-subst", schema=("φ:wff",), premises=(), conclusion="φ → (φ → φ)"
    )

    @bad.proof
    def prove_bad(proof: TheoryProofAuthor) -> CompleteProof:
        s1 = proof.use(ax_1, subst={"χ": "φ"})
        return proof.qed(s1)

    with pytest.raises(TheoryError, match="unknown substitution variable"):
        bad.implementation  # noqa: B018


def test_deprecated_assertion_warns_on_use() -> None:
    theory = _make_theory()
    ax_1 = theory.axiom(
        "ax-1",
        schema=("φ:wff", "ψ:wff"),
        conclusion="φ → (ψ → φ)",
        deprecated="use something newer",
    )
    mp = theory.primitive_rule("mp")
    a1i, _ = _declare_a1i(theory, ax_1, mp)
    with pytest.warns(DeprecationWarning, match="ax-1 is deprecated"):
        a1i.implementation  # noqa: B018


def test_internal_and_doc_metadata_are_carried() -> None:
    theory = _make_theory()
    ax = theory.axiom(
        "ax-int",
        schema=("φ:wff",),
        conclusion="φ → φ",
        doc="Internal helper.",
        internal=True,
    )
    assert ax.internal
    assert ax.doc == "Internal helper."
    assert theory.assertions["ax-int"] is ax


def test_proof_registration_rules() -> None:
    theory = _make_theory()
    ax = theory.axiom("ax-1", schema=("φ:wff", "ψ:wff"), conclusion="φ → (ψ → φ)")
    with pytest.raises(TheoryError, match="only theorems"):

        @ax.proof
        def prove_ax(proof: TheoryProofAuthor) -> CompleteProof:
            raise AssertionError("unreachable")

    theorem = theory.theorem("t", schema=("φ:wff",), premises=("φ",), conclusion="φ")

    @theorem.proof
    def prove_t(proof: TheoryProofAuthor) -> CompleteProof:
        return proof.qed(proof.hypotheses[0])

    with pytest.raises(TheoryError, match="already registered"):

        @theorem.proof
        def prove_t_again(proof: TheoryProofAuthor) -> CompleteProof:
            raise AssertionError("unreachable")

    assert theorem.implementation.signature is theorem.signature


def test_missing_proof_body_reported_by_verify_all() -> None:
    theory = _make_theory()
    theory.theorem("unproved", schema=("φ:wff",), premises=("φ",), conclusion="φ")
    report = theory.verify_all()
    assert not report.ok
    assert report.failures[0].label == "unproved"
    with pytest.raises(TheoryError, match="verification failed"):
        report.raise_if_failed()


def test_foreign_assertion_and_step_fail_closed() -> None:
    theory = _make_theory()
    other = _make_theory()
    foreign_ax = other.axiom("ax-foreign", schema=("φ:wff",), conclusion="φ → φ")
    theorem = theory.theorem("t", schema=("φ:wff",), premises=("φ",), conclusion="φ")

    @theorem.proof
    def prove_t(proof: TheoryProofAuthor) -> CompleteProof:
        proof.use(foreign_ax)
        return proof.qed(proof.hypotheses[0])

    with pytest.raises(TheoryError, match="not registered in this theory"):
        theorem.implementation  # noqa: B018

    donor = theory.theorem("donor", schema=("φ:wff",), premises=("φ",), conclusion="φ")

    @donor.proof
    def prove_donor(proof: TheoryProofAuthor) -> CompleteProof:
        return proof.qed(proof.hypotheses[0])

    stolen = donor.implementation.hypotheses[0]
    recipient = theory.theorem(
        "recipient", schema=("φ:wff",), premises=("φ",), conclusion="φ"
    )

    @recipient.proof
    def prove_recipient(proof: TheoryProofAuthor) -> CompleteProof:
        return proof.qed(stolen)

    with pytest.raises(TheoryError, match="created by this proof author"):
        recipient.implementation  # noqa: B018


def test_extend_pins_upstream_digests() -> None:
    upstream = _make_theory()
    good_pin = {
        _NAMESPACE: UpstreamPin(
            language=upstream.language.semantic_digest,
            calculus=upstream.calculus.digest,
        )
    }
    downstream = Theory.extend(
        upstream,
        theory_id="test-down#theory:main",
        namespace="test-down",
        language=upstream.language,
        calculus=upstream.calculus,
        notation=upstream.notation,
        provable_judgment=_PROVABLE,
        variable_kinds={"wff": _WFF_KIND},
        expected_upstream=good_pin,
    )
    assert downstream.upstreams == (upstream,)

    bad_pin = {_NAMESPACE: UpstreamPin(calculus=Digest("0" * 64))}
    with pytest.raises(TheoryError, match="calculus digest mismatch"):
        Theory.extend(
            upstream,
            theory_id="test-down#theory:main",
            namespace="test-down",
            language=upstream.language,
            calculus=upstream.calculus,
            provable_judgment=_PROVABLE,
            variable_kinds={"wff": _WFF_KIND},
            expected_upstream=bad_pin,
        )
    with pytest.raises(TheoryError, match="missing upstream pin"):
        Theory.extend(
            upstream,
            theory_id="test-down#theory:main",
            namespace="test-down",
            language=upstream.language,
            calculus=upstream.calculus,
            provable_judgment=_PROVABLE,
            variable_kinds={"wff": _WFF_KIND},
            expected_upstream={},
        )


def test_explicit_assertion_id_conflicting_with_upstream_fails_closed() -> None:
    upstream = _make_theory()
    assertion_id = "urn:uuid:00000000-0000-4000-8000-000000000009"
    upstream.axiom(
        "ax-upstream",
        assertion_id=assertion_id,
        schema=("φ:wff",),
        conclusion="φ → φ",
    )
    downstream = Theory.extend(
        upstream,
        theory_id="test-down#theory:main",
        namespace="test-down",
        language=upstream.language,
        calculus=upstream.calculus,
        notation=upstream.notation,
        provable_judgment=_PROVABLE,
        variable_kinds={"wff": _WFF_KIND},
    )

    with pytest.raises(
        TheoryError, match="assertion identifier conflicts with upstream theory"
    ):
        downstream.theorem(
            "th-downstream",
            assertion_id=assertion_id,
            schema=("φ:wff",),
            premises=("φ",),
            conclusion="φ",
        )


def test_cross_theory_proof_uses_upstream_handles() -> None:
    upstream = _make_theory()
    ax_1 = upstream.axiom("ax-1", schema=("φ:wff", "ψ:wff"), conclusion="φ → (ψ → φ)")
    mp = upstream.primitive_rule("mp")
    downstream = Theory.extend(
        upstream,
        theory_id="test-down#theory:main",
        namespace="test-down",
        language=upstream.language,
        calculus=upstream.calculus,
        notation=upstream.notation,
        provable_judgment=_PROVABLE,
        variable_kinds={"wff": _WFF_KIND},
    )
    a1i, _ = _declare_a1i(downstream, ax_1, mp)
    assert a1i.implementation.signature is a1i.signature  # type: ignore[attr-defined]

    with pytest.raises(TheoryError, match="conflicts with upstream"):
        downstream.axiom(
            "ax-1",
            assertion_id="urn:uuid:00000000-0000-4000-8000-000000000010",
            schema=("φ:wff",),
            conclusion="φ → φ",
        )


def test_dummy_variables_and_proof_distinct_resolve_in_scope() -> None:
    theory = _make_theory()
    ax_1 = theory.axiom("ax-1", schema=("φ:wff", "ψ:wff"), conclusion="φ → (ψ → φ)")
    # Declaration with an undeclared variable fails closed:
    with pytest.raises(TheoryError, match="with-dummy"):
        theory.theorem("with-dummy", schema=("φ:wff",), premises=(), conclusion="χ → φ")
    # Substitution values are parsed in the proof-body scope:
    theorem3 = theory.theorem(
        "subst-dummy",
        schema=("φ:wff",),
        premises=(),
        conclusion="φ → (¬ φ → φ)",
    )

    @theorem3.proof(dummy_variables=())
    def prove_theorem3(proof: TheoryProofAuthor) -> CompleteProof:
        s1 = proof.use(ax_1, subst={"φ": "φ", "ψ": "¬ φ"})
        return proof.qed(s1)

    assert theorem3.implementation.signature is theorem3.signature


def test_term_and_judgment_inputs_are_accepted() -> None:
    theory = _make_theory()
    owner = OwnerId(f"{_NAMESPACE}#assertion:ax-term")
    phi_ref = VariableRef("schema", owner, "φ", _WFF_KIND)
    phi = theory.language.variable(phi_ref)
    term = theory.language.apply(_IMP, (phi, phi))
    ax_term = theory.axiom("ax-term", schema=("φ:wff",), conclusion=term)
    assert ax_term.conclusion.arguments[0] == term
    judgment = Judgment(_PROVABLE, (term,))
    with pytest.raises(TheoryError, match="duplicate assertion label"):
        theory.axiom("ax-term", schema=("φ:wff",), conclusion=judgment)


def _emission_fixture() -> tuple[Theory, MetamathEmissionBinding]:
    theory = _make_theory()
    ax_1 = theory.axiom(
        "ax-1",
        schema=("φ:wff", "ψ:wff"),
        conclusion="φ → (ψ → φ)",
    )
    mp = theory.primitive_rule("mp")
    _declare_a1i(theory, ax_1, mp)
    hypothesis_root = theory.theorem(
        "hypothesis-root",
        schema=("φ:wff", "ψ:wff"),
        premises=("φ", "ψ"),
        conclusion="φ",
    )

    @hypothesis_root.proof
    def prove_hypothesis_root(proof: TheoryProofAuthor) -> CompleteProof:
        return proof.qed(proof.hypotheses[0])

    vocabulary = BackendVocabularyId("test-theory#vocabulary:mm")
    left = TokenRef(vocabulary, "(")
    implication = TokenRef(vocabulary, "->")
    right = TokenRef(vocabulary, ")")
    language = resolve_metamath_language(
        MetamathLanguageBinding(
            id=BackendBindingId("test-theory#binding:mm"),
            language=LanguageRequirement(
                id=theory.language.id,
                semantic_digest=theory.language.semantic_digest,
            ),
            foundation=FoundationRequirement(
                id=FoundationId("test-theory#foundation:mm")
            ),
            formations=(
                FormationBinding(
                    constructor=_IMP,
                    syntax_assertion=AssertionId("test-theory#formation:wi"),
                    syntax_assertion_label="wi",
                    template=(
                        LiteralPart(left),
                        ArgumentPart(0),
                        LiteralPart(implication),
                        ArgumentPart(1),
                        LiteralPart(right),
                    ),
                ),
            ),
        ),
        theory.language,
        {},
    )
    return theory, MetamathEmissionBinding(
        language=language,
        provable_judgment=_PROVABLE,
        provable_typecode="|-",
        token_names={left: "(", implication: "->", right: ")"},
        variable_names={"φ": "ph", "ψ": "ps"},
        sort_typecodes={_WFF: "wff"},
        formations=(
            MetamathFormationEmission(
                "wi",
                "wff",
                ("(", "ph", "->", "ps", ")"),
                (
                    MetamathFloatingEmission(_WFF, "ph"),
                    MetamathFloatingEmission(_WFF, "ps"),
                ),
            ),
        ),
        primitive_rule_floating={
            "mp": (
                MetamathFloatingEmission(_WFF, "ps"),
                MetamathFloatingEmission(_WFF, "ph"),
            )
        },
        sequence=(
            MetamathEmissionEntry("formation", "wi"),
            MetamathEmissionEntry("assertion", "ax-1"),
            MetamathEmissionEntry("assertion", "mp"),
            MetamathEmissionEntry("assertion", "a1i"),
            MetamathEmissionEntry("assertion", "hypothesis-root"),
        ),
    )


def _emit_text(theory: Theory, binding: MetamathEmissionBinding) -> str:
    interner = SymbolInterner()
    origins = OriginTable()
    mm = MMBuilderV2(
        interner=interner,
        origin_table=origins,
        names=NameResolver(),
        unit_id="semantic-emission",
        origin_module_id="semantic-emission",
        cfg=BuildConfig(auto_f=True, warn_raw=False, forbid_raw=True),
    )
    emit_semantic_metamath_theory(
        theory,
        binding,
        MetamathEmissionContext(mm=mm),
    )
    return LinkerV1.link(
        units=[mm.finish()],
        origin_table=origins,
        interner=interner,
    ).mm_text


def test_semantic_metamath_emission_is_deterministic_and_uses_semantic_proofs() -> None:
    theory, binding = _emission_fixture()
    first = _emit_text(theory, binding)
    second = _emit_text(theory, binding)
    assert first == second
    database = mmverify.MM()
    database.read(mmverify.toks(io.StringIO(first)))
    assert "mmtranspiler.h0 $f wff ph $." in first
    assert "wi $a wff ( ph -> ps ) $." in first
    assert "ax-1 $a |- ( ph -> ( ps -> ph ) ) $." in first
    mp_scope = first.split("mp $a", maxsplit=1)[0].rsplit("${", maxsplit=1)[1]
    assert mp_scope.index(" wff ps $.") < mp_scope.index(" wff ph $.")
    assert "a1i $p |- ( ps -> ph ) $=" in first
    hypothesis_root = first.split("hypothesis-root $p", maxsplit=1)[1]
    assert "mmtranspiler.h" in hypothesis_root
    assert "wi" not in hypothesis_root.split("$.", maxsplit=1)[0]


def test_semantic_metamath_emission_rejects_missing_mapping() -> None:
    theory, binding = _emission_fixture()
    broken = MetamathEmissionBinding(
        language=binding.language,
        provable_judgment=binding.provable_judgment,
        provable_typecode=binding.provable_typecode,
        token_names={
            token: name for token, name in binding.token_names.items() if name != "->"
        },
        variable_names=binding.variable_names,
        sort_typecodes=binding.sort_typecodes,
        formations=binding.formations,
        primitive_rule_floating=binding.primitive_rule_floating,
        sequence=binding.sequence,
    )
    with pytest.raises(MetamathEmissionError, match="no emission symbol for token"):
        _emit_text(theory, broken)


def test_semantic_metamath_emission_rejects_assertion_order_mismatch() -> None:
    theory, binding = _emission_fixture()
    broken = MetamathEmissionBinding(
        language=binding.language,
        provable_judgment=binding.provable_judgment,
        provable_typecode=binding.provable_typecode,
        token_names=binding.token_names,
        variable_names=binding.variable_names,
        sort_typecodes=binding.sort_typecodes,
        formations=binding.formations,
        primitive_rule_floating=binding.primitive_rule_floating,
        sequence=(
            binding.sequence[0],
            binding.sequence[2],
            binding.sequence[1],
            *binding.sequence[3:],
        ),
    )
    with pytest.raises(MetamathEmissionError, match="registration order"):
        _emit_text(theory, broken)


def test_semantic_metamath_emission_rejects_missing_primitive_floating() -> None:
    theory, binding = _emission_fixture()
    with pytest.raises(MetamathEmissionError, match="sequence is missing"):
        _emit_text(theory, replace(binding, primitive_rule_floating={}))


def test_semantic_metamath_emission_rejects_mismatched_primitive_floating() -> None:
    theory, binding = _emission_fixture()
    broken = replace(
        binding,
        primitive_rule_floating={"mp": (MetamathFloatingEmission(_WFF, "ph"),)},
    )
    with pytest.raises(MetamathEmissionError, match="do not match calculus rule"):
        _emit_text(theory, broken)


def test_semantic_metamath_emission_reuses_upstream_symbols_and_formations() -> None:
    upstream, binding = _emission_fixture()
    downstream = Theory.extend(
        upstream,
        theory_id="test-down#theory:main",
        namespace="test-down",
        language=upstream.language,
        calculus=upstream.calculus,
        notation=upstream.notation,
        provable_judgment=_PROVABLE,
        variable_kinds={"wff": _WFF_KIND},
    )
    copied = downstream.theorem(
        "copied-a1i",
        schema=("φ:wff", "ψ:wff"),
        premises=("φ",),
        conclusion="ψ → φ",
    )

    @copied.proof
    def prove_copied_a1i(proof: TheoryProofAuthor) -> CompleteProof:
        (h1,) = proof.hypotheses
        step = proof.use(
            upstream.assertions["a1i"],
            h1,
            target="ψ → φ",
        )
        return proof.qed(step)

    downstream_binding = replace(
        binding,
        sequence=(MetamathEmissionEntry("assertion", "copied-a1i"),),
    )
    interner = SymbolInterner()
    origins = OriginTable()
    upstream_mm = MMBuilderV2(
        interner=interner,
        origin_table=origins,
        names=NameResolver(),
        unit_id="upstream",
        origin_module_id="upstream",
    )
    emit_semantic_metamath_theory(
        upstream,
        binding,
        MetamathEmissionContext(mm=upstream_mm),
    )
    upstream_unit = upstream_mm.finish()
    symbol_table = interner.symbol_table()
    external_assertions = {
        symbol_table[symbol].local_name: symbol for symbol in upstream_unit.exports
    }
    external_constants = {
        definition.local_name: symbol
        for symbol, definition in symbol_table.items()
        if definition.kind == "Const"
    }
    external_variables = {
        definition.local_name: symbol
        for symbol, definition in symbol_table.items()
        if definition.kind == "Var"
    }
    downstream_mm = MMBuilderV2(
        interner=interner,
        origin_table=origins,
        names=NameResolver(),
        unit_id="downstream",
        origin_module_id="downstream",
    )
    emit_semantic_metamath_theory(
        downstream,
        downstream_binding,
        MetamathEmissionContext(
            mm=downstream_mm,
            external_assertions=external_assertions,
            external_constants=external_constants,
            external_variables=external_variables,
        ),
    )
    result = LinkerV1.link(
        units=[upstream_unit, downstream_mm.finish()],
        origin_table=origins,
        interner=interner,
        conformance_level=1,
    )
    database = mmverify.MM()
    database.read(mmverify.toks(io.StringIO(result.mm_text)))
    assert "copied-a1i $p |- ( ps -> ph ) $=" in result.mm_text
