# logic/propositional/hilbert/_syntactic.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Mapping, TypeAlias

from prelude.formula import Builtins, Wff, imp, try_parse_imp, wn, wa
from prelude.rules import RuleEntry, build_catalog, rules_view
from prelude.typing import (
    HypWff,
    PreludeShapeError,
    PreludeTypingError,
    RuleSig,
    WFF,
    require_hyp_sort,
)

RuleFn: TypeAlias = Callable[..., object]


# -----------------------------------------------------------------------------
# Concrete rules / axioms (token-level)
#
# IMPORTANT:
# - Each rule carries its own signature via `sig: RuleSig`.
# - The logic system collects signatures from rule objects at construction time.
# - This avoids a separate hand-maintained signatures table.
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Wi:
    """Syntactic axiom: from wff φ, wff ψ, construct wff (φ -> ψ)."""
    label: str = "wi"
    sig: RuleSig = RuleSig(in_sorts=(WFF, WFF), out_sort=WFF)
    b: Builtins | None = None

    def __call__(self, hphi: HypWff, hpsi: HypWff) -> Wff:
        if self.b is None:
            raise PreludeTypingError("wi: requires Builtins (Wi(b=...))")

        # Defensive sort checks (builder may already have checked via RuleApp).
        require_hyp_sort(hphi, "wff", ctx=self.label)
        require_hyp_sort(hpsi, "wff", ctx=self.label)

        return imp(self.b, hphi.body, hpsi.body)


@dataclass(frozen=True)
class Mp:
    """Inference rule: Modus Ponens."""
    label: str = "mp"
    sig: RuleSig = RuleSig(in_sorts=(WFF, WFF), out_sort=WFF)
    b: Builtins | None = None

    def __call__(self, hyp_phi: HypWff, hyp_imp: HypWff) -> Wff:
        if self.b is None:
            raise PreludeTypingError("mp: requires Builtins (Mp(b=...))")

        require_hyp_sort(hyp_phi, "wff", ctx=self.label)
        require_hyp_sort(hyp_imp, "wff", ctx=self.label)

        shp = try_parse_imp(self.b, hyp_imp.body.tokens)
        if shp is None:
            raise PreludeShapeError(f"{self.label}: expected token shape '( phi -> psi )'")

        if hyp_phi.body.tokens != shp.phi:
            raise PreludeShapeError(f"{self.label}: antecedent mismatch (token-level)")

        return Wff("wff", shp.psi)


@dataclass(frozen=True)
class Wn:
    """Syntactic constructor: from wff φ, construct wff ~φ."""
    label: str = "wn"
    sig: RuleSig = RuleSig(in_sorts=(WFF,), out_sort=WFF)
    b: Builtins | None = None

    def __call__(self, hphi: HypWff) -> Wff:
        if self.b is None:
            raise PreludeTypingError("wn: requires Builtins (Wn(b=...))")
        require_hyp_sort(hphi, "wff", ctx=self.label)
        return wn(self.b, hphi.body)


@dataclass(frozen=True)
class Wa:
    """Syntactic constructor: from wff φ, wff ψ, construct wff (φ /\\ ψ)."""
    label: str = "wa"
    sig: RuleSig = RuleSig(in_sorts=(WFF, WFF), out_sort=WFF)
    b: Builtins | None = None

    def __call__(self, hphi: HypWff, hpsi: HypWff) -> Wff:
        if self.b is None:
            raise PreludeTypingError("wa: requires Builtins (Wa(b=...))")
        require_hyp_sort(hphi, "wff", ctx=self.label)
        require_hyp_sort(hpsi, "wff", ctx=self.label)
        return wa(self.b, hphi.body, hpsi.body)


# -----------------------------------------------------------------------------
# Rule bundle (main API)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class RuleBundle:
    """A bound rule set plus the signatures collected from rule objects."""
    rules: Mapping[str, RuleFn]
    sigs: Mapping[str, RuleSig]


def make_rules(b: Builtins) -> RuleBundle:
    """Create a Hilbert rule bundle with Builtins bound.

    Returns:
      RuleBundle:
        - rules: label -> callable
        - sigs: label -> RuleSig (collected from rule objects)
    """
    wi = Wi(b=b)
    mp = Mp(b=b)
    wn_ = Wn(b=b)
    wa_ = Wa(b=b)

    rules: Dict[str, RuleFn] = {
        wi.label: wi,
        mp.label: mp,
        wn_.label: wn_,
        wa_.label: wa_,
    }
    sigs: Dict[str, RuleSig] = {
        wi.label: wi.sig,
        mp.label: mp.sig,
        wn_.label: wn_.sig,
        wa_.label: wa_.sig,
    }
    return RuleBundle(rules=rules, sigs=sigs)


# -----------------------------------------------------------------------------
# Debug catalog (optional)
#
# Kept for introspection/testing. Normal users should use HilbertSystem only.
# -----------------------------------------------------------------------------

DEBUG_CATALOG: Dict[str, RuleEntry] = build_catalog(
    [
        RuleEntry(label="wi", kind="axiom", fn=Wi()),
        RuleEntry(label="mp", kind="rule", fn=Mp()),
        RuleEntry(label="wn", kind="axiom", fn=Wn()),
        RuleEntry(label="wa", kind="axiom", fn=Wa()),
    ]
)

DEBUG_RULES: Mapping[str, RuleFn] = rules_view(DEBUG_CATALOG)


__all__ = [
    # main API
    "RuleBundle",
    "make_rules",
    # debug-only (explicitly named)
    "DEBUG_CATALOG",
    "DEBUG_RULES",
]
