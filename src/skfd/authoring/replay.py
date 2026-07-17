from __future__ import annotations

from dataclasses import dataclass

from .assertion import (
    AssertionKind,
    AssertionReplayContext,
    AssertionSignature,
    ElaboratedProof,
    apply_assertion,
    start_draft,
)
from .catalog import AssertionCatalogError, AssertionCatalogInterface
from .ids import (
    AssertionProfileId,
    AssertionSemanticId,
    ProofId,
    StepId,
)
from .judgment import CalculusInterface, DistinctPair, Judgment
from .term import Term, VariableRef


@dataclass(frozen=True, slots=True)
class ReplayHypothesis:
    position: int
    result: Judgment


@dataclass(frozen=True, slots=True)
class ReplayApplication:
    position: int
    assertion: AssertionSemanticId
    canonical_label: str
    kind: AssertionKind
    premise_positions: tuple[int, ...]
    substitution: tuple[tuple[VariableRef, Term], ...]
    result: Judgment
    satisfied_distinct: tuple[DistinctPair, ...]


@dataclass(frozen=True, slots=True)
class ResolvedDependency:
    assertion: AssertionSemanticId
    kind: AssertionKind


@dataclass(frozen=True, slots=True)
class SemanticReplayPlan:
    signature: AssertionSignature
    hypotheses: tuple[ReplayHypothesis, ...]
    applications: tuple[ReplayApplication, ...]
    root_position: int
    replay_context: AssertionReplayContext
    dependency_closure: tuple[ResolvedDependency, ...]


def build_semantic_replay_plan(
    proof: ElaboratedProof,
    calculus: CalculusInterface,
    catalog: AssertionCatalogInterface,
    profile: AssertionProfileId,
) -> SemanticReplayPlan:
    if proof.calculus_digest != calculus.digest:
        raise AssertionCatalogError("proof calculus digest mismatch")

    positions = {
        hypothesis.id: index for index, hypothesis in enumerate(proof.hypotheses)
    }
    draft = start_draft(
        _proof_id(proof.root),
        calculus,
        tuple(hypothesis.result for hypothesis in proof.hypotheses),
        active_distinct=proof.replay_context.active_distinct,
        signature=proof.signature,
    )
    applications: list[ReplayApplication] = []
    resolved: dict[AssertionSemanticId, AssertionKind] = {}
    offset = len(proof.hypotheses)
    for index, step in enumerate(proof.steps, start=offset):
        assertion = catalog.assertion(step.assertion, profile=profile)
        applied = apply_assertion(
            draft,
            calculus,
            assertion,
            step.premises,
            target=step.result,
            subst=dict(step.substitution),
        )
        if applied.step != step:
            raise AssertionCatalogError(
                f"proof step does not match catalog assertion: {step.assertion}"
            )
        draft = applied.draft
        positions[step.id] = index
        resolved[assertion.id] = assertion.kind
        applications.append(
            ReplayApplication(
                position=index,
                assertion=assertion.id,
                canonical_label=assertion.canonical_label,
                kind=assertion.kind,
                premise_positions=tuple(positions[item] for item in step.premises),
                substitution=step.substitution,
                result=step.result,
                satisfied_distinct=step.satisfied_distinct,
            )
        )

    dependencies = tuple(
        ResolvedDependency(assertion, resolved[assertion])
        for assertion in proof.dependency_closure
    )
    return SemanticReplayPlan(
        signature=proof.signature,
        hypotheses=tuple(
            ReplayHypothesis(index, hypothesis.result)
            for index, hypothesis in enumerate(proof.hypotheses)
        ),
        applications=tuple(applications),
        root_position=positions[proof.root],
        replay_context=proof.replay_context,
        dependency_closure=dependencies,
    )


def _proof_id(step_id: StepId) -> ProofId:
    prefix, separator, _ = str(step_id).rpartition("/step:")
    if not separator:
        raise AssertionCatalogError(f"noncanonical proof step id: {step_id}")
    return ProofId(prefix)
