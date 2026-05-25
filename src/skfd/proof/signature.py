"""Lemma signature introspection.

Extracts hypothesis templates and conclusion from a Proof object
so callers don't need to guess how many hyp_args to pass to lb.ref().
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from skfd.authoring.formula import Wff
from skfd.proof.unify import (
    UnifyCtx,
    _Ast,
    apply_subst,
    parse,
    to_tokens,
    unify_tokens,
)


# ── Signature data ─────────────────────────────────────────


@dataclass
class LemmaSignature:
    """The public signature of a lemma: name, hypotheses, conclusion."""

    name: str
    hyps: list[tuple[str, Wff]]  # [(label, formula)]
    concl: Wff

    @property
    def hyp_count(self) -> int:
        return len(self.hyps)

    @property
    def hyp_tokens(self) -> list[tuple[int, ...]]:
        """Hypothesis formulas as token tuples."""
        return [tuple(w.tokens) for _, w in self.hyps]

    @property
    def concl_tokens(self) -> tuple[int, ...]:
        """Conclusion formula as a token tuple."""
        return tuple(self.concl.tokens)

    def __repr__(self) -> str:
        hyps_str = ", ".join(f"{label}" for label, _ in self.hyps)
        return f"LemmaSignature({self.name}, hyps=[{hyps_str}], concl=...)"


# ── Extraction ─────────────────────────────────────────────


def extract_signature(lemma_fn: Callable[..., Any], sys: Any) -> LemmaSignature:
    """Execute a lemma function once and extract its signature."""
    p = lemma_fn(sys)
    hyps: list[tuple[str, Wff]] = []
    for s in p.steps:
        if getattr(s, "op", None) == "hyp":
            hyps.append((s.label, s.wff))
    return LemmaSignature(name=p.name, hyps=hyps, concl=p.statement)


# ── Hypothesis matching ───────────────────────────────────


def match_hyps(
    ctx: UnifyCtx,
    sig: LemmaSignature,
    target_stmt: Wff,
    existing_steps: Mapping[int, tuple[str, Wff]],
) -> tuple[tuple[str, ...] | None, dict[int, _Ast]]:
    """Try to match a lemma's hypotheses against existing proof steps.

    Returns:
        (hyp_labels, subst) on success, or (None, {}) on failure.
        hyp_labels: tuple of step labels matching each hypothesis.
        subst: the variable substitution from unifying concl with target_stmt.

    Algorithm:
      1. Unify sig.concl with target_stmt → subst
      2. Apply subst to each hyp → expected formula tokens
      3. Search existing_steps for steps whose formula tokens match
    """
    if not sig.hyps:
        return (), {}

    try:
        subst = unify_tokens(ctx, sig.concl_tokens, target_stmt.tokens)
    except ValueError:
        return None, {}

    matched_labels: list[str] = []
    for hyp_wff in sig.hyp_tokens:
        expected_ast = apply_subst(ctx, parse(ctx, hyp_wff), subst)
        expected_tokens = to_tokens(ctx, expected_ast)

        found: str | None = None
        for w_id, (step_label, step_wff) in existing_steps.items():
            if tuple(step_wff.tokens) == expected_tokens:
                found = step_label
                break

        if found is None:
            return None, {}
        matched_labels.append(found)

    return tuple(matched_labels), subst


# ── Signature cache ────────────────────────────────────────


class SignatureCache:
    """Memoised lemma signature lookup.

    Preload with a catalog (e.g. SETMM_TO_HILBERT_LEMMAS) once,
    then use get() for O(1) signature access.
    """

    def __init__(self) -> None:
        self._cache: dict[str, LemmaSignature] = {}

    def get(
        self, lemma_name: str, lemma_fn: Callable[..., Any] | None, sys: Any
    ) -> LemmaSignature | None:
        """Return cached signature, extracting if necessary."""
        if lemma_name in self._cache:
            return self._cache[lemma_name]
        if lemma_fn is not None:
            sig = extract_signature(lemma_fn, sys)
            self._cache[lemma_name] = sig
            return sig
        return None

    def preload(self, catalog: Mapping[str, Callable[..., Any]], sys: Any) -> None:
        """Extract and cache signatures for every entry in *catalog*."""
        for name, ctor in catalog.items():
            if name not in self._cache:
                try:
                    self._cache[name] = extract_signature(ctor, sys)
                except Exception:
                    # Some catalog entries may not be extractable
                    # (e.g. forward references); skip them.
                    pass

    def __contains__(self, lemma_name: str) -> bool:
        return lemma_name in self._cache

    def __len__(self) -> int:
        return len(self._cache)
