from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError, replace
from typing import cast

import pytest

from skfd.authoring.errors import AuthoringSemanticError
from skfd.authoring.formula import Formula
from skfd.authoring.ids import (
    BackendBindingId,
    BackendVocabularyId,
    AssertionSemanticId,
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
from skfd.authoring.legacy_metamath import (
    build_legacy_formula,
    legacy_binary_formation,
    legacy_symbol_spec,
)
from skfd.authoring.language import (
    BinderDecl,
    ConstructorDecl,
    LanguageInterface,
    LanguageRequirement,
    LanguageSpec,
    SortDecl,
    VariableKindDecl,
    resolve_language,
)
from skfd.authoring.metamath_language import (
    ArgumentPart,
    FormationBinding,
    FoundationRequirement,
    LiteralAtom,
    LiteralPart,
    MetamathLanguageBinding,
    MetamathLanguageRequirement,
    ResolvedMetamathLanguageBinding,
    SortTypecodeBinding,
    TokenRef,
    VariableAtom,
    resolve_metamath_language,
)
from skfd.authoring.notation import (
    BinderForm,
    CallForm,
    InfixForm,
    NotationDecl,
    NotationInterface,
    NotationRequirement,
    NotationSpec,
    PrefixForm,
    resolve_notation,
)
from skfd.authoring.term import App, Var, VariableRef
from skfd.authoring.term_ops import alpha_rename, free_variables, substitute


def test_end_to_end_semantic_core() -> None:
    wff = SortId("wff")
    kind = VariableKindId("formula")
    neg, imp, and3 = ConstructorId("not"), ConstructorId("imp"), ConstructorId("and3")
    language = resolve_language(
        LanguageSpec(
            id=LanguageId("logic"),
            sorts=(SortDecl(id=wff),),
            variable_kinds=(VariableKindDecl(id=kind, sort=wff),),
            constructors=(
                ConstructorDecl(id=neg, inputs=(wff,), output=wff),
                ConstructorDecl(id=imp, inputs=(wff, wff), output=wff),
                ConstructorDecl(id=and3, inputs=(wff, wff, wff), output=wff),
            ),
        ),
        {},
    )
    reordered = resolve_language(
        LanguageSpec(
            id=LanguageId("other"),
            sorts=(SortDecl(id=wff),),
            variable_kinds=(VariableKindDecl(id=kind, sort=wff),),
            constructors=tuple(reversed(tuple(language.constructors.values()))),
        ),
        {},
    )
    assert reordered.semantic_digest == language.semantic_digest
    refs = {
        name: VariableRef("schema", OwnerId("test"), name, kind)
        for name in ("p", "q", "r")
    }
    variables = {name: language.variable(ref) for name, ref in refs.items()}
    term = language.apply(imp, (language.apply(neg, (variables["p"],)), variables["q"]))
    assert term == term and hash(term) == hash(term)
    assert term != language.apply(imp, (variables["p"], variables["q"]))
    with pytest.raises(AuthoringSemanticError):
        language.apply(neg, ())

    notation = resolve_notation(
        NotationSpec(
            id=NotationId("ascii"),
            language=LanguageRequirement(id=language.id, semantic_digest=language.semantic_digest),
            declarations=(
                NotationDecl(constructor=neg, form=PrefixForm(token="~", precedence=20), aliases=("¬",)),
                NotationDecl(constructor=imp, form=InfixForm(token="->", precedence=10, associativity="right"), aliases=("→",)),
                NotationDecl(constructor=and3, form=CallForm(token="and3")),
            ),
        ),
        language,
        {},
    )
    rendered = notation.render(term, {ref: name for name, ref in refs.items()})
    assert notation.parse(rendered, refs) == term
    assert notation.parse("¬ p → q", refs) == term
    triple = language.apply(and3, tuple(variables.values()))
    assert notation.parse(notation.render(triple, {ref: name for name, ref in refs.items()}), refs) == triple
    assert language.semantic_digest == reordered.semantic_digest
    with pytest.raises(AuthoringSemanticError):
        notation.parse("unknown", refs)

    token = TokenRef(BackendVocabularyId("mm"), "wi")
    backend = resolve_metamath_language(
        MetamathLanguageBinding(
            id=BackendBindingId("mm"),
            language=LanguageRequirement(id=language.id),
            foundation=FoundationRequirement(id=FoundationId("foundation")),
            formations=(
                FormationBinding(
                    constructor=imp,
                    syntax_assertion=AssertionSemanticId("wi"),
                    syntax_assertion_label="wi",
                    template=(LiteralPart(token), ArgumentPart(0), ArgumentPart(1)),
                ),
            ),
        ),
        language,
        {},
    )
    assert backend.lower(language.apply(imp, (variables["p"], variables["q"]))) == (
        LiteralAtom(token),
        VariableAtom(refs["p"]),
        VariableAtom(refs["q"]),
    )
    calculus = resolve_calculus(
        CalculusSpec(
            id=CalculusId("prop"),
            language=LanguageRequirement(id=language.id),
            judgments=(JudgmentKindDecl(id=JudgmentKindId("provable"), arguments=(wff,)),),
        ),
        language,
    )
    assert calculus.judgment(JudgmentKindId("provable"), (term,)).arguments == (term,)


def _minimal_language(*, language_id: str = "test#language:base") -> LanguageInterface:
    wff = SortId("test#sort:wff")
    formula = VariableKindId("test#variable-kind:formula")
    return resolve_language(
        LanguageSpec(
            id=LanguageId(language_id),
            sorts=(SortDecl(id=wff),),
            variable_kinds=(VariableKindDecl(id=formula, sort=wff),),
            constructors=(
                ConstructorDecl(
                    id=ConstructorId("test#constructor:not"),
                    inputs=(wff,),
                    output=wff,
                ),
                ConstructorDecl(
                    id=ConstructorId("test#constructor:imp"),
                    inputs=(wff, wff),
                    output=wff,
                ),
            ),
        ),
        {},
    )


def _variables(language: LanguageInterface) -> tuple[dict[str, VariableRef], dict[str, Var]]:
    kind = VariableKindId("test#variable-kind:formula")
    refs = {
        name: VariableRef("schema", OwnerId("test#assertion:variables"), name, kind)
        for name in ("p", "q", "r")
    }
    return refs, {name: language.variable(ref) for name, ref in refs.items()}


def test_ids_are_nominal_and_validate_canonical_values() -> None:
    assert len({SortId("same#id"), ConstructorId("same#id")}) == 2
    assert str(LanguageId("package/path#language:name")) == "package/path#language:name"
    with pytest.raises(ValueError):
        SortId("contains space")
    with pytest.raises(ValueError):
        Digest("not-a-digest")
    with pytest.raises(ValueError):
        VariableRef("schema", OwnerId("owner"), "", VariableKindId("kind"))


def test_term_identity_is_structural_and_hashable() -> None:
    language = _minimal_language()
    _, variables = _variables(language)
    imp = ConstructorId("test#constructor:imp")
    neg = ConstructorId("test#constructor:not")

    left = language.apply(imp, (variables["p"], variables["q"]))
    same = language.apply(imp, (variables["p"], variables["q"]))
    different_argument = language.apply(imp, (variables["p"], variables["r"]))
    different_constructor = language.apply(neg, (variables["p"],))

    assert left == same
    assert hash(left) == hash(same)
    assert left != different_argument
    assert left != different_constructor
    assert variables["p"] != variables["q"]
    assert App(imp, left.arguments, SortId("other#sort:wff")) != left


def test_checked_term_construction_rejects_unknown_arity_and_sort() -> None:
    language = _minimal_language()
    _, variables = _variables(language)
    neg = ConstructorId("test#constructor:not")

    with pytest.raises(AuthoringSemanticError, match="unknown constructor"):
        language.apply(ConstructorId("test#constructor:missing"), ())
    with pytest.raises(AuthoringSemanticError, match="expects 1 arguments"):
        language.apply(neg, ())
    with pytest.raises(AuthoringSemanticError, match="expects test#sort:wff"):
        language.apply(
            neg,
            (Var(variables["p"].variable, SortId("other#sort:term")),),
        )
    with pytest.raises(AuthoringSemanticError, match="unknown variable kind"):
        language.variable(
            VariableRef(
                "local",
                OwnerId("test#proof:one"),
                "x",
                VariableKindId("test#variable-kind:missing"),
            )
        )


def test_language_digest_is_order_independent_and_interfaces_are_immutable() -> None:
    first = _minimal_language(language_id="test#language:first")
    reordered = resolve_language(
        LanguageSpec(
            id=LanguageId("test#language:reordered"),
            sorts=tuple(reversed(tuple(first.sorts.values()))),
            variable_kinds=tuple(reversed(tuple(first.variable_kinds.values()))),
            constructors=tuple(reversed(tuple(first.constructors.values()))),
        ),
        {},
    )
    assert first.semantic_digest == reordered.semantic_digest
    assert first.sorts is not reordered.sorts
    with pytest.raises(FrozenInstanceError):
        setattr(first, "id", LanguageId("test#language:changed"))
    with pytest.raises(TypeError):
        cast(MutableMapping[SortId, SortDecl], first.sorts)[SortId("test#sort:new")] = (
            SortDecl(id=SortId("test#sort:new"))
        )


def test_language_extensions_merge_identical_diamonds() -> None:
    base = _minimal_language()
    left = resolve_language(
        LanguageSpec(
            id=LanguageId("test#language:left"),
            extends=(LanguageRequirement(id=base.id, semantic_digest=base.semantic_digest),),
        ),
        {base.id: base},
    )
    right = resolve_language(
        LanguageSpec(
            id=LanguageId("test#language:right"),
            extends=(LanguageRequirement(id=base.id, semantic_digest=base.semantic_digest),),
        ),
        {base.id: base},
    )
    top = resolve_language(
        LanguageSpec(
            id=LanguageId("test#language:top"),
            extends=(LanguageRequirement(id=left.id), LanguageRequirement(id=right.id)),
        ),
        {left.id: left, right.id: right},
    )
    assert top.semantic_digest == base.semantic_digest
    assert top.constructors == base.constructors


def test_language_resolution_reports_missing_digest_conflict_and_unknown_sort() -> None:
    base = _minimal_language()
    with pytest.raises(AuthoringSemanticError, match="missing language dependency"):
        resolve_language(
            LanguageSpec(
                id=LanguageId("test#language:missing-parent"),
                extends=(LanguageRequirement(id=LanguageId("test#language:absent")),),
            ),
            {},
        )
    with pytest.raises(AuthoringSemanticError, match="digest mismatch"):
        resolve_language(
            LanguageSpec(
                id=LanguageId("test#language:wrong-digest"),
                extends=(
                    LanguageRequirement(id=base.id, semantic_digest=Digest("0" * 64)),
                ),
            ),
            {base.id: base},
        )
    with pytest.raises(AuthoringSemanticError, match="conflicting declaration"):
        resolve_language(
            LanguageSpec(
                id=LanguageId("test#language:conflict"),
                extends=(LanguageRequirement(id=base.id),),
                constructors=(
                    ConstructorDecl(
                        id=ConstructorId("test#constructor:not"),
                        inputs=(),
                        output=SortId("test#sort:wff"),
                    ),
                ),
            ),
            {base.id: base},
        )
    with pytest.raises(AuthoringSemanticError, match="unknown sort"):
        resolve_language(
            LanguageSpec(
                id=LanguageId("test#language:unknown-sort"),
                variable_kinds=(
                    VariableKindDecl(
                        id=VariableKindId("test#variable-kind:orphan"),
                        sort=SortId("test#sort:absent"),
                    ),
                ),
            ),
            {},
        )


def _notation(
    language: LanguageInterface,
    *,
    implication_token: str = "→",
) -> NotationInterface:
    return resolve_notation(
        NotationSpec(
            id=NotationId(f"test#notation:{'unicode' if implication_token == '→' else 'ascii'}"),
            language=LanguageRequirement(id=language.id, semantic_digest=language.semantic_digest),
            declarations=(
                NotationDecl(
                    constructor=ConstructorId("test#constructor:not"),
                    form=PrefixForm(token="¬", precedence=30),
                    aliases=("~",),
                ),
                NotationDecl(
                    constructor=ConstructorId("test#constructor:imp"),
                    form=InfixForm(
                        token=implication_token,
                        precedence=20,
                        associativity="right",
                    ),
                    aliases=("->",) if implication_token != "->" else ("⇒",),
                ),
            ),
        ),
        language,
        {},
    )


def test_notation_aliases_associativity_and_round_trip() -> None:
    language = _minimal_language()
    refs, variables = _variables(language)
    notation = _notation(language)
    imp = ConstructorId("test#constructor:imp")
    neg = ConstructorId("test#constructor:not")
    expected = language.apply(
        imp,
        (
            language.apply(neg, (variables["p"],)),
            language.apply(imp, (variables["q"], variables["r"])),
        ),
    )
    assert notation.parse("~ p -> q → r", refs) == expected
    rendered = notation.render(expected, {ref: name for name, ref in refs.items()})
    assert notation.parse(rendered, refs) == expected
    with pytest.raises(AuthoringSemanticError, match="unknown variable"):
        notation.parse("unknown", refs)
    with pytest.raises(AuthoringSemanticError, match="no display name"):
        notation.render(expected, {})


def test_notation_digest_is_separate_and_alias_collisions_fail() -> None:
    language = _minimal_language()
    unicode = _notation(language)
    ascii_notation = _notation(language, implication_token="=>")
    assert unicode.digest != ascii_notation.digest
    assert unicode.language.semantic_digest == ascii_notation.language.semantic_digest
    assert language.semantic_digest == unicode.language.semantic_digest

    reordered_aliases = resolve_notation(
        NotationSpec(
            id=NotationId("test#notation:reordered-aliases"),
            language=LanguageRequirement(id=language.id),
            declarations=tuple(
                NotationDecl(
                    constructor=item.constructor,
                    form=item.form,
                    aliases=tuple(reversed(item.aliases)),
                )
                for item in unicode.declarations
            ),
        ),
        language,
        {},
    )
    assert reordered_aliases.digest == unicode.digest
    assert reordered_aliases.declarations == unicode.declarations

    with pytest.raises(AuthoringSemanticError, match="alias collision"):
        resolve_notation(
            NotationSpec(
                id=NotationId("test#notation:collision"),
                language=LanguageRequirement(id=language.id),
                declarations=(
                    NotationDecl(
                        constructor=ConstructorId("test#constructor:not"),
                        form=PrefixForm(token="~", precedence=30),
                    ),
                    NotationDecl(
                        constructor=ConstructorId("test#constructor:imp"),
                        form=InfixForm(token="->", precedence=20, associativity="right"),
                        aliases=("~",),
                    ),
                ),
            ),
            language,
            {},
        )


def test_notation_extension_requires_matching_dependency() -> None:
    base = _minimal_language()
    base_notation = _notation(base)
    with pytest.raises(AuthoringSemanticError, match="notation digest mismatch"):
        resolve_notation(
            NotationSpec(
                id=NotationId("test#notation:child"),
                language=LanguageRequirement(id=base.id),
                extends=(
                    NotationRequirement(id=base_notation.id, digest=Digest("f" * 64)),
                ),
            ),
            base,
            {base_notation.id: base_notation},
        )


def _conjunction_language() -> tuple[LanguageInterface, ConstructorId, ConstructorId]:
    wff = SortId("test#sort:wff")
    formula = VariableKindId("test#variable-kind:formula")
    and2 = ConstructorId("test#constructor:and2")
    and3 = ConstructorId("test#constructor:and3")
    language = resolve_language(
        LanguageSpec(
            id=LanguageId("test#language:conjunction"),
            sorts=(SortDecl(id=wff),),
            variable_kinds=(VariableKindDecl(id=formula, sort=wff),),
            constructors=(
                ConstructorDecl(id=and2, inputs=(wff, wff), output=wff),
                ConstructorDecl(id=and3, inputs=(wff, wff, wff), output=wff),
            ),
        ),
        {},
    )
    return language, and2, and3


def test_same_backend_token_supports_distinct_binary_and_ternary_constructors() -> None:
    language, and2, and3 = _conjunction_language()
    kind = VariableKindId("test#variable-kind:formula")
    refs = {
        name: VariableRef("schema", OwnerId("test#assertion:and"), name, kind)
        for name in ("p", "q", "r")
    }
    variables = tuple(language.variable(ref) for ref in refs.values())
    vocabulary = BackendVocabularyId("test#vocabulary:setmm")
    slash_and = TokenRef(vocabulary, "/\\")
    lp = TokenRef(vocabulary, "(")
    rp = TokenRef(vocabulary, ")")
    binding = resolve_metamath_language(
        MetamathLanguageBinding(
            id=BackendBindingId("test#binding:setmm"),
            language=LanguageRequirement(id=language.id),
            foundation=FoundationRequirement(id=FoundationId("test#foundation:setmm")),
            sort_typecodes=(
                SortTypecodeBinding(
                    sort=SortId("test#sort:wff"),
                    typecode=TokenRef(vocabulary, "wff"),
                ),
            ),
            formations=(
                FormationBinding(
                    constructor=and2,
                    syntax_assertion=AssertionSemanticId("test#formation:wa"),
                    syntax_assertion_label="wa",
                    template=(
                        LiteralPart(lp),
                        ArgumentPart(0),
                        LiteralPart(slash_and),
                        ArgumentPart(1),
                        LiteralPart(rp),
                    ),
                ),
                FormationBinding(
                    constructor=and3,
                    syntax_assertion=AssertionSemanticId("test#formation:w3a"),
                    syntax_assertion_label="w3a",
                    template=(
                        LiteralPart(lp),
                        ArgumentPart(0),
                        LiteralPart(slash_and),
                        ArgumentPart(1),
                        LiteralPart(slash_and),
                        ArgumentPart(2),
                        LiteralPart(rp),
                    ),
                ),
            ),
        ),
        language,
        {},
    )
    binary = language.apply(and2, variables[:2])
    ternary = language.apply(and3, variables)
    assert binary != ternary
    assert binding.formations[and2].syntax_assertion != binding.formations[and3].syntax_assertion
    assert [
        atom.token.local_name if isinstance(atom, LiteralAtom) else atom.variable.local_key
        for atom in binding.lower(binary)
    ] == ["(", "p", "/\\", "q", ")"]
    assert [
        atom.token.local_name if isinstance(atom, LiteralAtom) else atom.variable.local_key
        for atom in binding.lower(ternary)
    ] == ["(", "p", "/\\", "q", "/\\", "r", ")"]
    assert all(isinstance(atom, (LiteralAtom, VariableAtom)) for atom in binding.lower(ternary))


def test_backend_digest_is_separate_and_template_coverage_is_checked() -> None:
    language, and2, _ = _conjunction_language()
    vocabulary = BackendVocabularyId("test#vocabulary:setmm")
    token = TokenRef(vocabulary, "/\\")

    def resolve(assertion: str) -> ResolvedMetamathLanguageBinding:
        return resolve_metamath_language(
            MetamathLanguageBinding(
                id=BackendBindingId(f"test#binding:{assertion}"),
                language=LanguageRequirement(id=language.id),
                foundation=FoundationRequirement(id=FoundationId("test#foundation:setmm")),
                formations=(
                    FormationBinding(
                        constructor=and2,
                        syntax_assertion=AssertionSemanticId(f"test#formation:{assertion}"),
                        syntax_assertion_label=assertion,
                        template=(ArgumentPart(0), LiteralPart(token), ArgumentPart(1)),
                    ),
                ),
            ),
            language,
            {},
        )

    first = resolve("wa")
    second = resolve("wa-alternative")
    assert first.digest != second.digest
    assert first.language.semantic_digest == second.language.semantic_digest
    with pytest.raises(AuthoringSemanticError, match="coverage mismatch"):
        resolve_metamath_language(
            MetamathLanguageBinding(
                id=BackendBindingId("test#binding:invalid"),
                language=LanguageRequirement(id=language.id),
                foundation=FoundationRequirement(id=FoundationId("test#foundation:setmm")),
                formations=(
                    FormationBinding(
                        constructor=and2,
                        syntax_assertion=AssertionSemanticId("test#formation:invalid"),
                        syntax_assertion_label="invalid",
                        template=(ArgumentPart(0), LiteralPart(token), ArgumentPart(0)),
                    ),
                ),
            ),
            language,
            {},
        )
    with pytest.raises(AuthoringSemanticError, match="missing Metamath binding dependency"):
        resolve_metamath_language(
            MetamathLanguageBinding(
                id=BackendBindingId("test#binding:missing-parent"),
                language=LanguageRequirement(id=language.id),
                foundation=FoundationRequirement(id=FoundationId("test#foundation:setmm")),
                extends=(
                    MetamathLanguageRequirement(id=BackendBindingId("test#binding:absent")),
                ),
            ),
            language,
            {},
        )


def test_legacy_formula_adapter_applies_the_resolved_formation() -> None:
    language, and2, _ = _conjunction_language()
    vocabulary = BackendVocabularyId("test#vocabulary:setmm")
    lp = TokenRef(vocabulary, "(")
    conjunction = TokenRef(vocabulary, "/\\")
    rp = TokenRef(vocabulary, ")")
    binding = resolve_metamath_language(
        MetamathLanguageBinding(
            id=BackendBindingId("test#binding:legacy"),
            language=LanguageRequirement(id=language.id),
            foundation=FoundationRequirement(id=FoundationId("test#foundation:setmm")),
            formations=(
                FormationBinding(
                    constructor=and2,
                    syntax_assertion=AssertionSemanticId("test#formation:wa"),
                    syntax_assertion_label="wa",
                    template=(
                        LiteralPart(lp),
                        ArgumentPart(0),
                        LiteralPart(conjunction),
                        ArgumentPart(1),
                        LiteralPart(rp),
                    ),
                ),
            ),
        ),
        language,
        {},
    )
    formula = build_legacy_formula(
        binding,
        and2,
        (Formula("wff", (10,)), Formula("wff", (11,))),
        token_symbols={lp: 1, conjunction: 2, rp: 3},
        legacy_sorts={SortId("test#sort:wff"): "wff"},
    )
    assert formula == Formula("wff", (1, 10, 2, 11, 3))

    notation = resolve_notation(
        NotationSpec(
            id=NotationId("test#notation:legacy"),
            language=LanguageRequirement(id=language.id),
            declarations=(
                NotationDecl(
                    constructor=and2,
                    form=InfixForm(token="∧", precedence=25, associativity="left"),
                    aliases=("/\\", "&"),
                ),
            ),
        ),
        language,
        {},
    )
    symbol_spec = legacy_symbol_spec(
        binding,
        notation,
        and2,
        legacy_sorts={SortId("test#sort:wff"): "wff"},
    )
    assert symbol_spec.name == "/\\"
    assert symbol_spec.arity == 2
    assert symbol_spec.in_sorts == ("wff", "wff")
    assert symbol_spec.out_sort == "wff"
    assert symbol_spec.aliases == ("∧", "&")
    binary_shape = legacy_binary_formation(binding, and2)
    assert binary_shape == (
        type(binary_shape)(left_delimiter=lp, operator=conjunction, right_delimiter=rp)
    )

    conflicting_language = resolve_language(
        LanguageSpec(
            id=LanguageId("test#language:conflicting-notation"),
            sorts=(SortDecl(id=SortId("test#sort:wff")),),
            constructors=(
                ConstructorDecl(
                    id=and2,
                    inputs=(SortId("test#sort:wff"),),
                    output=SortId("test#sort:wff"),
                ),
            ),
        ),
        {},
    )
    conflicting_notation = resolve_notation(
        NotationSpec(
            id=NotationId("test#notation:conflicting-language"),
            language=LanguageRequirement(id=conflicting_language.id),
            declarations=(
                NotationDecl(
                    constructor=and2,
                    form=PrefixForm(token="∧", precedence=25),
                    aliases=("/\\",),
                ),
            ),
        ),
        conflicting_language,
        {},
    )
    with pytest.raises(AuthoringSemanticError, match="notation language mismatch"):
        legacy_symbol_spec(
            binding,
            conflicting_notation,
            and2,
            legacy_sorts={SortId("test#sort:wff"): "wff"},
        )

    with pytest.raises(AuthoringSemanticError, match="expects 2 arguments"):
        build_legacy_formula(
            binding,
            and2,
            (),
            token_symbols={lp: 1, conjunction: 2, rp: 3},
            legacy_sorts={SortId("test#sort:wff"): "wff"},
        )
    with pytest.raises(AuthoringSemanticError, match="no legacy symbol binding"):
        build_legacy_formula(
            binding,
            and2,
            (Formula("wff", (10,)), Formula("wff", (11,))),
            token_symbols={},
            legacy_sorts={SortId("test#sort:wff"): "wff"},
        )


def test_minimal_calculus_makes_provability_an_explicit_judgment() -> None:
    language = _minimal_language()
    refs, variables = _variables(language)
    provable = JudgmentKindId("test#judgment:provable")
    mp = RuleId("test#rule:modus-ponens")
    implication = language.apply(
        ConstructorId("test#constructor:imp"),
        (variables["p"], variables["q"]),
    )
    modus_ponens = PrimitiveRuleDecl(
        id=mp,
        schema_variables=(refs["p"], refs["q"]),
        premises=(
            Judgment(provable, (variables["p"],)),
            Judgment(provable, (implication,)),
        ),
        conclusion=Judgment(provable, (variables["q"],)),
    )
    calculus = resolve_calculus(
        CalculusSpec(
            id=CalculusId("test#calculus:hilbert"),
            language=LanguageRequirement(id=language.id, semantic_digest=language.semantic_digest),
            judgments=(
                JudgmentKindDecl(
                    id=provable,
                    arguments=(SortId("test#sort:wff"),),
                ),
            ),
            rules=(modus_ponens,),
        ),
        language,
    )
    judgment = calculus.judgment(provable, (variables["p"],))
    assert judgment.kind == provable
    assert judgment.arguments == (variables["p"],)
    assert calculus.rule(mp) == modus_ponens
    assert calculus.rule(mp).premises[1].arguments == (implication,)
    reordered = resolve_calculus(
        CalculusSpec(
            id=CalculusId("test#calculus:reordered"),
            language=LanguageRequirement(id=language.id),
            judgments=(JudgmentKindDecl(id=provable, arguments=(SortId("test#sort:wff"),)),),
            rules=(replace(modus_ponens, schema_variables=(refs["q"], refs["p"])),),
        ),
        language,
    )
    assert reordered.digest == calculus.digest
    assert reordered.rule(mp).schema_variables == (refs["p"], refs["q"])

    axiom = resolve_axiom(
        AxiomDecl(
            id=AssertionSemanticId("test#axiom:distinct-canary"),
            schema_variables=(refs["q"], refs["p"]),
            conclusion=Judgment(provable, (implication,)),
            mandatory_distinct=(DistinctPair(refs["q"], refs["p"]),),
        ),
        calculus,
    )
    assert axiom.declaration.schema_variables == (refs["p"], refs["q"])
    assert axiom.declaration.mandatory_distinct == (DistinctPair(refs["p"], refs["q"]),)
    assert axiom.digest == resolve_axiom(
        replace(
            axiom.declaration,
            schema_variables=(refs["q"], refs["p"]),
            mandatory_distinct=(DistinctPair(refs["q"], refs["p"]),),
        ),
        calculus,
    ).digest
    with pytest.raises(AuthoringSemanticError, match="different endpoints"):
        DistinctPair(refs["p"], refs["p"])
    undeclared_ref = replace(refs["q"], local_key="r")
    with pytest.raises(AuthoringSemanticError, match="undeclared distinct-variable endpoint"):
        resolve_axiom(
            replace(
                axiom.declaration,
                mandatory_distinct=(DistinctPair(refs["p"], undeclared_ref),),
            ),
            calculus,
        )
    with pytest.raises(AuthoringSemanticError, match="unknown judgment"):
        calculus.judgment(JudgmentKindId("test#judgment:missing"), ())
    with pytest.raises(AuthoringSemanticError, match="unknown primitive rule"):
        calculus.rule(RuleId("test#rule:missing"))
    with pytest.raises(AuthoringSemanticError, match="argument mismatch"):
        calculus.judgment(provable, ())
    forged = App(
        ConstructorId("test#constructor:missing"),
        (),
        SortId("test#sort:wff"),
    )
    with pytest.raises(AuthoringSemanticError, match="unknown term constructor"):
        calculus.judgment(provable, (forged,))
    with pytest.raises(AuthoringSemanticError, match="calculus language requirement mismatch"):
        resolve_calculus(
            CalculusSpec(
                id=CalculusId("test#calculus:wrong-language"),
                language=LanguageRequirement(id=LanguageId("test#language:other")),
            ),
            language,
        )

    undeclared = PrimitiveRuleDecl(
        id=RuleId("test#rule:undeclared-variable"),
        schema_variables=(refs["p"],),
        premises=(),
        conclusion=Judgment(provable, (variables["q"],)),
    )
    with pytest.raises(AuthoringSemanticError, match="undeclared rule schema variable"):
        resolve_calculus(
            CalculusSpec(
                id=CalculusId("test#calculus:invalid-rule"),
                language=LanguageRequirement(id=language.id),
                judgments=(JudgmentKindDecl(id=provable, arguments=(SortId("test#sort:wff"),)),),
                rules=(undeclared,),
            ),
            language,
        )

    unknown_kind = VariableRef(
        "schema",
        OwnerId("test#rule:unknown-kind"),
        "unused",
        VariableKindId("test#variable-kind:missing"),
    )
    with pytest.raises(AuthoringSemanticError, match="unknown schema variable kind"):
        resolve_calculus(
            CalculusSpec(
                id=CalculusId("test#calculus:unknown-kind"),
                language=LanguageRequirement(id=language.id),
                judgments=(JudgmentKindDecl(id=provable, arguments=(SortId("test#sort:wff"),)),),
                rules=(replace(modus_ponens, schema_variables=(*modus_ponens.schema_variables, unknown_kind)),),
            ),
            language,
        )


def test_binder_semantics_support_free_variables_alpha_renaming_and_capture_avoidance() -> None:
    wff = SortId("test#sort:wff")
    setvar = SortId("test#sort:setvar")
    formula_kind = VariableKindId("test#variable-kind:formula")
    setvar_kind = VariableKindId("test#variable-kind:setvar")
    predicate = ConstructorId("test#constructor:predicate")
    name = ConstructorId("test#constructor:name")
    all_ = ConstructorId("test#constructor:all")
    contextual = ConstructorId("test#constructor:contextual-binder")
    imp = ConstructorId("test#constructor:binder-imp")
    neg = ConstructorId("test#constructor:binder-neg")
    language = resolve_language(
        LanguageSpec(
            id=LanguageId("test#language:binder"),
            sorts=(SortDecl(id=wff), SortDecl(id=setvar)),
            variable_kinds=(
                VariableKindDecl(id=formula_kind, sort=wff),
                VariableKindDecl(id=setvar_kind, sort=setvar),
            ),
            constructors=(
                ConstructorDecl(id=name, inputs=(), output=setvar),
                ConstructorDecl(id=predicate, inputs=(setvar,), output=wff),
                ConstructorDecl(id=all_, inputs=(setvar, wff), output=wff),
                ConstructorDecl(id=contextual, inputs=(setvar, wff, wff), output=wff),
                ConstructorDecl(id=imp, inputs=(wff, wff), output=wff),
                ConstructorDecl(id=neg, inputs=(wff,), output=wff),
            ),
            binders=(
                BinderDecl(
                    constructor=all_,
                    variable_argument=0,
                    scoped_arguments=(1,),
                ),
                BinderDecl(
                    constructor=contextual,
                    variable_argument=0,
                    scoped_arguments=(1,),
                ),
            ),
        ),
        {},
    )
    owner = OwnerId("test#binder:variables")
    x_ref = VariableRef("schema", owner, "x", setvar_kind)
    y_ref = VariableRef("schema", owner, "y", setvar_kind)
    z_ref = VariableRef("schema", owner, "z", setvar_kind)
    phi_ref = VariableRef("schema", owner, "phi", formula_kind)
    x, y = language.variable(x_ref), language.variable(y_ref)
    phi = language.variable(phi_ref)
    pred_x = language.apply(predicate, (x,))
    pred_y = language.apply(predicate, (y,))
    quantified_x = language.apply(all_, (x, pred_x))

    assert free_variables(quantified_x, language) == frozenset()
    assert substitute(quantified_x, {x_ref: y}, language) == quantified_x

    renamed = alpha_rename(quantified_x, z_ref, language)
    assert renamed.arguments[0] == language.variable(z_ref)
    assert renamed.arguments[1] == language.apply(predicate, (language.variable(z_ref),))

    shadowed = language.apply(all_, (x, language.apply(all_, (x, pred_x))))
    shadowed_renamed = alpha_rename(shadowed, z_ref, language)
    assert shadowed_renamed.arguments[1] == shadowed.arguments[1]

    mixed_scope = language.apply(
        all_,
        (x, language.apply(contextual, (x, pred_x, pred_x))),
    )
    mixed_renamed = alpha_rename(mixed_scope, z_ref, language)
    nested = mixed_renamed.arguments[1]
    assert isinstance(nested, App)
    assert nested.arguments[1] == pred_x
    assert nested.arguments[2] == language.apply(predicate, (language.variable(z_ref),))

    capture_risk = language.apply(all_, (x, pred_y))
    substituted = substitute(capture_risk, {y_ref: x}, language)
    fresh = VariableRef("schema", owner, "x_1", setvar_kind)
    assert substituted == language.apply(
        all_,
        (
            language.variable(fresh),
            pred_x,
        ),
    )
    assert free_variables(substituted, language) == frozenset((x_ref,))

    x_1_ref = VariableRef("schema", owner, "x_1", setvar_kind)
    z = language.variable(z_ref)
    substituted_with_domain_collision = substitute(
        capture_risk,
        {y_ref: x, x_1_ref: z},
        language,
    )
    x_2_ref = VariableRef("schema", owner, "x_2", setvar_kind)
    assert substituted_with_domain_collision == language.apply(
        all_,
        (language.variable(x_2_ref), pred_x),
    )

    provable = JudgmentKindId("test#judgment:binder-provable")
    forged_quantifier = App(
        all_,
        (App(name, (), setvar), phi),
        wff,
    )
    invalid_rule = PrimitiveRuleDecl(
        id=RuleId("test#rule:forged-binder"),
        schema_variables=(phi_ref,),
        premises=(),
        conclusion=Judgment(provable, (forged_quantifier,)),
    )
    with pytest.raises(AuthoringSemanticError, match="must be a variable"):
        resolve_calculus(
            CalculusSpec(
                id=CalculusId("test#calculus:forged-binder"),
                language=LanguageRequirement(id=language.id),
                judgments=(JudgmentKindDecl(id=provable, arguments=(wff,)),),
                rules=(invalid_rule,),
            ),
            language,
        )
    calculus = resolve_calculus(
        CalculusSpec(
            id=CalculusId("test#calculus:binder"),
            language=LanguageRequirement(id=language.id),
            judgments=(JudgmentKindDecl(id=provable, arguments=(wff,)),),
        ),
        language,
    )
    with pytest.raises(AuthoringSemanticError, match="must be a variable"):
        resolve_axiom(
            AxiomDecl(
                id=AssertionSemanticId("test#axiom:forged-binder"),
                schema_variables=(phi_ref,),
                conclusion=Judgment(provable, (forged_quantifier,)),
            ),
            calculus,
        )

    notation = resolve_notation(
        NotationSpec(
            id=NotationId("test#notation:binder"),
            language=LanguageRequirement(id=language.id),
            declarations=(
                NotationDecl(constructor=predicate, form=CallForm(token="P")),
                NotationDecl(
                    constructor=imp,
                    form=InfixForm(token="→", precedence=10, associativity="right"),
                ),
                NotationDecl(
                    constructor=neg,
                    form=PrefixForm(token="¬", precedence=20),
                ),
                NotationDecl(
                    constructor=all_,
                    form=BinderForm(token="∀", precedence=0),
                    aliases=("forall",),
                ),
            ),
        ),
        language,
        {},
    )
    variable_names = {x_ref: "x", y_ref: "y", z_ref: "z"}
    term = language.apply(all_, (x, pred_y))
    assert notation.parse(notation.render(term, variable_names), {"x": x_ref, "y": y_ref}) == term
    assert notation.parse("forall x P(y)", {"x": x_ref, "y": y_ref}) == term
    names = {"x": x_ref, "y": y_ref, "phi": phi_ref}
    displays = {x_ref: "x", y_ref: "y", phi_ref: "phi"}
    for compound in (
        language.apply(imp, (term, phi)),
        language.apply(imp, (phi, term)),
        language.apply(neg, (term,)),
    ):
        assert notation.parse(notation.render(compound, displays), names) == compound

    unbound_base = resolve_language(
        LanguageSpec(
            id=LanguageId("test#language:unbound-base"),
            sorts=(SortDecl(id=wff), SortDecl(id=setvar)),
            variable_kinds=(VariableKindDecl(id=setvar_kind, sort=setvar),),
            constructors=(ConstructorDecl(id=all_, inputs=(setvar, wff), output=wff),),
        ),
        {},
    )
    with pytest.raises(AuthoringSemanticError, match="inherited binder semantics changed"):
        resolve_language(
            LanguageSpec(
                id=LanguageId("test#language:illegal-binder-extension"),
                extends=(LanguageRequirement(id=unbound_base.id),),
                binders=(
                    BinderDecl(
                        constructor=all_,
                        variable_argument=0,
                        scoped_arguments=(1,),
                    ),
                ),
            ),
            {unbound_base.id: unbound_base},
        )
