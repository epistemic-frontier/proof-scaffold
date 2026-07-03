"""Proof IR: Step, Proof, and ProofBuilder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from skfd.authoring.formula import Wff
from skfd.authoring.parsing import wff
from skfd.authoring.typing import Hypothesis, HypothesisAny, PreludeTypingError

from .core import SystemCore


@dataclass(frozen=True)
class Step:
    label: str
    wff: Wff
    note: str
    op: str = "raw"
    args: tuple[str, ...] = ()
    ref: str | None = None


@dataclass(frozen=True)
class Proof:
    name: str
    statement: Wff
    steps: tuple[Step, ...]


class ProofBuilder:
    """Build a Metamath proof step-by-step.

    Uses a System for formula compilation and an optional
    SignatureCache for automatic hypothesis resolution.
    """

    # -- Class-level default signature cache (set once by script_runner) --
    _default_signature_cache: Any = None

    def __init__(self, sys: SystemCore, name: str):
        self.sys: SystemCore = sys
        self.name: str = name
        self.steps: list[Step] = []
        self._wff_to_label: dict[int, str] = {}
        self._signature_cache: Any = ProofBuilder._default_signature_cache
        self._unify_ctx: Any = None
        # Build UnifyCtx from system if a cache is available
        if self._signature_cache is not None:
            self._init_unify_ctx()

    def set_signature_cache(self, cache: Any) -> None:
        """Inject a SignatureCache for automatic hypothesis matching."""
        self._signature_cache = cache
        self._init_unify_ctx()

    def _init_unify_ctx(self) -> None:
        """Build a UnifyCtx from the system's builtins + symbol table."""
        b = getattr(self.sys, "builtins", None)
        if b is not None:
            from skfd.proof.unify import UnifyCtx

            symtab = self.sys.interner.symbol_table()
            binops = [b.imp, b.and_]
            or_ = getattr(b, "or_", None)
            if or_ is not None:
                binops.append(or_)
            self._unify_ctx = UnifyCtx(
                symtab=symtab,
                neg=b.neg,
                imp=b.imp,
                and_=b.and_,
                lp=b.lp,
                rp=b.rp,
                binops=binops,
            )

    def _remember(self, label: str, stmt: Wff) -> None:
        self._wff_to_label[id(stmt)] = label

    def _compile_str(self, label: str, expr_str: str) -> Wff:
        try:
            expr = wff(expr_str)
        except PreludeTypingError as e:
            raise PreludeTypingError(
                f"{label}: parse failed for {expr_str!r}\n{e}"
            ) from e
        return self.sys.compile(expr, ctx=label)

    def hyp(self, label: str, expr_str: str) -> Wff:
        stmt = self._compile_str(label, expr_str)
        self.steps.append(Step(label, stmt, "Hypothesis", op="hyp"))
        self._remember(label, stmt)
        return stmt

    def ref(
        self, label: str, expr_str: str, *hyp_args: Wff, ref: str, note: str = ""
    ) -> Wff:
        stmt = self._compile_str(label, expr_str)

        # ── Auto-match hypotheses if none were provided ──
        if not hyp_args and self._signature_cache is not None:
            sig = self._signature_cache.get(ref, None, self.sys)
            if sig is not None and sig.hyps:
                hyp_args = self._auto_match(sig, stmt)
                # If auto-match fails, hyp_args stays empty and
                # the emit phase will report the mismatch clearly.

        arg_labels: list[str] = []
        for w in hyp_args:
            w_label = self._wff_to_label.get(id(w))
            if w_label is None:
                raise ValueError(
                    f"{label}: ref args must be steps created by this ProofBuilder"
                )
            arg_labels.append(w_label)
        self.steps.append(
            Step(label, stmt, note, op="ref", ref=ref, args=tuple(arg_labels))
        )
        self._remember(label, stmt)
        return stmt

    def _auto_match(self, sig: Any, target_stmt: Wff) -> tuple[Wff, ...]:
        """Try to match a lemma's hypotheses against existing proof steps.

        Returns a tuple of Wff objects (one per hypothesis) on success,
        or an empty tuple on failure.
        """
        from skfd.proof.signature import match_hyps

        # Build id→(label, wff) mapping
        existing: dict[int, tuple[str, Wff]] = {}
        for w_id, label in self._wff_to_label.items():
            # Find the Wff object that has this id
            for step in self.steps:
                if step.label == label and id(step.wff) == w_id:
                    existing[w_id] = (label, step.wff)
                    break

        matched_labels, _subst = match_hyps(self._unify_ctx, sig, target_stmt, existing)
        if matched_labels is None:
            return ()

        # Map labels back to Wff objects
        label_to_wff: dict[str, Wff] = {}
        for step in self.steps:
            label_to_wff[step.label] = step.wff

        result: list[Wff] = []
        for ml in matched_labels:
            w = label_to_wff.get(ml)
            if w is None:
                return ()
            result.append(w)
        return tuple(result)

    def raw(self, label: str, expr_str: str, *, note: str = "") -> Wff:
        stmt = self._compile_str(label, expr_str)
        self.steps.append(Step(label, stmt, note, op="raw", ref=None))
        self._remember(label, stmt)
        return stmt

    def apply(self, label: str, rule: str, *args: Wff, note: str = "") -> Wff:
        hyps: list[HypothesisAny] = [
            cast(HypothesisAny, Hypothesis(f"h_{label}_{i}", w))
            for i, w in enumerate(args)
        ]
        res = self.sys.apply(rule, hyps, ctx=label)
        arg_labels: list[str] = []
        for w in args:
            w_label = self._wff_to_label.get(id(w))
            if w_label is None:
                raise ValueError(
                    f"{label}: apply args must be steps created by this ProofBuilder"
                )
            arg_labels.append(w_label)
        self.steps.append(
            Step(label, res, note, op="apply", args=tuple(arg_labels), ref=rule)
        )
        self._remember(label, res)
        return res

    def mp(self, label: str, major: Wff, minor: Wff, note: str = "mp") -> Wff:
        return self.apply(label, "mp", major, minor, note=note)

    def build(self, statement: Wff) -> Proof:
        return Proof(name=self.name, statement=statement, steps=tuple(self.steps))
