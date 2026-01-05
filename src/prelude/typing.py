# prelude/typing.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Literal, Mapping, Sequence, Tuple, TypeVar, Final, Protocol

from .formula import Formula, Sort

S = TypeVar("S", bound=Sort)

WFF: Final[Sort] = "wff"
CLS: Final[Sort] = "class"
SETVAR: Final[Sort] = "setvar"

# -----------------------------------------------------------------------------
# Errors
# -----------------------------------------------------------------------------

class PreludeTypingError(TypeError):
    """Raised when typed scaffold constraints are violated."""


class PreludeShapeError(ValueError):
    """Raised when a rule expects a specific syntactic shape but sees another."""


# -----------------------------------------------------------------------------
# Core objects: Hypothesis / Judgment Context
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Hypothesis(Generic[S]):
    """A labeled hypothesis with a typed body."""
    label: str
    body: Formula[S]


HypWff = Hypothesis[Literal["wff"]]
HypClass = Hypothesis[Literal["class"]]
HypSetVar = Hypothesis[Literal["setvar"]]


@dataclass(frozen=True)
class Context:
    """A minimal typing context Γ containing visible hypotheses.

    Prelude only: no scope frames, no exports; linker handles that later.
    This is used by DSL builder to carry the currently available hyps.
    """
    hyps: Tuple[Hypothesis[Sort], ...] = ()

    def extend(self, *new_hyps: Hypothesis[Sort]) -> Context:
        return Context(hyps=self.hyps + tuple(new_hyps))

    def by_label(self) -> Mapping[str, Hypothesis[Sort]]:
        # last-wins is fine for prelude; higher layers can forbid shadowing
        return {h.label: h for h in self.hyps}

    def require(self, label: str, *, ctx: str) -> Hypothesis[Sort]:
        for h in reversed(self.hyps):
            if h.label == label:
                return h
        raise PreludeTypingError(f"{ctx}: missing hypothesis label {label!r}")


# -----------------------------------------------------------------------------
# Sort checks
# -----------------------------------------------------------------------------

def require_sort(formula: Formula[Sort], expected: Sort, *, ctx: str) -> None:
    if formula.sort != expected:
        raise PreludeTypingError(
            f"{ctx}: expected sort={expected!r}, got sort={formula.sort!r} (tokens_len={len(formula.tokens)})"
        )


def require_hyp_sort(h: Hypothesis[Sort], expected: Sort, *, ctx: str) -> None:
    require_sort(h.body, expected, ctx=f"{ctx} (hyp={h.label!r})")


# -----------------------------------------------------------------------------
# Rule signatures (the "typing" part)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class RuleSig:
    """Rule signature: input sorts -> output sort.

    Examples:
      wi: (wff, wff) -> wff
      mp: (wff, wff) -> wff    (shape constraint handled by _syntactic.py)
    """
    in_sorts: Tuple[Sort, ...]
    out_sort: Sort

    @property
    def arity(self) -> int:
        return len(self.in_sorts)


@dataclass(frozen=True)
class RuleApp:
    """A typed rule application checker.

    This object does not *execute* the rule; it only validates arity/sorts.
    Execution remains in prelude/_syntactic.py to keep responsibilities crisp.
    """
    sigs: Mapping[str, RuleSig]

    def check(self, label: str, hyps: Sequence[Hypothesis[Sort]], *, ctx: str) -> RuleSig:
        sig = self.sigs.get(label)
        if sig is None:
            raise PreludeTypingError(f"{ctx}: unknown rule label {label!r}")

        if len(hyps) != sig.arity:
            raise PreludeTypingError(
                f"{ctx}: rule {label!r} expects {sig.arity} hyps, got {len(hyps)}"
            )

        for i, (h, expected) in enumerate(zip(hyps, sig.in_sorts, strict=True)):
            if h.body.sort != expected:
                raise PreludeTypingError(
                    f"{ctx}: rule {label!r} arg#{i} expects {expected!r}, got {h.body.sort!r}"
                    f" (hyp={h.label!r})"
                )
        return sig


class HasRuleSig(Protocol):
    label: str
    sig: RuleSig


# -----------------------------------------------------------------------------
# Public exports
# -----------------------------------------------------------------------------

__all__ = [
    # Core objects
    "Hypothesis",
    "HypWff",
    "HypClass",
    "HypSetVar",
    "Context",
    # Errors
    "PreludeTypingError",
    "PreludeShapeError",
    # Sort checks
    "require_sort",
    "require_hyp_sort",
    # Signatures
    "RuleSig",
    "RuleApp",
]
