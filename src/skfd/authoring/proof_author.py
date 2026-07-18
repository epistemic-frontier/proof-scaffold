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
    finalize_proof,
    start_draft,
)
from .catalog import (
    AssertionCatalogInterface,
    apply_assertion_by_id,
)
from .ids import AssertionProfileId, AssertionSemanticId, ProofId, StepId
from .judgment import CalculusInterface, DistinctPair, Judgment
from .term import Term, VariableRef

ProofStep: TypeAlias = HypothesisStep | ElaboratedStep


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
        self._draft = start_draft(
            proof_id,
            calculus,
            signature.premises,
            active_distinct=active_distinct,
            signature=signature,
        )

    @property
    def hypotheses(self) -> tuple[HypothesisStep, ...]:
        return self._draft.hypotheses

    @property
    def draft(self) -> ProofDraft:
        return self._draft

    def use(
        self,
        assertion: AssertionSemanticId | AssertionSignature,
        *premises: ProofStep,
        target: Judgment | None = None,
        subst: Mapping[VariableRef, Term] | None = None,
    ) -> ElaboratedStep:
        premise_ids = tuple(self._known_step_id(step) for step in premises)
        assertion_id = assertion.id if isinstance(assertion, AssertionSignature) else assertion
        result = apply_assertion_by_id(
            self._draft,
            self._calculus,
            self._catalog,
            self._profile,
            assertion_id,
            premise_ids,
            target=target,
            subst=subst,
        )
        self._draft = result.draft
        return result.step

    def qed(self, root: ProofStep) -> ElaboratedProof:
        return finalize_proof(
            self._draft,
            self._calculus,
            root=self._known_step_id(root),
        )

    def _known_step_id(self, step: ProofStep) -> StepId:
        known = (*self._draft.hypotheses, *self._draft.steps)
        if not any(candidate is step for candidate in known):
            raise AssertionApplicationError(
                "proof author arguments must be steps created by this author"
            )
        return step.id
