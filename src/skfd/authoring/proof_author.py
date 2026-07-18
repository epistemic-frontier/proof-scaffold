from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeAlias

from .assertion import (
    AssertionApplicationError,
    AssertionSignature,
    CompleteProof,
    AssertionStep,
    HypothesisStep,
    CheckedProofPrefix,
    _apply_assertion_step,
    _finalize_proof,
    _validate_assertion_judgments,
    create_proof_prefix,
)
from .catalog import AssertionCatalogInterface
from .ids import AssertionId, AssertionProfileId, Digest, ProofId, StepId
from .judgment import CalculusInterface, DistinctPair, Judgment
from .term import Term, VariableRef

ProofStep: TypeAlias = HypothesisStep | AssertionStep

_VALIDATED_CATALOG_ASSERTIONS: set[
    tuple[Digest, Digest, AssertionId]
] = set()


class ProofAuthor:
    """Convenience API for writing complete, forward, linear proofs."""

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
        self._base_prefix = create_proof_prefix(
            proof_id,
            calculus,
            signature.premises,
            active_distinct=active_distinct,
            signature=signature,
        )
        self._steps: list[AssertionStep] = []
        self._results = {
            step.id: step.result for step in self._base_prefix.hypotheses
        }
        self._known_steps: dict[int, ProofStep] = {
            id(step): step for step in self._base_prefix.hypotheses
        }
        self._prefix_cache: CheckedProofPrefix | None = self._base_prefix

    @property
    def hypotheses(self) -> tuple[HypothesisStep, ...]:
        return self._base_prefix.hypotheses

    @property
    def checked_prefix(self) -> CheckedProofPrefix:
        return self._materialize_prefix()

    @property
    def draft(self) -> CheckedProofPrefix:
        return self.checked_prefix

    def use(
        self,
        assertion: AssertionId | AssertionSignature,
        *premises: ProofStep,
        target: Judgment | None = None,
        subst: Mapping[VariableRef, Term] | None = None,
    ) -> AssertionStep:
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
            self._base_prefix,
            self._calculus,
            signature,
            premise_ids,
            known_results=self._results,
            step_index=len(self._base_prefix.hypotheses) + len(self._steps),
            validate_assertion_judgments=False,
            target=target,
            subst=subst,
        )
        self._steps.append(step)
        self._results[step.id] = step.result
        self._known_steps[id(step)] = step
        self._prefix_cache = None
        return step

    def qed(self, root: ProofStep) -> CompleteProof:
        root_id = self._known_step_id(root)
        return _finalize_proof(
            self._materialize_prefix(),
            self._calculus,
            root=root_id,
            validate_prefix_judgments=False,
        )

    def _known_step_id(self, step: ProofStep) -> StepId:
        known = self._known_steps.get(id(step))
        if known is not step:
            raise AssertionApplicationError(
                "ProofAuthor arguments must be steps created by this ProofAuthor"
            )
        return step.id

    def _materialize_prefix(self) -> CheckedProofPrefix:
        if self._prefix_cache is None:
            self._prefix_cache = CheckedProofPrefix(
                proof_id=self._base_prefix.proof_id,
                calculus_digest=self._base_prefix.calculus_digest,
                signature=self._base_prefix.signature,
                hypotheses=self._base_prefix.hypotheses,
                steps=tuple(self._steps),
                active_distinct=self._base_prefix.active_distinct,
            )
        return self._prefix_cache
