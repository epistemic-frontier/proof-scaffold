from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pytest

from skfd.authoring.dsl import Expr
from skfd.authoring.formula import Wff, wff_atom
from skfd.authoring.typing import HypothesisAny
from skfd.core.disjoint import DisjointSpecError
from skfd.core.symbols import SymbolInterner
from skfd.proof import ProofBuilder


@dataclass(frozen=True)
class _DummySystem:
    interner: SymbolInterner

    def compile(self, _expr: Expr, *, ctx: str = "compile") -> Wff:
        tok = self.interner.intern(
            origin_module_id="test",
            local_name=f"v_{ctx}",
            kind="Var",
            origin_ref=-1,
        )
        return wff_atom(tok)

    def compile_axioms(self) -> Mapping[str, Wff]:
        return {}

    def apply(self, rule: str, hyps: Sequence[HypothesisAny], *, ctx: str) -> Wff:
        assert rule
        assert ctx
        assert len(hyps) >= 1
        tok = self.interner.intern(
            origin_module_id="test",
            local_name=f"r_{rule}_{ctx}",
            kind="Var",
            origin_ref=-1,
        )
        return wff_atom(tok)


def test_proof_builder_apply_records_deps() -> None:
    sys = _DummySystem(interner=SymbolInterner())
    pb = ProofBuilder(sys, "demo")

    h1 = pb.hyp("h1", "ph")
    s1 = pb.ref("s1", "ps", ref="A1", note="a1")
    s2 = pb.apply("s2", "mp", h1, s1, note="mp")

    proof = pb.build(s2)

    assert proof.name == "demo"
    assert proof.statement == s2
    assert [s.label for s in proof.steps] == ["h1", "s1", "s2"]
    assert proof.steps[0].op == "hyp"
    assert proof.steps[1].op == "ref" and proof.steps[1].ref == "A1"
    assert proof.steps[2].op == "apply" and proof.steps[2].ref == "mp"
    assert proof.steps[2].args == ("h1", "s1")


def test_proof_builder_mp_is_apply_mp() -> None:
    sys = _DummySystem(interner=SymbolInterner())
    pb = ProofBuilder(sys, "demo")
    a = pb.hyp("a", "ph")
    b = pb.hyp("b", "ps")
    _ = pb.mp("c", a, b)

    assert pb.steps[-1].op == "apply"
    assert pb.steps[-1].ref == "mp"


def test_proof_builder_ref_hyp_args_are_recorded() -> None:
    sys = _DummySystem(interner=SymbolInterner())
    pb = ProofBuilder(sys, "demo")
    h = pb.hyp("h", "ph")
    _ = pb.ref("s", "ps", h, ref="T", note="t")

    assert pb.steps[-1].op == "ref"
    assert pb.steps[-1].ref == "T"
    assert pb.steps[-1].args == ("h",)


def test_proof_builder_ref_rejects_foreign_args() -> None:
    sys = _DummySystem(interner=SymbolInterner())
    pb1 = ProofBuilder(sys, "p1")
    pb2 = ProofBuilder(sys, "p2")
    foreign = pb2.hyp("h", "ph")

    try:
        pb1.ref("s", "ps", foreign, ref="T")
    except ValueError as e:
        assert "ref args must be steps created by this ProofBuilder" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_proof_builder_records_canonical_active_dv_pairs() -> None:
    sys = _DummySystem(interner=SymbolInterner())
    x = sys.interner.intern(
        origin_module_id="test", local_name="x", kind="Var", origin_ref=-1
    )
    y = sys.interner.intern(
        origin_module_id="test", local_name="y", kind="Var", origin_ref=-1
    )
    pb = ProofBuilder(sys, "dv-demo")

    pb.disjoint(y, x)
    pb.disjoint(x, y)
    proof = pb.build(wff_atom(x))

    assert proof.active_dv_pairs == ((x, y),)

    with pytest.raises(DisjointSpecError, match="itself"):
        pb.disjoint(x, x)
