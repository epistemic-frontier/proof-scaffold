# skfd/authoring/rules.py
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from .typing import RuleSig

# -----------------------------------------------------------------------------
# Errors (local to this module)
# -----------------------------------------------------------------------------


class PreludeRulesError(ValueError):
    """Raised when rule/registry constraints are violated (e.g. duplicate labels)."""


# -----------------------------------------------------------------------------
# Rule/Axiom interfaces (lightweight, reusable)
# -----------------------------------------------------------------------------

R_co = TypeVar("R_co", covariant=True)  # result type (e.g. Wff)


class Axiom1(Protocol[R_co]):
    """Axiom-like constructor taking 1 hypothesis and returning R."""

    label: str
    arity: int

    def __call__(self, h1: object) -> R_co: ...


class Axiom2(Protocol[R_co]):
    """Axiom-like constructor taking 2 hypotheses and returning R."""

    label: str
    arity: int

    def __call__(self, h1: object, h2: object) -> R_co: ...


class Rule2to1(Protocol[R_co]):
    """Rule-like inference taking 2 hypotheses and returning R."""

    label: str

    def __call__(self, h1: object, h2: object) -> R_co: ...


# -----------------------------------------------------------------------------
# Catalog / registry utilities
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class RuleEntry:
    """A registry entry for a rule/axiom.

    `fn` is a callable object (usually a dataclass instance).
    `kind` helps downstream tooling categorize entries.
    """

    label: str
    kind: str  # e.g. "axiom" | "rule"
    fn: Callable[..., object]


@dataclass(frozen=True)
class RuleBundle:
    rules: Mapping[str, Callable[..., object]]
    sigs: Mapping[str, RuleSig]


@dataclass(frozen=True)
class RuleDecl:
    label: str
    kind: str
    sig: RuleSig
    target: Callable[..., object]


class RuleRegistry:
    def __init__(self) -> None:
        self._decls: list[RuleDecl] = []
        self._by_label: dict[str, RuleDecl] = {}

    def register(self, *, label: str, kind: str, sig: RuleSig, target: Callable[..., object]) -> None:
        existing = self._by_label.get(label)
        if existing is not None and existing.target is not target:
            raise PreludeRulesError(f"duplicate rule label: {label!r}")
        if hasattr(target, "label") and getattr(target, "label") != label:
            raise PreludeRulesError(
                f"rule label mismatch: decorator label={label!r} but target.label={getattr(target, 'label')!r}"
            )
        if hasattr(target, "sig") and getattr(target, "sig") != sig:
            raise PreludeRulesError(
                f"rule signature mismatch for {label!r}: decorator sig differs from target.sig"
            )
        decl = RuleDecl(label=label, kind=kind, sig=sig, target=target)
        if existing is None:
            self._decls.append(decl)
        self._by_label[label] = decl

    def decls(self) -> Sequence[RuleDecl]:
        return tuple(self._decls)


def rule(
    *,
    label: str,
    kind: str,
    sig: RuleSig,
    registry: RuleRegistry,
) -> Callable[[Callable[..., object]], Callable[..., object]]:
    def deco(target: Callable[..., object]) -> Callable[..., object]:
        registry.register(label=label, kind=kind, sig=sig, target=target)
        return target

    return deco


def build_rule_bundle(
    registry: RuleRegistry,
    *,
    bind: Callable[[Callable[..., object]], Callable[..., object]],
) -> RuleBundle:
    rules: dict[str, Callable[..., object]] = {}
    sigs: dict[str, RuleSig] = {}
    for d in registry.decls():
        rules[d.label] = bind(d.target)
        sigs[d.label] = d.sig
    return RuleBundle(rules=rules, sigs=sigs)


def build_rule_catalog(
    registry: RuleRegistry,
    *,
    bind: Callable[[Callable[..., object]], Callable[..., object]],
) -> dict[str, RuleEntry]:
    entries: list[RuleEntry] = []
    for d in registry.decls():
        entries.append(RuleEntry(label=d.label, kind=d.kind, fn=bind(d.target)))
    return build_catalog(entries)


def build_catalog(entries: Iterable[RuleEntry]) -> dict[str, RuleEntry]:
    """Build a label->entry dict with duplicate-label checks."""
    cat: dict[str, RuleEntry] = {}
    for e in entries:
        if e.label in cat:
            raise PreludeRulesError(f"duplicate rule label: {e.label!r}")
        cat[e.label] = e
    return cat


def rules_view(cat: Mapping[str, RuleEntry]) -> Mapping[str, Callable[..., object]]:
    """Convenience: label->callable view."""
    return {k: v.fn for k, v in cat.items()}


def get_rule(cat: Mapping[str, RuleEntry], label: str) -> Callable[..., object]:
    """Fetch a rule/axiom by label. Raises PreludeRulesError if missing."""
    try:
        return cat[label].fn
    except KeyError as e:
        raise PreludeRulesError(f"unknown rule label: {label!r}") from e


def debug_list(cat: Mapping[str, RuleEntry]) -> list[tuple[str, str]]:
    """Return a stable (label, kind) list for debug/introspection."""
    return sorted([(e.label, e.kind) for e in cat.values()], key=lambda x: x[0])


def debug_get(cat: Mapping[str, RuleEntry], label: str) -> Callable[..., object]:
    """Debug fetch: same as get_rule, kept for symmetry and readability."""
    return get_rule(cat, label)


__all__ = [
    "PreludeRulesError",
    "Axiom1",
    "Axiom2",
    "Rule2to1",
    "RuleEntry",
    "RuleDecl",
    "RuleRegistry",
    "rule",
    "RuleBundle",
    "build_catalog",
    "build_rule_bundle",
    "build_rule_catalog",
    "rules_view",
    "get_rule",
]
