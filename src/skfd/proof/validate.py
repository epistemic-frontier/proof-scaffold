from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar


SystemT = TypeVar("SystemT")


class StepLike(Protocol):
    @property
    def label(self) -> str:
        ...

    @property
    def op(self) -> str:
        ...

    @property
    def ref(self) -> str | None:
        ...


class ProofLike(Protocol):
    @property
    def name(self) -> str:
        ...

    @property
    def steps(self) -> Sequence[StepLike]:
        ...


ProofConstructor = Callable[[SystemT], ProofLike]


@dataclass(frozen=True)
class ProofRegistryIssue:
    kind: str
    lemma: str
    message: str
    step: str | None = None
    ref: str | None = None
    details: Mapping[str, object] | None = None


@dataclass(frozen=True)
class ProofRegistryValidationResult:
    proofs: Mapping[str, ProofLike]
    issues: tuple[ProofRegistryIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues


class ProofRegistryValidationError(ValueError):
    def __init__(self, result: ProofRegistryValidationResult) -> None:
        self.result = result
        super().__init__(format_proof_registry_issues(result.issues))


def _names_from(value: Mapping[str, object] | Iterable[str] | None) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, Mapping):
        return set(value)
    return set(value)


def _proof_name(proof: ProofLike, fallback: str) -> str:
    name = proof.name
    return name if name else fallback


def _collect_ref_graph(
    proofs: Mapping[str, ProofLike],
    known_refs: set[str],
) -> tuple[dict[str, set[str]], list[ProofRegistryIssue]]:
    graph: dict[str, set[str]] = {name: set() for name in proofs}
    issues: list[ProofRegistryIssue] = []

    for lemma, proof in proofs.items():
        for step in proof.steps:
            if step.op != "ref":
                continue
            ref = step.ref
            if ref is None or ref == "":
                issues.append(
                    ProofRegistryIssue(
                        kind="missing_step_ref",
                        lemma=lemma,
                        step=step.label,
                        message=f"step {step.label!r} is a ref step with no ref label",
                    )
                )
                continue
            if ref == lemma:
                issues.append(
                    ProofRegistryIssue(
                        kind="self_reference",
                        lemma=lemma,
                        step=step.label,
                        ref=ref,
                        message=f"lemma {lemma!r} references itself",
                    )
                )
            if ref in proofs:
                graph[lemma].add(ref)
                continue
            if ref not in known_refs:
                issues.append(
                    ProofRegistryIssue(
                        kind="unknown_ref",
                        lemma=lemma,
                        step=step.label,
                        ref=ref,
                        message=f"lemma {lemma!r} step {step.label!r} references unknown label {ref!r}",
                    )
                )

    return graph, issues


def _cycle_issues(graph: Mapping[str, set[str]]) -> list[ProofRegistryIssue]:
    permanent: set[str] = set()
    temporary: set[str] = set()
    stack: list[str] = []
    issues: list[ProofRegistryIssue] = []
    seen_cycles: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        if node in permanent:
            return
        if node in temporary:
            idx = stack.index(node)
            cycle = tuple(stack[idx:] + [node])
            key = tuple(sorted(cycle))
            if key not in seen_cycles:
                seen_cycles.add(key)
                issues.append(
                    ProofRegistryIssue(
                        kind="cycle",
                        lemma=node,
                        message="proof registry dependency cycle: " + " -> ".join(cycle),
                        details={"cycle": cycle},
                    )
                )
            return

        temporary.add(node)
        stack.append(node)
        for dep in sorted(graph.get(node, ())):
            visit(dep)
        stack.pop()
        temporary.remove(node)
        permanent.add(node)

    for node in sorted(graph):
        visit(node)

    return issues


def validate_proof_registry(
    *,
    system: SystemT,
    constructors: Mapping[str, ProofConstructor[SystemT]],
    axioms: Mapping[str, object] | Iterable[str] | None = None,
    reserved: Iterable[str] = (),
    known_refs: Iterable[str] = (),
) -> ProofRegistryValidationResult:
    """Validate an authoring proof registry before emission.

    The check is intentionally independent from `emit_lowered_lemmas`: it validates
    the declared constructor surface, even if only a small proof closure is emitted.
    """
    proofs: dict[str, ProofLike] = {}
    issues: list[ProofRegistryIssue] = []

    for registry_name, ctor in constructors.items():
        try:
            proof = ctor(system)
        except Exception as e:
            issues.append(
                ProofRegistryIssue(
                    kind="constructor_error",
                    lemma=registry_name,
                    message=f"constructor for {registry_name!r} failed: {type(e).__name__}: {e}",
                    details={"exception_type": type(e).__name__, "exception": str(e)},
                )
            )
            continue

        proof_name = _proof_name(proof, registry_name)
        if proof_name != registry_name:
            issues.append(
                ProofRegistryIssue(
                    kind="name_mismatch",
                    lemma=registry_name,
                    message=f"registry key {registry_name!r} produced proof {proof_name!r}",
                    details={"proof_name": proof_name},
                )
            )
        if proof_name in proofs:
            issues.append(
                ProofRegistryIssue(
                    kind="duplicate_proof",
                    lemma=proof_name,
                    message=f"duplicate proof name {proof_name!r}",
                )
            )
            continue
        proofs[proof_name] = proof

    allowed_refs = _names_from(axioms) | set(reserved) | set(known_refs)
    graph, ref_issues = _collect_ref_graph(proofs, allowed_refs)
    issues.extend(ref_issues)
    issues.extend(_cycle_issues(graph))

    return ProofRegistryValidationResult(proofs=proofs, issues=tuple(issues))


def assert_valid_proof_registry(
    *,
    system: SystemT,
    constructors: Mapping[str, ProofConstructor[SystemT]],
    axioms: Mapping[str, object] | Iterable[str] | None = None,
    reserved: Iterable[str] = (),
    known_refs: Iterable[str] = (),
) -> Mapping[str, ProofLike]:
    result = validate_proof_registry(
        system=system,
        constructors=constructors,
        axioms=axioms,
        reserved=reserved,
        known_refs=known_refs,
    )
    if not result.ok:
        raise ProofRegistryValidationError(result)
    return result.proofs


def format_proof_registry_issues(issues: Sequence[ProofRegistryIssue]) -> str:
    if not issues:
        return "proof registry is valid"
    lines = ["proof registry validation failed:"]
    for issue in issues:
        loc = issue.lemma
        if issue.step is not None:
            loc = f"{loc}:{issue.step}"
        if issue.ref is not None:
            lines.append(f"- {issue.kind} at {loc}: {issue.message} (ref={issue.ref})")
        else:
            lines.append(f"- {issue.kind} at {loc}: {issue.message}")
    return "\n".join(lines)


__all__ = [
    "ProofConstructor",
    "ProofLike",
    "ProofRegistryIssue",
    "ProofRegistryValidationError",
    "ProofRegistryValidationResult",
    "StepLike",
    "assert_valid_proof_registry",
    "format_proof_registry_issues",
    "validate_proof_registry",
]
