from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeAlias

from .assertion import (
    AssertionApplicationError,
    AssertionSignature,
    ElaboratedProof,
    ElaboratedStep,
    HypothesisStep,
    ProofDraft,
    _apply_assertion_step,
    _finalize_proof,
    _validate_assertion_judgments,
    start_draft,
)
from .catalog import AssertionCatalogInterface
from .ids import AssertionProfileId, AssertionSemanticId, Digest, ProofId, StepId
from .judgment import CalculusInterface, DistinctPair, Judgment
from .term import Term, VariableRef

ProofStep: TypeAlias = HypothesisStep | ElaboratedStep

_VALIDATED_CATALOG_ASSERTIONS: set[
    tuple[Digest, Digest, AssertionSemanticId]
] = set()


class ProofAuthor:
    """Small human-facing facade over the immutable assertion kernel."""

    def __init__(
        self,
        signature: AssertionSignature,
        *,
        proof_id: ProofId,
        calculus: CalculusInterface,
        catalog: AssertionCatalogInterface,
        profile: AssertionProfileId,
        active_distinct: Sequence[DistinctPair] = (),
    ) -> None:
        self._calculus = calculus
        self._catalog = catalog
        self._profile = profile
        self._base_draft = start_draft(
            proof_id,
            calculus,
            signature.premises,
            active_distinct=active_distinct,
            signature=signature,
        )
        self._steps: list[ElaboratedStep] = []
        self._results = {
            step.id: step.result for step in self._base_draft.hypotheses
        }
        self._known_steps: dict[int, ProofStep] = {
            id(step): step for step in self._base_draft.hypotheses
        }
        self._draft_cache: ProofDraft | None = self._base_draft

    @property
    def hypotheses(self) -> tuple[HypothesisStep, ...]:
        return self._base_draft.hypotheses

    @property
    def draft(self) -> ProofDraft:
        return self._materialize_draft()

    def use(
        self,
        assertion: AssertionSemanticId | AssertionSignature,
        *premises: ProofStep,
        target: Judgment | None = None,
        subst: Mapping[VariableRef, Term] | None = None,
    ) -> ElaboratedStep:
        premise_ids = tuple(self._known_step_id(step) for step in premises)
        assertion_id = assertion.id if isinstance(assertion, AssertionSignature) else assertion
        signature = self._catalog.assertion(assertion_id, profile=self._profile)
        validation_key = (
            self._calculus.digest,
            self._catalog.digest,
            signature.id,
        )
        if validation_key not in _VALIDATED_CATALOG_ASSERTIONS:
            _validate_assertion_judgments(self._calculus, signature)
            _VALIDATED_CATALOG_ASSERTIONS.add(validation_key)
        step = _apply_assertion_step(
            self._base_draft,
            self._calculus,
            signature,
            premise_ids,
            known_results=self._results,
            step_index=len(self._base_draft.hypotheses) + len(self._steps),
            validate_assertion_judgments=False,
            target=target,
            subst=subst,
        )
        self._steps.append(step)
        self._results[step.id] = step.result
        self._known_steps[id(step)] = step
        self._draft_cache = None
        return step

    def qed(self, root: ProofStep) -> ElaboratedProof:
        root_id = self._known_step_id(root)
        return _finalize_proof(
            self._materialize_draft(),
            self._calculus,
            root=root_id,
            validate_draft_judgments=False,
        )

    def _known_step_id(self, step: ProofStep) -> StepId:
        known = self._known_steps.get(id(step))
        if known is not step:
            raise AssertionApplicationError(
                "proof author arguments must be steps created by this author"
            )
        return step.id

    def _materialize_draft(self) -> ProofDraft:
        if self._draft_cache is None:
            self._draft_cache = ProofDraft(
                proof_id=self._base_draft.proof_id,
                calculus_digest=self._base_draft.calculus_digest,
                signature=self._base_draft.signature,
                hypotheses=self._base_draft.hypotheses,
                steps=tuple(self._steps),
                active_distinct=self._base_draft.active_distinct,
            )
        return self._draft_cache
