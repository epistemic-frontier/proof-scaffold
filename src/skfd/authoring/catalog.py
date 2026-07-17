from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from ._canonical import canonical_digest
from .assertion import (
    ApplicationResult,
    AssertionApplicationError,
    AssertionSignature,
    ProofDraft,
    apply_assertion,
    assertion_signature_document,
)
from .ids import (
    AssertionCatalogId,
    AssertionProfileId,
    AssertionSemanticId,
    Digest,
    StepId,
)
from .judgment import CalculusInterface, Judgment
from .term import Term, VariableRef


class AssertionCatalogError(AssertionApplicationError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class AssertionProfileSpec:
    id: AssertionProfileId
    allowed: tuple[AssertionSemanticId, ...]

    def __post_init__(self) -> None:
        if len(frozenset(self.allowed)) != len(self.allowed):
            raise AssertionCatalogError(f"duplicate assertion in profile: {self.id}")


@dataclass(frozen=True, slots=True, kw_only=True)
class AssertionCatalogSpec:
    id: AssertionCatalogId
    assertions: tuple[AssertionSignature, ...]
    profiles: tuple[AssertionProfileSpec, ...]


@dataclass(frozen=True, slots=True)
class AssertionCatalogInterface:
    id: AssertionCatalogId
    digest: Digest
    assertions: Mapping[AssertionSemanticId, AssertionSignature] = field(
        compare=False, hash=False, repr=False
    )
    labels: Mapping[str, AssertionSemanticId] = field(
        compare=False, hash=False, repr=False
    )
    profiles: Mapping[AssertionProfileId, frozenset[AssertionSemanticId]] = field(
        compare=False, hash=False, repr=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "assertions", MappingProxyType(dict(self.assertions)))
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))
        object.__setattr__(self, "profiles", MappingProxyType(dict(self.profiles)))

    def assertion(
        self,
        assertion_id: AssertionSemanticId,
        *,
        profile: AssertionProfileId,
    ) -> AssertionSignature:
        allowed = self.profiles.get(profile)
        if allowed is None:
            raise AssertionCatalogError(f"unknown assertion profile: {profile}")
        assertion = self.assertions.get(assertion_id)
        if assertion is None:
            raise AssertionCatalogError(f"unknown assertion: {assertion_id}")
        if assertion_id not in allowed:
            raise AssertionCatalogError(
                f"assertion {assertion_id} is not allowed by profile {profile}"
            )
        return assertion


def resolve_assertion_catalog(spec: AssertionCatalogSpec) -> AssertionCatalogInterface:
    assertions: dict[AssertionSemanticId, AssertionSignature] = {}
    labels: dict[str, AssertionSemanticId] = {}
    for assertion in spec.assertions:
        if assertion.id in assertions:
            raise AssertionCatalogError(f"duplicate assertion id: {assertion.id}")
        if assertion.canonical_label in labels:
            raise AssertionCatalogError(
                f"duplicate assertion label: {assertion.canonical_label}"
            )
        assertions[assertion.id] = assertion
        labels[assertion.canonical_label] = assertion.id

    profiles: dict[AssertionProfileId, frozenset[AssertionSemanticId]] = {}
    for profile in spec.profiles:
        if profile.id in profiles:
            raise AssertionCatalogError(f"duplicate assertion profile: {profile.id}")
        missing = frozenset(profile.allowed) - assertions.keys()
        if missing:
            raise AssertionCatalogError(
                f"profile {profile.id} references unknown assertion: {min(missing)}"
            )
        profiles[profile.id] = frozenset(profile.allowed)

    digest = canonical_digest(
        {
            "version": "skfd.assertion-catalog.v1",
            "assertions": [
                {
                    "signature": assertion_signature_document(assertion),
                    "canonical_label": assertion.canonical_label,
                }
                for assertion in sorted(assertions.values(), key=lambda item: item.id)
            ],
            "profiles": [
                {
                    "id": str(profile_id),
                    "allowed": [str(item) for item in sorted(allowed)],
                }
                for profile_id, allowed in sorted(profiles.items())
            ],
        }
    )
    return AssertionCatalogInterface(spec.id, digest, assertions, labels, profiles)


def apply_assertion_by_id(
    draft: ProofDraft,
    calculus: CalculusInterface,
    catalog: AssertionCatalogInterface,
    profile: AssertionProfileId,
    assertion_id: AssertionSemanticId,
    premises: Sequence[StepId],
    *,
    target: Judgment | None = None,
    subst: Mapping[VariableRef, Term] | None = None,
) -> ApplicationResult:
    return apply_assertion(
        draft,
        calculus,
        catalog.assertion(assertion_id, profile=profile),
        premises,
        target=target,
        subst=subst,
    )
