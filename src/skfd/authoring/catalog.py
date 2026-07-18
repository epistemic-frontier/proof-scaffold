from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from ._canonical import canonical_digest
from .assertion import (
    AssertionApplicationResult,
    AssertionApplicationError,
    AssertionSignature,
    CheckedProofPrefix,
    apply_assertion,
    assertion_signature_document,
)
from .ids import (
    AssertionCatalogId,
    AssertionProfileId,
    AssertionId,
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
    allowed: tuple[AssertionId, ...]

    def __post_init__(self) -> None:
        if len(frozenset(self.allowed)) != len(self.allowed):
            raise AssertionCatalogError(f"duplicate assertion in profile: {self.id}")


@dataclass(frozen=True, slots=True, kw_only=True)
class AssertionCatalogRequirement:
    id: AssertionCatalogId
    digest: Digest | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class AssertionCatalogSpec:
    id: AssertionCatalogId
    assertions: tuple[AssertionSignature, ...]
    profiles: tuple[AssertionProfileSpec, ...]
    extends: tuple[AssertionCatalogRequirement, ...] = ()


@dataclass(frozen=True, slots=True)
class AssertionCatalogInterface:
    id: AssertionCatalogId
    digest: Digest
    assertions: Mapping[AssertionId, AssertionSignature] = field(
        compare=False, hash=False, repr=False
    )
    labels: Mapping[str, AssertionId] = field(
        compare=False, hash=False, repr=False
    )
    profiles: Mapping[AssertionProfileId, frozenset[AssertionId]] = field(
        compare=False, hash=False, repr=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "assertions", MappingProxyType(dict(self.assertions)))
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))
        object.__setattr__(self, "profiles", MappingProxyType(dict(self.profiles)))

    def assertion(
        self,
        assertion_id: AssertionId,
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


def resolve_assertion_catalog(
    spec: AssertionCatalogSpec,
    dependencies: Mapping[AssertionCatalogId, AssertionCatalogInterface] | None = None,
) -> AssertionCatalogInterface:
    dependency_map = dependencies or {}
    assertions: dict[AssertionId, AssertionSignature] = {}
    labels: dict[str, AssertionId] = {}
    profiles: dict[AssertionProfileId, frozenset[AssertionId]] = {}

    def merge_assertion(assertion: AssertionSignature) -> None:
        old = assertions.get(assertion.id)
        if old is not None and old != assertion:
            raise AssertionCatalogError(f"conflicting assertion id: {assertion.id}")
        old_id = labels.get(assertion.canonical_label)
        if old_id is not None and old_id != assertion.id:
            raise AssertionCatalogError(
                f"conflicting assertion label: {assertion.canonical_label}"
            )
        assertions[assertion.id] = assertion
        labels[assertion.canonical_label] = assertion.id

    for requirement in sorted(spec.extends, key=lambda item: item.id):
        dependency = dependency_map.get(requirement.id)
        if dependency is None:
            raise AssertionCatalogError(f"missing assertion catalog dependency: {requirement.id}")
        if requirement.digest is not None and requirement.digest != dependency.digest:
            raise AssertionCatalogError(f"assertion catalog digest mismatch: {requirement.id}")
        for assertion in dependency.assertions.values():
            merge_assertion(assertion)
        for profile_id, allowed in dependency.profiles.items():
            old = profiles.get(profile_id)
            if old is not None and old != allowed:
                raise AssertionCatalogError(f"conflicting assertion profile: {profile_id}")
            profiles[profile_id] = allowed

    local_assertion_ids: set[AssertionId] = set()
    local_assertion_labels: set[str] = set()
    for assertion in spec.assertions:
        if assertion.id in local_assertion_ids:
            raise AssertionCatalogError(f"duplicate assertion id: {assertion.id}")
        if assertion.canonical_label in local_assertion_labels:
            raise AssertionCatalogError(
                f"duplicate assertion label: {assertion.canonical_label}"
            )
        local_assertion_ids.add(assertion.id)
        local_assertion_labels.add(assertion.canonical_label)
        merge_assertion(assertion)

    local_profile_ids: set[AssertionProfileId] = set()
    for profile in spec.profiles:
        if profile.id in local_profile_ids:
            raise AssertionCatalogError(f"duplicate assertion profile: {profile.id}")
        local_profile_ids.add(profile.id)
        old = profiles.get(profile.id)
        allowed = frozenset(profile.allowed)
        if old is not None and old != allowed:
            raise AssertionCatalogError(f"conflicting assertion profile: {profile.id}")
        missing = frozenset(profile.allowed) - assertions.keys()
        if missing:
            raise AssertionCatalogError(
                f"profile {profile.id} references unknown assertion: {min(missing)}"
            )
        profiles[profile.id] = allowed

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
    prefix: CheckedProofPrefix,
    calculus: CalculusInterface,
    catalog: AssertionCatalogInterface,
    profile: AssertionProfileId,
    assertion_id: AssertionId,
    premises: Sequence[StepId],
    *,
    target: Judgment | None = None,
    subst: Mapping[VariableRef, Term] | None = None,
) -> AssertionApplicationResult:
    return apply_assertion(
        prefix,
        calculus,
        catalog.assertion(assertion_id, profile=profile),
        premises,
        target=target,
        subst=subst,
    )
