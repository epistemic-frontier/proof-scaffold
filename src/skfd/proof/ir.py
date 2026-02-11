from __future__ import annotations

from dataclasses import dataclass
from typing import cast

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
    def __init__(self, sys: SystemCore, name: str):
        self.sys = sys
        self.name = name
        self.steps: list[Step] = []
        self._wff_to_label: dict[int, str] = {}

    def _remember(self, label: str, stmt: Wff) -> None:
        self._wff_to_label[id(stmt)] = label

    def _compile_str(self, label: str, expr_str: str) -> Wff:
        try:
            expr = wff(expr_str)
        except PreludeTypingError as e:
            raise PreludeTypingError(f"{label}: parse failed for {expr_str!r}\n{e}") from e
        return self.sys.compile(expr, ctx=label)

    def hyp(self, label: str, expr_str: str) -> Wff:
        stmt = self._compile_str(label, expr_str)
        self.steps.append(Step(label, stmt, "Hypothesis", op="hyp"))
        self._remember(label, stmt)
        return stmt

    def ref(self, label: str, expr_str: str, *hyp_args: Wff, ref: str, note: str = "") -> Wff:
        stmt = self._compile_str(label, expr_str)
        arg_labels: list[str] = []
        for w in hyp_args:
            w_label = self._wff_to_label.get(id(w))
            if w_label is None:
                raise ValueError(f"{label}: ref args must be steps created by this ProofBuilder")
            arg_labels.append(w_label)
        self.steps.append(
            Step(label, stmt, note, op="ref", ref=ref, args=tuple(arg_labels))
        )
        self._remember(label, stmt)
        return stmt

    def raw(self, label: str, expr_str: str, *, note: str = "") -> Wff:
        stmt = self._compile_str(label, expr_str)
        self.steps.append(Step(label, stmt, note, op="raw", ref=None))
        self._remember(label, stmt)
        return stmt

    def apply(self, label: str, rule: str, *args: Wff, note: str = "") -> Wff:
        hyps: list[HypothesisAny] = [
            cast(HypothesisAny, Hypothesis(f"h_{label}_{i}", w)) for i, w in enumerate(args)
        ]
        res = self.sys.apply(rule, hyps, ctx=label)
        arg_labels: list[str] = []
        for w in args:
            w_label = self._wff_to_label.get(id(w))
            if w_label is None:
                raise ValueError(f"{label}: apply args must be steps created by this ProofBuilder")
            arg_labels.append(w_label)
        self.steps.append(Step(label, res, note, op="apply", args=tuple(arg_labels), ref=rule))
        self._remember(label, res)
        return res

    def mp(self, label: str, major: Wff, minor: Wff, note: str = "mp") -> Wff:
        return self.apply(label, "mp", major, minor, note=note)

    def build(self, statement: Wff) -> Proof:
        return Proof(name=self.name, statement=statement, steps=tuple(self.steps))
