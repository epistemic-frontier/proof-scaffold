from __future__ import annotations

import pytest

from skfd.authoring.emit import emit_lowered_lemmas
from skfd.authoring.formula import Wff
from skfd.builder import MMBuilder
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner


class DummyBuiltins:
    lp = 1
    rp = 2
    imp = 3
    neg = 4
    and_ = 5


class DummyProvider:
    def __init__(self, interner: SymbolInterner) -> None:
        self.interner = interner
        self.builtins = DummyBuiltins()

    def compile_axioms(self):
        return {}


class Step:
    def __init__(self, label: str, wff: Wff, op: str, args=(), ref=None):
        self.label = label
        self.wff = wff
        self.op = op
        self.args = list(args)
        self.ref = ref


class Lemma:
    def __init__(self, name: str, statement: Wff, steps):
        self.name = name
        self.statement = statement
        self.steps = steps


def _mk_wff(interner: SymbolInterner) -> Wff:
    return Wff(
        "wff",
        (
            interner.intern(
                origin_module_id="t", local_name="ph", kind="Var", origin_ref=None
            ),
        ),
    )


def _mk_provider_with_token_builtins(interner: SymbolInterner):
    class Builtins:
        def __init__(self, *, lp: int, rp: int, imp: int, neg: int, and_: int) -> None:
            self.lp = lp
            self.rp = rp
            self.imp = imp
            self.neg = neg
            self.and_ = and_

    class Provider:
        def __init__(self, interner: SymbolInterner, builtins: Builtins) -> None:
            self.interner = interner
            self.builtins = builtins

        def compile_axioms(self):
            return {}

    lp = interner.intern(origin_module_id="t", local_name="lp", kind="Const", origin_ref=None)
    rp = interner.intern(origin_module_id="t", local_name="rp", kind="Const", origin_ref=None)
    imp = interner.intern(origin_module_id="t", local_name="imp", kind="Const", origin_ref=None)
    neg = interner.intern(origin_module_id="t", local_name="neg", kind="Const", origin_ref=None)
    and_ = interner.intern(origin_module_id="t", local_name="and", kind="Const", origin_ref=None)

    return Provider(interner, Builtins(lp=lp, rp=rp, imp=imp, neg=neg, and_=and_))


def test_emit_lowered_lemmas_missing_steps_raises() -> None:
    interner = SymbolInterner()
    w = _mk_wff(interner)
    mm = MMBuilder(interner=interner, origin_table=OriginTable(), module_id="t")
    mm.c("wff")

    lemma = Lemma("L1", w, [])
    with pytest.raises(ValueError):
        emit_lowered_lemmas(mm, DummyProvider(interner), [lemma])


def test_emit_lowered_lemmas_missing_ref_raises() -> None:
    interner = SymbolInterner()
    w = _mk_wff(interner)
    mm = MMBuilder(interner=interner, origin_table=OriginTable(), module_id="t")
    mm.c("wff")
    mm.v("v0")
    mm.f("w_v0", "wff", "v0")

    lemma = Lemma("L1", w, [Step("s1", w, op="ref", ref=None)])
    with pytest.raises(ValueError):
        emit_lowered_lemmas(mm, DummyProvider(interner), [lemma])


def test_emit_lowered_lemmas_missing_builtins() -> None:
    interner = SymbolInterner()
    w = _mk_wff(interner)
    mm = MMBuilder(interner=interner, origin_table=OriginTable(), module_id="t")
    mm.c("wff")
    mm.v("v0")
    mm.f("w_v0", "wff", "v0")

    class ProviderNoBuiltins:
        def __init__(self, interner: SymbolInterner) -> None:
            self.interner = interner

        def compile_axioms(self):
            return {}

    lemma = Lemma("L1", w, [Step("s1", w, op="ref", ref="w_v0")])
    with pytest.raises(ValueError):
        emit_lowered_lemmas(mm, ProviderNoBuiltins(interner), [lemma])


def test_emit_lowered_lemmas_ref_step_success() -> None:
    interner = SymbolInterner()
    w = _mk_wff(interner)
    mm = MMBuilder(interner=interner, origin_table=OriginTable(), module_id="t")
    mm.c("wff")
    mm.v("v0")
    mm.f("w_v0", "wff", "v0")
    mm.a("ax", "wff", "v0")

    lemma = Lemma("L1", w, [Step("s1", w, op="ref", ref="ax")])
    emit_lowered_lemmas(mm, _mk_provider_with_token_builtins(interner), [lemma])
    out = mm.render()
    assert "L1 $p" in out
    assert "ax" in out


def test_emit_lowered_lemmas_mp_success() -> None:
    interner = SymbolInterner()
    w = _mk_wff(interner)
    provider = _mk_provider_with_token_builtins(interner)
    lp = provider.builtins.lp
    rp = provider.builtins.rp
    imp = provider.builtins.imp
    w_imp = Wff("wff", (lp, w.tokens[0], imp, w.tokens[0], rp))

    mm = MMBuilder(interner=interner, origin_table=OriginTable(), module_id="t")
    mm.c("wff")
    mm.v("v0")
    mm.f("w_v0", "wff", "v0")
    mm.a("mp", "wff", "v0")

    steps = [
        Step("s1", w, op="hyp"),
        Step("s2", w_imp, op="hyp"),
        Step("s3", w, op="mp", args=("s1", "s2")),
    ]
    lemma = Lemma("L1", w, steps)
    emit_lowered_lemmas(mm, provider, [lemma])
    out = mm.render()
    assert "s1 $e" in out
    assert "s2 $e" in out
    assert "L1 $p" in out


def test_emit_lowered_lemmas_mp_wrong_arity_raises() -> None:
    interner = SymbolInterner()
    w = _mk_wff(interner)
    provider = _mk_provider_with_token_builtins(interner)

    mm = MMBuilder(interner=interner, origin_table=OriginTable(), module_id="t")
    mm.c("wff")
    mm.v("v0")
    mm.f("w_v0", "wff", "v0")
    mm.a("mp", "wff", "v0")

    lemma = Lemma("L1", w, [Step("s1", w, op="mp", args=("x",))])
    with pytest.raises(ValueError):
        emit_lowered_lemmas(mm, provider, [lemma])


def test_emit_lowered_lemmas_mp_missing_arg_step_raises() -> None:
    interner = SymbolInterner()
    w = _mk_wff(interner)
    provider = _mk_provider_with_token_builtins(interner)
    lp = provider.builtins.lp
    rp = provider.builtins.rp
    imp = provider.builtins.imp
    w_imp = Wff("wff", (lp, w.tokens[0], imp, w.tokens[0], rp))

    mm = MMBuilder(interner=interner, origin_table=OriginTable(), module_id="t")
    mm.c("wff")
    mm.v("v0")
    mm.f("w_v0", "wff", "v0")
    mm.a("mp", "wff", "v0")

    steps = [
        Step("s2", w_imp, op="hyp"),
        Step("s3", w, op="mp", args=("missing", "s2")),
    ]
    lemma = Lemma("L1", w, steps)
    with pytest.raises(ValueError):
        emit_lowered_lemmas(mm, provider, [lemma])


def test_emit_lowered_lemmas_mp_minor_not_implication_raises() -> None:
    interner = SymbolInterner()
    w = _mk_wff(interner)
    provider = _mk_provider_with_token_builtins(interner)

    mm = MMBuilder(interner=interner, origin_table=OriginTable(), module_id="t")
    mm.c("wff")
    mm.v("v0")
    mm.f("w_v0", "wff", "v0")
    mm.a("mp", "wff", "v0")

    steps = [
        Step("s1", w, op="hyp"),
        Step("s2", w, op="hyp"),
        Step("s3", w, op="mp", args=("s1", "s2")),
    ]
    lemma = Lemma("L1", w, steps)
    with pytest.raises(ValueError):
        emit_lowered_lemmas(mm, provider, [lemma])


def test_emit_lowered_lemmas_mp_antecedent_mismatch_raises() -> None:
    interner = SymbolInterner()
    ph = _mk_wff(interner)
    ps = Wff(
        "wff",
        (
            interner.intern(
                origin_module_id="t", local_name="ps", kind="Var", origin_ref=None
            ),
        ),
    )
    provider = _mk_provider_with_token_builtins(interner)
    lp = provider.builtins.lp
    rp = provider.builtins.rp
    imp = provider.builtins.imp
    w_imp = Wff("wff", (lp, ph.tokens[0], imp, ph.tokens[0], rp))

    mm = MMBuilder(interner=interner, origin_table=OriginTable(), module_id="t")
    mm.c("wff")
    mm.v("v0", "v1")
    mm.f("w_v0", "wff", "v0")
    mm.f("w_v1", "wff", "v1")
    mm.a("mp", "wff", "v0")

    steps = [
        Step("s1", ps, op="hyp"),
        Step("s2", w_imp, op="hyp"),
        Step("s3", ph, op="mp", args=("s1", "s2")),
    ]
    lemma = Lemma("L1", ph, steps)
    with pytest.raises(ValueError):
        emit_lowered_lemmas(mm, provider, [lemma])


def test_emit_lowered_lemmas_cycle_detected_raises() -> None:
    interner = SymbolInterner()
    w = _mk_wff(interner)
    provider = _mk_provider_with_token_builtins(interner)
    lp = provider.builtins.lp
    rp = provider.builtins.rp
    imp = provider.builtins.imp
    w_imp = Wff("wff", (lp, w.tokens[0], imp, w.tokens[0], rp))

    mm = MMBuilder(interner=interner, origin_table=OriginTable(), module_id="t")
    mm.c("wff")
    mm.v("v0")
    mm.f("w_v0", "wff", "v0")
    mm.a("mp", "wff", "v0")

    steps = [
        Step("s2", w_imp, op="hyp"),
        Step("s1", w, op="mp", args=("s1", "s2")),
    ]
    lemma = Lemma("L1", w, steps)
    with pytest.raises(ValueError):
        emit_lowered_lemmas(mm, provider, [lemma])


def test_emit_lowered_lemmas_wff_proof_unsupported_shape_raises() -> None:
    interner = SymbolInterner()
    w = _mk_wff(interner)
    provider = _mk_provider_with_token_builtins(interner)
    lp = provider.builtins.lp
    rp = provider.builtins.rp
    imp = provider.builtins.imp
    w_paren = Wff("wff", (lp, w.tokens[0], rp))
    w_imp_bad = Wff("wff", (lp, w.tokens[0], imp, w_paren.tokens[0], rp))

    mm = MMBuilder(interner=interner, origin_table=OriginTable(), module_id="t")
    mm.c("wff")
    mm.v("v0")
    mm.f("w_v0", "wff", "v0")
    mm.a("mp", "wff", "v0")

    steps = [
        Step("s1", w, op="hyp"),
        Step("s2", w_imp_bad, op="hyp"),
        Step("s3", w_paren, op="mp", args=("s1", "s2")),
    ]
    lemma = Lemma("L1", w_paren, steps)
    with pytest.raises(ValueError):
        emit_lowered_lemmas(mm, provider, [lemma])
