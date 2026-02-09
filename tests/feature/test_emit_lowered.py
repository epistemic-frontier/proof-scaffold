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
