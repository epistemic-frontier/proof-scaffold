from __future__ import annotations

from dataclasses import dataclass

from .assertion import (
    AssertionKind,
    AssertionReplayContext,
    AssertionSignature,
    CompleteProof,
    apply_assertion,
    create_proof_prefix,
)
from .catalog import AssertionCatalogError, AssertionCatalogInterface
from .ids import (
    AssertionProfileId,
    AssertionId,
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
    assertion: AssertionId
    canonical_label: str
    kind: AssertionKind
    premise_positions: tuple[int, ...]
    substitution: tuple[tuple[VariableRef, Term], ...]
    result: Judgment
    satisfied_distinct: tuple[DistinctPair, ...]


@dataclass(frozen=True, slots=True)
class ResolvedDependency:
    assertion: AssertionId
    kind: AssertionKind


@dataclass(frozen=True, slots=True)
class ReplaySequence:
    signature: AssertionSignature
    hypotheses: tuple[ReplayHypothesis, ...]
    applications: tuple[ReplayApplication, ...]
    root_position: int
    replay_context: AssertionReplayContext
    direct_dependencies: tuple[ResolvedDependency, ...]

    @property
    def dependency_closure(self) -> tuple[ResolvedDependency, ...]:
        return self.direct_dependencies

    def __post_init__(self) -> None:
        if tuple(item.result for item in self.hypotheses) != self.signature.premises:
            raise AssertionCatalogError(
                "replay hypotheses do not match the theorem signature"
            )
        hypothesis_count = len(self.hypotheses)
        if tuple(item.position for item in self.hypotheses) != tuple(
            range(hypothesis_count)
        ):
            raise AssertionCatalogError("replay hypothesis positions are not canonical")
        available = set(range(hypothesis_count))
        by_position: dict[int, ReplayApplication] = {}
        for expected, application in enumerate(
            self.applications, start=hypothesis_count
        ):
            if application.position != expected:
                raise AssertionCatalogError(
                    "replay application positions are not canonical"
                )
            if any(position not in available for position in application.premise_positions):
                raise AssertionCatalogError("replay application has a forward premise")
            available.add(application.position)
            by_position[application.position] = application
        if self.root_position not in available:
            raise AssertionCatalogError("replay root position is unknown")

        reachable: set[int] = set()
        pending = [self.root_position]
        while pending:
            position = pending.pop()
            reachable_application = by_position.get(position)
            if reachable_application is None or position in reachable:
                continue
            reachable.add(position)
            pending.extend(reachable_application.premise_positions)
        if reachable != frozenset(by_position):
            raise AssertionCatalogError("replay plan contains unreachable applications")

        expected_dependencies = tuple(
            ResolvedDependency(assertion, kind)
            for assertion, kind in sorted(
                {
                    (application.assertion, application.kind)
                    for application in self.applications
                }
            )
        )
        if self.direct_dependencies != expected_dependencies:
            raise AssertionCatalogError("replay direct dependencies are not canonical")


def replay_proof(
    proof: CompleteProof,
    calculus: CalculusInterface,
    catalog: AssertionCatalogInterface,
    profile: AssertionProfileId,
) -> ReplaySequence:
    if proof.calculus_digest != calculus.digest:
        raise AssertionCatalogError("proof calculus digest mismatch")

    positions = {
        hypothesis.id: index for index, hypothesis in enumerate(proof.hypotheses)
    }
    prefix = create_proof_prefix(
        _proof_id(proof.root),
        calculus,
        tuple(hypothesis.result for hypothesis in proof.hypotheses),
        active_distinct=proof.replay_context.active_distinct,
        signature=proof.signature,
    )
    applications: list[ReplayApplication] = []
    resolved: dict[AssertionId, AssertionKind] = {}
    offset = len(proof.hypotheses)
    for index, step in enumerate(proof.steps, start=offset):
        assertion = catalog.assertion(step.assertion, profile=profile)
        applied = apply_assertion(
            prefix,
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
        prefix = applied.prefix
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
        for assertion in proof.direct_dependencies
    )
    return ReplaySequence(
        signature=proof.signature,
        hypotheses=tuple(
            ReplayHypothesis(index, hypothesis.result)
            for index, hypothesis in enumerate(proof.hypotheses)
        ),
        applications=tuple(applications),
        root_position=positions[proof.root],
        replay_context=proof.replay_context,
        direct_dependencies=dependencies,
    )


def _proof_id(step_id: StepId) -> ProofId:
    prefix, separator, _ = str(step_id).rpartition("/step:")
    if not separator:
        raise AssertionCatalogError(f"noncanonical proof step id: {step_id}")
    return ProofId(prefix)


# Compatibility aliases for callers using the original terminology.
SemanticReplayPlan = ReplaySequence
build_semantic_replay_plan = replay_proof
