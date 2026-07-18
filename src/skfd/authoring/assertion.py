from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from ._canonical import JsonValue, canonical_digest
from .errors import AuthoringSemanticError
from .ids import AssertionSemanticId, Digest, ProofId, StepId
from .judgment import (
    AxiomInterface,
    CalculusInterface,
    DefinitionInterface,
    DistinctPair,
    Judgment,
    PrimitiveRuleDecl,
)
from .term import Term, Var, VariableRef
from .term_ops import variables

AssertionKind: TypeAlias = Literal["axiom", "definition", "primitive_rule", "theorem"]


class AssertionApplicationError(AuthoringSemanticError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class AssertionSignature:
    id: AssertionSemanticId
    canonical_label: str
    kind: AssertionKind
    schema_variables: tuple[VariableRef, ...]
    premises: tuple[Judgment, ...]
    conclusion: Judgment
    mandatory_distinct: tuple[DistinctPair, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in ("axiom", "definition", "primitive_rule", "theorem"):
            raise AssertionApplicationError(f"invalid assertion kind: {self.kind}")
        if not self.canonical_label:
            raise AssertionApplicationError("assertion canonical label must be non-empty")
        declared = frozenset(self.schema_variables)
        if len(declared) != len(self.schema_variables):
            raise AssertionApplicationError(f"duplicate assertion schema variable: {self.id}")
        if any(variable.scope != "schema" for variable in declared):
            raise AssertionApplicationError(f"non-schema assertion variable: {self.id}")
        used = frozenset().union(
            *(
                _judgment_variables(judgment)
                for judgment in (*self.premises, self.conclusion)
            )
        )
        if declared != used:
            raise AssertionApplicationError(
                f"assertion schema variables must exactly match its judgment variables: {self.id}"
            )
        normalized = normalize_distinct_pairs(self.mandatory_distinct)
        if any(pair.left not in used or pair.right not in used for pair in normalized):
            raise AssertionApplicationError(
                f"mandatory distinct endpoint is not an assertion variable: {self.id}"
            )
        object.__setattr__(self, "mandatory_distinct", normalized)


@dataclass(frozen=True, slots=True)
class HypothesisStep:
    id: StepId
    result: Judgment


@dataclass(frozen=True, slots=True)
class ElaboratedStep:
    id: StepId
    assertion: AssertionSemanticId
    premises: tuple[StepId, ...]
    substitution: tuple[tuple[VariableRef, Term], ...]
    result: Judgment
    satisfied_distinct: tuple[DistinctPair, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ProofDraft:
    proof_id: ProofId
    calculus_digest: Digest
    signature: AssertionSignature | None = None
    hypotheses: tuple[HypothesisStep, ...] = ()
    steps: tuple[ElaboratedStep, ...] = ()
    active_distinct: tuple[DistinctPair, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "active_distinct",
            normalize_distinct_pairs(self.active_distinct),
        )
        if self.signature is not None:
            if self.signature.kind != "theorem":
                raise AssertionApplicationError("proof draft signature must be a theorem")
            if tuple(step.result for step in self.hypotheses) != self.signature.premises:
                raise AssertionApplicationError(
                    "draft hypotheses do not match the theorem signature premises"
                )
            mandatory_variables = frozenset(self.signature.schema_variables)
            expected_mandatory = tuple(
                pair
                for pair in self.active_distinct
                if pair.left in mandatory_variables and pair.right in mandatory_variables
            )
            if self.signature.mandatory_distinct != expected_mandatory:
                raise AssertionApplicationError(
                    "theorem mandatory distinct relation does not match its active scope"
                )
            if any(step.assertion == self.signature.id for step in self.steps):
                raise AssertionApplicationError("a theorem draft cannot cite itself")
        prior: set[StepId] = set()
        for index, hypothesis in enumerate(self.hypotheses):
            expected = _step_id(self.proof_id, index)
            if hypothesis.id != expected:
                raise AssertionApplicationError(
                    f"noncanonical hypothesis step id: {hypothesis.id}"
                )
            prior.add(hypothesis.id)
        offset = len(self.hypotheses)
        for index, step in enumerate(self.steps, start=offset):
            expected = _step_id(self.proof_id, index)
            if step.id != expected:
                raise AssertionApplicationError(
                    f"noncanonical elaborated step id: {step.id}"
                )
            if any(premise not in prior for premise in step.premises):
                raise AssertionApplicationError(
                    f"elaborated step has foreign or forward premise: {step.id}"
                )
            prior.add(step.id)


@dataclass(frozen=True, slots=True)
class ApplicationResult:
    draft: ProofDraft
    step: ElaboratedStep


@dataclass(frozen=True, slots=True)
class AssertionReplayContext:
    active_distinct: tuple[DistinctPair, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "active_distinct",
            normalize_distinct_pairs(self.active_distinct),
        )


@dataclass(frozen=True, slots=True)
class ElaboratedProof:
    calculus_digest: Digest
    signature: AssertionSignature
    hypotheses: tuple[HypothesisStep, ...]
    steps: tuple[ElaboratedStep, ...]
    root: StepId
    replay_context: AssertionReplayContext
    dependency_closure: tuple[AssertionSemanticId, ...]
    semantic_digest: Digest = field(init=False)

    def __post_init__(self) -> None:
        _validate_elaborated_proof(self)
        object.__setattr__(self, "semantic_digest", _elaborated_proof_digest(self))


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


def _pair_document(pair: DistinctPair) -> JsonValue:
    return [_variable_document(pair.left), _variable_document(pair.right)]


def assertion_signature_document(signature: AssertionSignature) -> JsonValue:
    return {
        "id": str(signature.id),
        "kind": signature.kind,
        "schema_variables": [
            _variable_document(variable) for variable in signature.schema_variables
        ],
        "premises": [_judgment_document(premise) for premise in signature.premises],
        "conclusion": _judgment_document(signature.conclusion),
        "mandatory_distinct": [
            _pair_document(pair) for pair in signature.mandatory_distinct
        ],
    }


def _canonical_pair(pair: DistinctPair) -> DistinctPair:
    if _variable_key(pair.left) <= _variable_key(pair.right):
        return pair
    return DistinctPair(pair.right, pair.left)


def normalize_distinct_pairs(pairs: Sequence[DistinctPair]) -> tuple[DistinctPair, ...]:
    return tuple(
        sorted(
            {_canonical_pair(pair) for pair in pairs},
            key=lambda pair: (_variable_key(pair.left), _variable_key(pair.right)),
        )
    )


def _judgment_variables(judgment: Judgment) -> frozenset[VariableRef]:
    return frozenset().union(*(variables(argument) for argument in judgment.arguments))


def _make_signature(
    *,
    assertion_id: AssertionSemanticId,
    canonical_label: str,
    kind: AssertionKind,
    schema_variables: tuple[VariableRef, ...],
    premises: tuple[Judgment, ...],
    conclusion: Judgment,
    mandatory_distinct: tuple[DistinctPair, ...],
) -> AssertionSignature:
    return AssertionSignature(
        id=assertion_id,
        canonical_label=canonical_label,
        kind=kind,
        schema_variables=schema_variables,
        premises=premises,
        conclusion=conclusion,
        mandatory_distinct=mandatory_distinct,
    )


def signature_from_axiom(
    axiom: AxiomInterface,
    *,
    canonical_label: str,
) -> AssertionSignature:
    declaration = axiom.declaration
    return _make_signature(
        assertion_id=declaration.id,
        canonical_label=canonical_label,
        kind="axiom",
        schema_variables=declaration.schema_variables,
        premises=(),
        conclusion=declaration.conclusion,
        mandatory_distinct=declaration.mandatory_distinct,
    )


def signature_from_definition(
    definition: DefinitionInterface,
    *,
    canonical_label: str,
) -> AssertionSignature:
    declaration = definition.declaration
    return _make_signature(
        assertion_id=declaration.id,
        canonical_label=canonical_label,
        kind="definition",
        schema_variables=declaration.schema_variables,
        premises=(),
        conclusion=declaration.conclusion,
        mandatory_distinct=declaration.mandatory_distinct,
    )


def signature_from_primitive_rule(
    rule: PrimitiveRuleDecl,
    *,
    assertion_id: AssertionSemanticId,
    canonical_label: str,
) -> AssertionSignature:
    return _make_signature(
        assertion_id=assertion_id,
        canonical_label=canonical_label,
        kind="primitive_rule",
        schema_variables=rule.schema_variables,
        premises=rule.premises,
        conclusion=rule.conclusion,
        mandatory_distinct=rule.mandatory_distinct,
    )


def start_draft(
    proof_id: ProofId,
    calculus: CalculusInterface,
    hypotheses: Sequence[Judgment],
    *,
    active_distinct: Sequence[DistinctPair] = (),
    signature: AssertionSignature | None = None,
) -> ProofDraft:
    checked_hypotheses = tuple(
        _checked_judgment(calculus, hypothesis, context="hypothesis")
        for hypothesis in hypotheses
    )
    normalized_distinct = normalize_distinct_pairs(active_distinct)
    for pair in normalized_distinct:
        for endpoint in (pair.left, pair.right):
            if endpoint.kind not in calculus.language.variable_kinds:
                raise AssertionApplicationError(
                    f"active distinct endpoint has unknown variable kind: {endpoint.local_key}"
                )
    if signature is not None:
        if signature.kind != "theorem":
            raise AssertionApplicationError("only theorem signatures can start proof drafts")
        checked_signature_premises = tuple(
            _checked_judgment(calculus, premise, context="draft signature premise")
            for premise in signature.premises
        )
        _checked_judgment(
            calculus,
            signature.conclusion,
            context="draft signature conclusion",
        )
        if checked_hypotheses != checked_signature_premises:
            raise AssertionApplicationError(
                "draft hypotheses do not match the theorem signature premises"
            )
    return ProofDraft(
        proof_id=proof_id,
        calculus_digest=calculus.digest,
        signature=signature,
        hypotheses=tuple(
            HypothesisStep(_step_id(proof_id, index), judgment)
            for index, judgment in enumerate(checked_hypotheses)
        ),
        active_distinct=normalized_distinct,
    )


def _step_id(proof_id: ProofId, index: int) -> StepId:
    return StepId(f"{proof_id}/step:{index}")


def _checked_judgment(
    calculus: CalculusInterface,
    judgment: Judgment,
    *,
    context: str,
) -> Judgment:
    try:
        return calculus.judgment(judgment.kind, judgment.arguments)
    except AuthoringSemanticError as error:
        raise AssertionApplicationError(f"invalid {context}: {error}") from error


def _unify_term(
    pattern: Term,
    actual: Term,
    schema_variables: frozenset[VariableRef],
    substitution: dict[VariableRef, Term],
) -> None:
    if isinstance(pattern, Var) and pattern.variable in schema_variables:
        if pattern.sort != actual.sort:
            raise AssertionApplicationError(
                f"substitution sort mismatch: {pattern.variable.local_key}"
            )
        existing = substitution.get(pattern.variable)
        if existing is not None and existing != actual:
            raise AssertionApplicationError(
                f"inconsistent substitution: {pattern.variable.local_key}"
            )
        substitution[pattern.variable] = actual
        return
    if isinstance(pattern, Var) or isinstance(actual, Var):
        if pattern != actual:
            raise AssertionApplicationError("assertion term does not match the supplied judgment")
        return
    if (
        pattern.constructor != actual.constructor
        or pattern.sort != actual.sort
        or len(pattern.arguments) != len(actual.arguments)
    ):
        raise AssertionApplicationError("assertion term does not match the supplied judgment")
    for pattern_argument, actual_argument in zip(
        pattern.arguments, actual.arguments, strict=True
    ):
        _unify_term(pattern_argument, actual_argument, schema_variables, substitution)


def _unify_judgment(
    pattern: Judgment,
    actual: Judgment,
    schema_variables: frozenset[VariableRef],
    substitution: dict[VariableRef, Term],
) -> None:
    if pattern.kind != actual.kind or len(pattern.arguments) != len(actual.arguments):
        raise AssertionApplicationError("assertion judgment does not match")
    for pattern_argument, actual_argument in zip(
        pattern.arguments, actual.arguments, strict=True
    ):
        _unify_term(pattern_argument, actual_argument, schema_variables, substitution)


def _instantiate_term(
    pattern: Term,
    schema_variables: frozenset[VariableRef],
    substitution: Mapping[VariableRef, Term],
    calculus: CalculusInterface,
) -> Term:
    if isinstance(pattern, Var):
        if pattern.variable not in schema_variables:
            return pattern
        return substitution[pattern.variable]
    return calculus.language.apply(
        pattern.constructor,
        tuple(
            _instantiate_term(argument, schema_variables, substitution, calculus)
            for argument in pattern.arguments
        ),
    )


def _instantiate_judgment(
    pattern: Judgment,
    schema_variables: frozenset[VariableRef],
    substitution: Mapping[VariableRef, Term],
    calculus: CalculusInterface,
) -> Judgment:
    try:
        arguments = tuple(
            _instantiate_term(argument, schema_variables, substitution, calculus)
            for argument in pattern.arguments
        )
    except AuthoringSemanticError as error:
        raise AssertionApplicationError(f"invalid instantiated assertion term: {error}") from error
    return _checked_judgment(
        calculus,
        Judgment(pattern.kind, arguments),
        context="instantiated assertion judgment",
    )


def _step_results(draft: ProofDraft) -> dict[StepId, Judgment]:
    results = {step.id: step.result for step in draft.hypotheses}
    results.update((step.id, step.result) for step in draft.steps)
    return results


def apply_assertion(
    draft: ProofDraft,
    calculus: CalculusInterface,
    assertion: AssertionSignature,
    premises: Sequence[StepId],
    *,
    target: Judgment | None = None,
    subst: Mapping[VariableRef, Term] | None = None,
) -> ApplicationResult:
    if draft.calculus_digest != calculus.digest:
        raise AssertionApplicationError("draft calculus digest mismatch")
    if len(premises) != len(assertion.premises):
        raise AssertionApplicationError("assertion premise count mismatch")
    if draft.signature is not None and assertion.id == draft.signature.id:
        raise AssertionApplicationError("a theorem draft cannot cite itself")

    for pattern in (*assertion.premises, assertion.conclusion):
        _checked_judgment(calculus, pattern, context="assertion signature judgment")
    for hypothesis in draft.hypotheses:
        _checked_judgment(calculus, hypothesis.result, context="draft step judgment")
    for step in draft.steps:
        _checked_judgment(calculus, step.result, context="draft step judgment")

    schema_variables = frozenset(assertion.schema_variables)
    substitution: dict[VariableRef, Term] = {}
    for variable, replacement in (subst or {}).items():
        if variable not in schema_variables:
            raise AssertionApplicationError(
                f"foreign explicit substitution variable: {variable.local_key}"
            )
        variable_kind = calculus.language.variable_kinds.get(variable.kind)
        if variable_kind is None:
            raise AssertionApplicationError(
                f"explicit substitution has unknown variable kind: {variable.local_key}"
            )
        expected_sort = variable_kind.sort
        if replacement.sort != expected_sort:
            raise AssertionApplicationError(
                f"explicit substitution sort mismatch: {variable.local_key}"
            )
        substitution[variable] = replacement

    results = _step_results(draft)
    actual_premises: list[Judgment] = []
    for step_id in premises:
        actual = results.get(step_id)
        if actual is None:
            raise AssertionApplicationError(f"unknown premise step: {step_id}")
        actual_premises.append(actual)
    for pattern, actual in zip(assertion.premises, actual_premises, strict=True):
        _unify_judgment(pattern, actual, schema_variables, substitution)

    if target is not None:
        checked_target = _checked_judgment(calculus, target, context="explicit target")
        _unify_judgment(assertion.conclusion, checked_target, schema_variables, substitution)

    missing = [
        variable.local_key
        for variable in assertion.schema_variables
        if variable not in substitution
    ]
    if missing:
        raise AssertionApplicationError(
            "underdetermined assertion substitution: " + ", ".join(missing)
        )

    for pattern, actual in zip(assertion.premises, actual_premises, strict=True):
        if _instantiate_judgment(pattern, schema_variables, substitution, calculus) != actual:
            raise AssertionApplicationError("instantiated assertion premise mismatch")
    result = _instantiate_judgment(
        assertion.conclusion, schema_variables, substitution, calculus
    )
    if target is not None and result != target:
        raise AssertionApplicationError("assertion result does not match explicit target")

    active_distinct = frozenset(draft.active_distinct)
    satisfied: set[DistinctPair] = set()
    for required in assertion.mandatory_distinct:
        left_variables = variables(substitution[required.left])
        right_variables = variables(substitution[required.right])
        if left_variables & right_variables:
            raise AssertionApplicationError("mandatory distinct substitutions overlap")
        for left in left_variables:
            for right in right_variables:
                actual_pair = _canonical_pair(DistinctPair(left, right))
                if actual_pair not in active_distinct:
                    raise AssertionApplicationError(
                        "missing active distinct-variable pair: "
                        f"{left.local_key}, {right.local_key}"
                    )
                satisfied.add(actual_pair)

    index = len(draft.hypotheses) + len(draft.steps)
    step = ElaboratedStep(
        id=_step_id(draft.proof_id, index),
        assertion=assertion.id,
        premises=tuple(premises),
        substitution=tuple(
            (variable, substitution[variable]) for variable in assertion.schema_variables
        ),
        result=result,
        satisfied_distinct=normalize_distinct_pairs(tuple(satisfied)),
    )
    return ApplicationResult(
        ProofDraft(
            proof_id=draft.proof_id,
            calculus_digest=draft.calculus_digest,
            signature=draft.signature,
            hypotheses=draft.hypotheses,
            steps=(*draft.steps, step),
            active_distinct=draft.active_distinct,
        ),
        step,
    )


def finalize_proof(
    draft: ProofDraft,
    calculus: CalculusInterface,
    *,
    root: StepId,
) -> ElaboratedProof:
    if draft.calculus_digest != calculus.digest:
        raise AssertionApplicationError("draft calculus digest mismatch")
    signature = draft.signature
    if signature is None:
        raise AssertionApplicationError("draft has no theorem signature")
    if signature.kind != "theorem":
        raise AssertionApplicationError("only theorem drafts can be finalized")
    if any(step.assertion == signature.id for step in draft.steps):
        raise AssertionApplicationError("a theorem proof cannot cite itself")
    checked_premises = tuple(
        _checked_judgment(calculus, premise, context="theorem premise")
        for premise in signature.premises
    )
    if tuple(hypothesis.result for hypothesis in draft.hypotheses) != checked_premises:
        raise AssertionApplicationError(
            "draft hypotheses do not match the theorem signature premises"
        )
    for step in draft.steps:
        _checked_judgment(calculus, step.result, context="elaborated proof step")
    results = _step_results(draft)
    root_result = results.get(root)
    if root_result is None:
        raise AssertionApplicationError(f"unknown proof root: {root}")
    expected = _checked_judgment(
        calculus,
        signature.conclusion,
        context="theorem conclusion",
    )
    if root_result != expected:
        raise AssertionApplicationError("proof root does not match the theorem conclusion")

    reachable = _reachable_elaborated_steps(draft.hypotheses, draft.steps, root)
    if reachable != frozenset(step.id for step in draft.steps):
        raise AssertionApplicationError("proof contains an elaborated step unreachable from its root")
    dependencies = tuple(sorted({step.assertion for step in draft.steps}))
    replay_context = AssertionReplayContext(draft.active_distinct)
    return ElaboratedProof(
        calculus_digest=calculus.digest,
        signature=signature,
        hypotheses=draft.hypotheses,
        steps=draft.steps,
        root=root,
        replay_context=replay_context,
        dependency_closure=dependencies,
    )


def _reachable_elaborated_steps(
    hypotheses: tuple[HypothesisStep, ...],
    steps: tuple[ElaboratedStep, ...],
    root: StepId,
) -> frozenset[StepId]:
    hypothesis_ids = frozenset(hypothesis.id for hypothesis in hypotheses)
    by_id = {step.id: step for step in steps}
    reachable: set[StepId] = set()
    pending = [root]
    while pending:
        current = pending.pop()
        if current in hypothesis_ids or current in reachable:
            continue
        step = by_id.get(current)
        if step is None:
            raise AssertionApplicationError(f"proof references an unknown step: {current}")
        reachable.add(current)
        pending.extend(step.premises)
    return frozenset(reachable)


def _validate_elaborated_proof(proof: ElaboratedProof) -> None:
    if proof.signature.kind != "theorem":
        raise AssertionApplicationError("elaborated proof signature must be a theorem")
    if any(step.assertion == proof.signature.id for step in proof.steps):
        raise AssertionApplicationError("an elaborated theorem cannot cite itself")
    if tuple(hypothesis.result for hypothesis in proof.hypotheses) != proof.signature.premises:
        raise AssertionApplicationError(
            "elaborated proof hypotheses do not match its signature"
        )
    prior: set[StepId] = set()
    for hypothesis in proof.hypotheses:
        if hypothesis.id in prior:
            raise AssertionApplicationError("elaborated proof has duplicate step ids")
        prior.add(hypothesis.id)
    for step in proof.steps:
        if step.id in prior:
            raise AssertionApplicationError("elaborated proof has duplicate step ids")
        if any(premise not in prior for premise in step.premises):
            raise AssertionApplicationError(
                "elaborated proof has a foreign or forward premise"
            )
        prior.add(step.id)
    results = {hypothesis.id: hypothesis.result for hypothesis in proof.hypotheses}
    results.update((step.id, step.result) for step in proof.steps)
    if results.get(proof.root) != proof.signature.conclusion:
        raise AssertionApplicationError("elaborated proof root does not match its conclusion")
    reachable = _reachable_elaborated_steps(proof.hypotheses, proof.steps, proof.root)
    if reachable != frozenset(step.id for step in proof.steps):
        raise AssertionApplicationError("elaborated proof contains unreachable steps")
    dependencies = tuple(sorted({step.assertion for step in proof.steps}))
    if proof.dependency_closure != dependencies:
        raise AssertionApplicationError("elaborated proof dependency closure is not canonical")
    mandatory_variables = frozenset(proof.signature.schema_variables)
    expected_mandatory = tuple(
        pair
        for pair in proof.replay_context.active_distinct
        if pair.left in mandatory_variables and pair.right in mandatory_variables
    )
    if proof.signature.mandatory_distinct != expected_mandatory:
        raise AssertionApplicationError(
            "elaborated proof mandatory distinct relation does not match replay context"
        )


def _elaborated_proof_digest(proof: ElaboratedProof) -> Digest:
    positions = {
        hypothesis.id: index for index, hypothesis in enumerate(proof.hypotheses)
    }
    offset = len(proof.hypotheses)
    positions.update(
        (step.id, index)
        for index, step in enumerate(proof.steps, start=offset)
    )
    return canonical_digest(
        {
            "version": "skfd.elaborated-proof.v2",
            "calculus_digest": str(proof.calculus_digest),
            "signature": assertion_signature_document(proof.signature),
            "hypotheses": [
                _judgment_document(hypothesis.result) for hypothesis in proof.hypotheses
            ],
            "steps": [
                {
                    "assertion": str(step.assertion),
                    "premises": [positions[premise] for premise in step.premises],
                    "substitution": [
                        [_variable_document(variable), _term_document(term)]
                        for variable, term in step.substitution
                    ],
                    "result": _judgment_document(step.result),
                    "satisfied_distinct": [
                        _pair_document(pair) for pair in step.satisfied_distinct
                    ],
                }
                for step in proof.steps
            ],
            "root": positions[proof.root],
            "active_distinct": [
                _pair_document(pair) for pair in proof.replay_context.active_distinct
            ],
            "dependency_closure": [
                str(dependency) for dependency in proof.dependency_closure
            ],
        }
    )
