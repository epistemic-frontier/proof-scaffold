from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skfd.authoring.emit import emit_lowered_lemmas
from skfd.authoring.formula import Wff
from skfd.builder_v2 import MMBuilderV2
from skfd.core.lir import Theorem
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolId, SymbolInterner
from skfd.names import NameResolver


@dataclass(frozen=True)
class _Builtins:
    lp: SymbolId
    rp: SymbolId
    imp: SymbolId
    neg: SymbolId
    and_: SymbolId


@dataclass(frozen=True)
class _Step:
    label: str
    op: str
    args: tuple[str, ...]
    ref: str | None
    wff: Wff


@dataclass(frozen=True)
class _Lemma:
    name: str
    statement: Wff
    steps: tuple[_Step, ...]


class _Provider:
    def __init__(
        self, *, interner: SymbolInterner, builtins: Any, axioms: dict[str, Wff] | None = None
    ) -> None:
        self.interner = interner
        self.builtins = builtins
        self._axioms = axioms or {}

    def compile_axioms(self) -> dict[str, Wff]:
        return dict(self._axioms)


def test_emit_lowered_lemmas_v2_builds_theorem_proof_tokens() -> None:
    interner = SymbolInterner()
    origin_table = OriginTable()
    mm = MMBuilderV2(
        interner=interner,
        origin_table=origin_table,
        names=NameResolver(),
        unit_id="u",
        origin_module_id="m",
    )

    lp = interner.intern(origin_module_id="__b__", local_name="(", kind="Const", origin_ref=0)
    rp = interner.intern(origin_module_id="__b__", local_name=")", kind="Const", origin_ref=0)
    imp = interner.intern(origin_module_id="__b__", local_name="->", kind="Const", origin_ref=0)
    neg = interner.intern(origin_module_id="__b__", local_name="-.", kind="Const", origin_ref=0)
    and_ = interner.intern(origin_module_id="__b__", local_name="/\\", kind="Const", origin_ref=0)
    b = _Builtins(lp=lp, rp=rp, imp=imp, neg=neg, and_=and_)

    interner.intern(origin_module_id="dep", local_name="wi", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="wn", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="wa", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="mp", kind="Label", origin_ref=0)

    ph = interner.intern(origin_module_id="m", local_name="ph", kind="Var", origin_ref=0)
    phi = Wff("wff", (ph,))
    phi_imp_phi = Wff("wff", (lp, ph, imp, ph, rp))

    lemma_ref = _Lemma(
        name="Lref",
        statement=phi_imp_phi,
        steps=(
            _Step(label="s1", op="ref", args=(), ref="wi", wff=phi_imp_phi),
        ),
    )
    lemma_mp = _Lemma(
        name="Lmp",
        statement=phi,
        steps=(
            _Step(label="maj", op="hyp", args=(), ref=None, wff=phi),
            _Step(label="min", op="hyp", args=(), ref=None, wff=phi_imp_phi),
            _Step(label="s3", op="mp", args=("maj", "min"), ref=None, wff=phi),
        ),
    )

    provider = _Provider(interner=interner, builtins=b)
    emit_lowered_lemmas(mm, provider, [lemma_ref, lemma_mp], typecode="wff", label_ids=None)
    unit = mm.finish()
    assert any(isinstance(s, Theorem) for s in unit.lir_stmts)


def test_emit_lowered_lemmas_v2_ref_with_hyp_args_unifies_hyp_only_vars() -> None:
    interner = SymbolInterner()
    origin_table = OriginTable()
    mm = MMBuilderV2(
        interner=interner,
        origin_table=origin_table,
        names=NameResolver(),
        unit_id="u",
        origin_module_id="m",
    )

    lp = interner.intern(origin_module_id="__b__", local_name="(", kind="Const", origin_ref=0)
    rp = interner.intern(origin_module_id="__b__", local_name=")", kind="Const", origin_ref=0)
    imp = interner.intern(origin_module_id="__b__", local_name="->", kind="Const", origin_ref=0)
    neg = interner.intern(origin_module_id="__b__", local_name="-.", kind="Const", origin_ref=0)
    and_ = interner.intern(origin_module_id="__b__", local_name="/\\", kind="Const", origin_ref=0)
    b = _Builtins(lp=lp, rp=rp, imp=imp, neg=neg, and_=and_)

    interner.intern(origin_module_id="dep", local_name="wi", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="wn", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="wa", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="mp", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="id", kind="Label", origin_ref=0)

    ph = interner.intern(origin_module_id="m", local_name="ph", kind="Var", origin_ref=0)
    ps = interner.intern(origin_module_id="m", local_name="ps", kind="Var", origin_ref=0)
    ch = interner.intern(origin_module_id="m", local_name="ch", kind="Var", origin_ref=0)

    ph_imp_ps = Wff("wff", (lp, ph, imp, ps, rp))
    ph_imp_ph = Wff("wff", (lp, ph, imp, ph, rp))
    ph_imp_ch = Wff("wff", (lp, ph, imp, ch, rp))

    t2 = _Lemma(
        name="T2",
        statement=ph_imp_ph,
        steps=(
            _Step(label="T2.1", op="hyp", args=(), ref=None, wff=ph_imp_ps),
            _Step(label="res", op="ref", args=(), ref="id", wff=ph_imp_ph),
        ),
    )
    u = _Lemma(
        name="U",
        statement=ph_imp_ph,
        steps=(
            _Step(label="h", op="hyp", args=(), ref=None, wff=ph_imp_ch),
            _Step(label="res", op="ref", args=("h",), ref="T2", wff=ph_imp_ph),
        ),
    )

    provider = _Provider(interner=interner, builtins=b, axioms={"id": ph_imp_ph})
    emit_lowered_lemmas(mm, provider, [t2, u], typecode="wff", label_ids=None)
    unit = mm.finish()
    assert any(isinstance(s, Theorem) for s in unit.lir_stmts)


def test_emit_lowered_lemmas_v2_declares_floating_for_hyp_only_vars() -> None:
    from skfd.core.lir import FloatingHyp

    interner = SymbolInterner()
    origin_table = OriginTable()
    mm = MMBuilderV2(
        interner=interner,
        origin_table=origin_table,
        names=NameResolver(),
        unit_id="u",
        origin_module_id="m",
    )

    lp = interner.intern(origin_module_id="__b__", local_name="(", kind="Const", origin_ref=0)
    rp = interner.intern(origin_module_id="__b__", local_name=")", kind="Const", origin_ref=0)
    imp = interner.intern(origin_module_id="__b__", local_name="->", kind="Const", origin_ref=0)
    neg = interner.intern(origin_module_id="__b__", local_name="-.", kind="Const", origin_ref=0)
    and_ = interner.intern(origin_module_id="__b__", local_name="/\\", kind="Const", origin_ref=0)
    b = _Builtins(lp=lp, rp=rp, imp=imp, neg=neg, and_=and_)

    interner.intern(origin_module_id="dep", local_name="wi", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="wn", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="wa", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="mp", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="ax_ph", kind="Label", origin_ref=0)

    ph = interner.intern(origin_module_id="m", local_name="ph", kind="Var", origin_ref=0)
    th = interner.intern(origin_module_id="m", local_name="th", kind="Var", origin_ref=0)
    phi = Wff("wff", (ph,))
    theta = Wff("wff", (th,))

    lemma = _Lemma(
        name="L",
        statement=phi,
        steps=(
            _Step(label="L.1", op="hyp", args=(), ref=None, wff=theta),
            _Step(label="res", op="ref", args=(), ref="ax_ph", wff=phi),
        ),
    )

    provider = _Provider(interner=interner, builtins=b, axioms={"ax_ph": phi})
    emit_lowered_lemmas(mm, provider, [lemma], typecode="wff", label_ids=None)
    unit = mm.finish()
    assert any(isinstance(s, FloatingHyp) and s.var == th for s in unit.lir_stmts)
