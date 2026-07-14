from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from skfd.authoring.emit import emit_axioms, emit_lowered_lemmas
from skfd.authoring.formula import Wff
from skfd.builder_v2 import BuildConfig
from skfd.builder_v2 import MMBuilderV2
from skfd.core.diag import LinkerDiagError
from skfd.core.lir import Theorem
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolId, SymbolInterner
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver
from tests._sanity_utils import verify_expect_fail, verify_expect_ok


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
    active_dv_pairs: tuple[tuple[SymbolId, SymbolId], ...] = ()


class _Provider:
    def __init__(
        self,
        *,
        interner: SymbolInterner,
        builtins: Any,
        axioms: dict[str, Wff] | None = None,
    ) -> None:
        self.interner = interner
        self.builtins = builtins
        self._axioms = axioms or {}

    def compile_axioms(self) -> dict[str, Wff]:
        return dict(self._axioms)


def _write_linked_mm(tmp_path: Any, mm: MMBuilderV2, origin_table: OriginTable) -> Any:
    unit = mm.finish()
    res = LinkerV1.link(
        units=[unit],
        origin_table=origin_table,
        interner=mm.interner,
        conformance_level=1,
    )
    out = tmp_path / "out.mm"
    out.write_text(res.mm_text, encoding="utf-8")
    return out


def _setup_hilbert_core(
    *, floating_order: tuple[str, ...] = ("ph", "ps", "ch")
) -> tuple[
    MMBuilderV2,
    OriginTable,
    _Provider,
    dict[str, SymbolId],
    dict[SymbolId, SymbolId],
    dict[str, Wff],
]:
    interner = SymbolInterner()
    origin_table = OriginTable()
    mm = MMBuilderV2(
        interner=interner,
        origin_table=origin_table,
        names=NameResolver(),
        unit_id="u",
        origin_module_id="m",
    )

    wff = mm.sym.const("wff")
    provable = mm.sym.const("|-")

    lp = interner.intern(
        origin_module_id="__b__", local_name="(", kind="Const", origin_ref=0
    )
    rp = interner.intern(
        origin_module_id="__b__", local_name=")", kind="Const", origin_ref=0
    )
    imp = interner.intern(
        origin_module_id="__b__", local_name="->", kind="Const", origin_ref=0
    )
    neg = interner.intern(
        origin_module_id="__b__", local_name="-.", kind="Const", origin_ref=0
    )
    and_ = interner.intern(
        origin_module_id="__b__", local_name="/\\", kind="Const", origin_ref=0
    )
    b = _Builtins(lp=lp, rp=rp, imp=imp, neg=neg, and_=and_)

    ph = mm.sym.var("ph")
    ps = mm.sym.var("ps")
    ch = mm.sym.var("ch")
    vars_by_name = {"ph": ph, "ps": ps, "ch": ch}
    floating_by_var: dict[SymbolId, SymbolId] = {}
    for name in floating_order:
        var = vars_by_name[name]
        floating_by_var[var] = mm.f(mm.sym.label(f"w{name}"), tc=wff, var=var)

    wi = mm.a(mm.sym.label("wi"), tc=wff, expr=[lp, ph, imp, ps, rp])
    wn = mm.a(mm.sym.label("wn"), tc=wff, expr=[neg, ph])
    wa = mm.a(mm.sym.label("wa"), tc=wff, expr=[lp, ph, and_, ps, rp])

    a1 = Wff("wff", (lp, ph, imp, lp, ps, imp, ph, rp, rp))
    ph_imp_ps = Wff("wff", (lp, ph, imp, ps, rp))
    ph_imp_ch = Wff("wff", (lp, ph, imp, ch, rp))
    ph_imp_ph = Wff("wff", (lp, ph, imp, ph, rp))
    ps_imp_ph = Wff("wff", (lp, ps, imp, ph, rp))
    ph_imp_ph_imp_ph = Wff("wff", (lp, ph, imp, lp, *ph_imp_ph.tokens, imp, ph, rp, rp))
    a2 = Wff(
        "wff",
        (
            lp,
            lp,
            ph,
            imp,
            lp,
            ps,
            imp,
            ch,
            rp,
            rp,
            imp,
            lp,
            *ph_imp_ps.tokens,
            imp,
            *ph_imp_ch.tokens,
            rp,
            rp,
        ),
    )

    ax1 = mm.a(mm.sym.label("A1"), tc=provable, expr=a1.tokens)
    ax2 = mm.a(mm.sym.label("A2"), tc=provable, expr=a2.tokens)

    with mm.block():
        mm.e(mm.sym.label("ax-mp.1"), tc=provable, expr=[ph])
        mm.e(mm.sym.label("ax-mp.2"), tc=provable, expr=ph_imp_ps.tokens)
        ax_mp = mm.a(mm.sym.label("mp"), tc=provable, expr=[ps])

    label_ids = {
        "wi": wi,
        "wn": wn,
        "wa": wa,
        "mp": ax_mp,
        "A1": ax1,
        "A2": ax2,
    }
    wffs = {
        "ph": Wff("wff", (ph,)),
        "ps": Wff("wff", (ps,)),
        "ch": Wff("wff", (ch,)),
        "a1": a1,
        "a2": a2,
        "ph_imp_ps": ph_imp_ps,
        "ph_imp_ch": ph_imp_ch,
        "ph_imp_ph": ph_imp_ph,
        "ps_imp_ph": ps_imp_ph,
        "ph_imp_ph_imp_ph": ph_imp_ph_imp_ph,
    }
    provider = _Provider(interner=interner, builtins=b, axioms={"A1": a1, "A2": a2})
    return mm, origin_table, provider, label_ids, floating_by_var, wffs


def test_emit_lowered_lemmas_v2_mp_proofs_verify_with_mmverify(tmp_path: Any) -> None:
    mm, origin_table, provider, _, _, w = _setup_hilbert_core(
        floating_order=("ps", "ph", "ch")
    )
    b = provider.builtins
    ph = w["ph"].tokens[0]

    ph_imp_ph = w["ph_imp_ph"]
    a1_self = Wff("wff", (b.lp, ph, b.imp, *ph_imp_ph.tokens, b.rp))
    id_a2 = Wff(
        "wff",
        (
            b.lp,
            *w["ph_imp_ph_imp_ph"].tokens,
            b.imp,
            b.lp,
            *a1_self.tokens,
            b.imp,
            *ph_imp_ph.tokens,
            b.rp,
            b.rp,
        ),
    )

    a1i = _Lemma(
        name="a1i",
        statement=w["ps_imp_ph"],
        steps=(
            _Step(label="a1i.1", op="hyp", args=(), ref=None, wff=w["ph"]),
            _Step(label="s1", op="ref", args=(), ref="A1", wff=w["a1"]),
            _Step(
                label="res", op="mp", args=("a1i.1", "s1"), ref=None, wff=w["ps_imp_ph"]
            ),
        ),
    )
    identity = _Lemma(
        name="id",
        statement=ph_imp_ph,
        steps=(
            _Step(label="id.s1", op="ref", args=(), ref="A1", wff=a1_self),
            _Step(label="id.s2", op="ref", args=(), ref="A2", wff=id_a2),
            _Step(
                label="id.s3",
                op="ref",
                args=(),
                ref="A1",
                wff=w["ph_imp_ph_imp_ph"],
            ),
            _Step(
                label="id.s4",
                op="mp",
                args=("id.s3", "id.s2"),
                ref=None,
                wff=Wff("wff", (b.lp, *a1_self.tokens, b.imp, *ph_imp_ph.tokens, b.rp)),
            ),
            _Step(
                label="id.res",
                op="mp",
                args=("id.s1", "id.s4"),
                ref=None,
                wff=ph_imp_ph,
            ),
        ),
    )

    emit_lowered_lemmas(
        mm,
        provider,
        [a1i, identity],
        typecode="|-",
        wff_typecode="wff",
        label_ids=None,
        floating_by_var=None,
    )

    verify_expect_ok(_write_linked_mm(tmp_path, mm, origin_table))


def _emit_dv_reference_theorem(tmp_path: Any, *, theorem_has_active_dv: bool) -> Any:
    mm, origin_table, provider, _, _, w = _setup_hilbert_core()
    ph = w["ph"].tokens[0]
    ps = w["ps"].tokens[0]
    statement = w["ph_imp_ps"]
    dv_provider = _Provider(
        interner=mm.interner,
        builtins=provider.builtins,
        axioms={"dv-ax": statement},
    )
    emit_axioms(
        mm,
        dv_provider,
        typecode="|-",
        active_dv_pairs_by_label={"dv-ax": ((ph, ps),)},
    )
    theorem = _Lemma(
        name="dv-th",
        statement=statement,
        steps=(
            _Step(
                label="dv-th.res",
                op="ref",
                args=(),
                ref="dv-ax",
                wff=statement,
            ),
        ),
        active_dv_pairs=((ph, ps),) if theorem_has_active_dv else (),
    )
    emit_lowered_lemmas(
        mm,
        dv_provider,
        [theorem],
        typecode="|-",
        wff_typecode="wff",
    )
    return _write_linked_mm(tmp_path, mm, origin_table)


def test_emit_lowered_lemmas_emits_active_dv_needed_for_proof_replay(
    tmp_path: Any,
) -> None:
    verify_expect_ok(_emit_dv_reference_theorem(tmp_path, theorem_has_active_dv=True))


def test_emit_lowered_lemmas_missing_active_dv_fails_verification(
    tmp_path: Any,
) -> None:
    verify_expect_fail(
        _emit_dv_reference_theorem(tmp_path, theorem_has_active_dv=False)
    )


def test_emit_lowered_lemmas_rejects_map_that_clears_ir_dv() -> None:
    mm, _, provider, _, _, w = _setup_hilbert_core()
    ph = w["ph"].tokens[0]
    ps = w["ps"].tokens[0]
    theorem = _Lemma(
        name="dv-th",
        statement=w["ph_imp_ps"],
        steps=(),
        active_dv_pairs=((ph, ps),),
    )

    with pytest.raises(LinkerDiagError) as excinfo:
        emit_lowered_lemmas(
            mm,
            provider,
            [theorem],
            typecode="|-",
            active_dv_pairs_by_label={"dv-th": ()},
        )

    assert excinfo.value.diag.error_code == "E_CONFLICTING_DV_MAP"


def test_emit_lowered_lemmas_v2_ref_with_hyp_args_verifies_with_mmverify(
    tmp_path: Any,
) -> None:
    mm, origin_table, provider, _, _, w = _setup_hilbert_core(
        floating_order=("ps", "ph", "ch")
    )
    mm.a(mm.sym.label("id"), tc=mm.sym.const("|-"), expr=w["ph_imp_ph"].tokens)
    provider = _Provider(
        interner=mm.interner,
        builtins=provider.builtins,
        axioms={**provider.compile_axioms(), "id": w["ph_imp_ph"]},
    )
    t2 = _Lemma(
        name="T2",
        statement=w["ph_imp_ph"],
        steps=(
            _Step(label="T2.1", op="hyp", args=(), ref=None, wff=w["ph_imp_ps"]),
            _Step(label="T2.res", op="ref", args=(), ref="id", wff=w["ph_imp_ph"]),
        ),
    )
    u = _Lemma(
        name="U",
        statement=w["ph_imp_ph"],
        steps=(
            _Step(label="U.1", op="hyp", args=(), ref=None, wff=w["ph_imp_ch"]),
            _Step(label="U.res", op="ref", args=("U.1",), ref="T2", wff=w["ph_imp_ph"]),
        ),
    )

    emit_lowered_lemmas(
        mm,
        provider,
        [t2, u],
        typecode="|-",
        wff_typecode="wff",
        label_ids=None,
        floating_by_var=None,
    )

    verify_expect_ok(_write_linked_mm(tmp_path, mm, origin_table))


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

    lp = interner.intern(
        origin_module_id="__b__", local_name="(", kind="Const", origin_ref=0
    )
    rp = interner.intern(
        origin_module_id="__b__", local_name=")", kind="Const", origin_ref=0
    )
    imp = interner.intern(
        origin_module_id="__b__", local_name="->", kind="Const", origin_ref=0
    )
    neg = interner.intern(
        origin_module_id="__b__", local_name="-.", kind="Const", origin_ref=0
    )
    and_ = interner.intern(
        origin_module_id="__b__", local_name="/\\", kind="Const", origin_ref=0
    )
    b = _Builtins(lp=lp, rp=rp, imp=imp, neg=neg, and_=and_)

    interner.intern(origin_module_id="dep", local_name="wi", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="wn", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="wa", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="mp", kind="Label", origin_ref=0)

    ph = interner.intern(
        origin_module_id="m", local_name="ph", kind="Var", origin_ref=0
    )
    phi = Wff("wff", (ph,))
    phi_imp_phi = Wff("wff", (lp, ph, imp, ph, rp))

    lemma_ref = _Lemma(
        name="Lref",
        statement=phi_imp_phi,
        steps=(_Step(label="s1", op="ref", args=(), ref="wi", wff=phi_imp_phi),),
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
    emit_lowered_lemmas(
        mm, provider, [lemma_ref, lemma_mp], typecode="wff", label_ids=None
    )
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

    lp = interner.intern(
        origin_module_id="__b__", local_name="(", kind="Const", origin_ref=0
    )
    rp = interner.intern(
        origin_module_id="__b__", local_name=")", kind="Const", origin_ref=0
    )
    imp = interner.intern(
        origin_module_id="__b__", local_name="->", kind="Const", origin_ref=0
    )
    neg = interner.intern(
        origin_module_id="__b__", local_name="-.", kind="Const", origin_ref=0
    )
    and_ = interner.intern(
        origin_module_id="__b__", local_name="/\\", kind="Const", origin_ref=0
    )
    b = _Builtins(lp=lp, rp=rp, imp=imp, neg=neg, and_=and_)

    interner.intern(origin_module_id="dep", local_name="wi", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="wn", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="wa", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="mp", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="id", kind="Label", origin_ref=0)

    ph = interner.intern(
        origin_module_id="m", local_name="ph", kind="Var", origin_ref=0
    )
    ps = interner.intern(
        origin_module_id="m", local_name="ps", kind="Var", origin_ref=0
    )
    ch = interner.intern(
        origin_module_id="m", local_name="ch", kind="Var", origin_ref=0
    )

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

    lp = interner.intern(
        origin_module_id="__b__", local_name="(", kind="Const", origin_ref=0
    )
    rp = interner.intern(
        origin_module_id="__b__", local_name=")", kind="Const", origin_ref=0
    )
    imp = interner.intern(
        origin_module_id="__b__", local_name="->", kind="Const", origin_ref=0
    )
    neg = interner.intern(
        origin_module_id="__b__", local_name="-.", kind="Const", origin_ref=0
    )
    and_ = interner.intern(
        origin_module_id="__b__", local_name="/\\", kind="Const", origin_ref=0
    )
    b = _Builtins(lp=lp, rp=rp, imp=imp, neg=neg, and_=and_)

    interner.intern(origin_module_id="dep", local_name="wi", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="wn", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="wa", kind="Label", origin_ref=0)
    interner.intern(origin_module_id="dep", local_name="mp", kind="Label", origin_ref=0)
    interner.intern(
        origin_module_id="dep", local_name="ax_ph", kind="Label", origin_ref=0
    )

    ph = interner.intern(
        origin_module_id="m", local_name="ph", kind="Var", origin_ref=0
    )
    th = interner.intern(
        origin_module_id="m", local_name="th", kind="Var", origin_ref=0
    )
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


def test_emit_lowered_lemmas_requires_provider_builtins() -> None:
    mm, _, provider, _, _, w = _setup_hilbert_core()

    class ProviderWithoutBuiltins:
        interner = provider.interner

        def compile_axioms(self) -> dict[str, Wff]:
            return {}

    lemma = _Lemma(
        name="L",
        statement=w["ph"],
        steps=(_Step(label="res", op="ref", args=(), ref="A1", wff=w["a1"]),),
    )

    with pytest.raises(ValueError, match="missing .builtins"):
        emit_lowered_lemmas(mm, ProviderWithoutBuiltins(), [lemma], typecode="|-")


def test_emit_lowered_lemmas_rejects_interner_mismatch() -> None:
    mm, _, provider, _, _, w = _setup_hilbert_core()
    other = _Provider(interner=SymbolInterner(), builtins=provider.builtins)
    lemma = _Lemma(name="L", statement=w["ph"], steps=())

    with pytest.raises(LinkerDiagError) as excinfo:
        emit_lowered_lemmas(mm, other, [lemma], typecode="|-")
    assert excinfo.value.diag.error_code == "E_INTERNER_MISMATCH"


def test_emit_lowered_lemmas_warns_and_emits_axiom_for_raw_steps() -> None:
    mm, _, provider, _, _, w = _setup_hilbert_core()
    lemma = _Lemma(
        name="rawLemma",
        statement=w["ph"],
        steps=(_Step(label="raw", op="raw", args=(), ref=None, wff=w["ph"]),),
    )

    with pytest.warns(RuntimeWarning, match="emitting it as an axiom"):
        emit_lowered_lemmas(mm, provider, [lemma], typecode="|-")

    unit = mm.finish()
    labels = {
        mm.interner.symbol_table()[s.label].local_name
        for s in unit.lir_stmts
        if hasattr(s, "label")
    }
    assert "rawLemma" in labels


def test_emit_lowered_lemmas_forbids_raw_steps_at_strict_level() -> None:
    mm, _, provider, _, _, w = _setup_hilbert_core()
    mm.cfg = BuildConfig(forbid_raw=True)
    lemma = _Lemma(
        name="rawLemma",
        statement=w["ph"],
        steps=(_Step(label="raw", op="raw", args=(), ref=None, wff=w["ph"]),),
    )

    with pytest.raises(LinkerDiagError) as excinfo:
        emit_lowered_lemmas(mm, provider, [lemma], typecode="|-")
    assert excinfo.value.diag.error_code == "E_RAW_NOT_ALLOWED"


def test_emit_lowered_lemmas_rejects_self_and_circular_references() -> None:
    mm, _, provider, _, _, w = _setup_hilbert_core()
    self_ref = _Lemma(
        name="L",
        statement=w["ph"],
        steps=(_Step(label="s", op="ref", args=(), ref="L", wff=w["ph"]),),
    )
    with pytest.raises(LinkerDiagError) as excinfo:
        emit_lowered_lemmas(mm, provider, [self_ref], typecode="|-")
    assert excinfo.value.diag.error_code == "E_SELF_REFERENCE"

    mm2, _, provider2, _, _, w2 = _setup_hilbert_core()
    a = _Lemma(
        name="A",
        statement=w2["ph"],
        steps=(_Step(label="a", op="ref", args=(), ref="B", wff=w2["ph"]),),
    )
    b = _Lemma(
        name="B",
        statement=w2["ph"],
        steps=(_Step(label="b", op="ref", args=(), ref="A", wff=w2["ph"]),),
    )
    with pytest.raises(LinkerDiagError) as excinfo2:
        emit_lowered_lemmas(mm2, provider2, [a, b], typecode="|-")
    assert excinfo2.value.diag.error_code == "E_CIRCULAR_DEPENDENCY"


def test_emit_lowered_lemmas_rejects_empty_unknown_and_bad_mp_steps() -> None:
    mm, _, provider, _, _, w = _setup_hilbert_core()
    empty = _Lemma(name="empty", statement=w["ph"], steps=())
    with pytest.raises(ValueError, match="has no steps"):
        emit_lowered_lemmas(mm, provider, [empty], typecode="|-")

    mm2, _, provider2, _, _, w2 = _setup_hilbert_core()
    unknown = _Lemma(
        name="unknown",
        statement=w2["ph"],
        steps=(_Step(label="s", op="ref", args=(), ref="missing", wff=w2["ph"]),),
    )
    with pytest.raises(LinkerDiagError) as excinfo:
        emit_lowered_lemmas(mm2, provider2, [unknown], typecode="|-")
    assert excinfo.value.diag.error_code == "E_UNKNOWN_LABEL_NAME"

    mm3, _, provider3, _, _, w3 = _setup_hilbert_core()
    bad_mp = _Lemma(
        name="badmp",
        statement=w3["ph"],
        steps=(
            _Step(label="h", op="hyp", args=(), ref=None, wff=w3["ph"]),
            _Step(label="res", op="mp", args=("h",), ref=None, wff=w3["ph"]),
        ),
    )
    with pytest.raises(ValueError, match="mp expects 2 args"):
        emit_lowered_lemmas(mm3, provider3, [bad_mp], typecode="|-")


def test_emit_lowered_lemmas_reports_missing_explicit_floating_hyp() -> None:
    mm, _, provider, _, _, w = _setup_hilbert_core()
    lemma = _Lemma(
        name="L",
        statement=w["ph_imp_ph"],
        steps=(_Step(label="s", op="ref", args=(), ref="wi", wff=w["ph_imp_ph"]),),
    )

    with pytest.raises(LinkerDiagError) as excinfo:
        emit_lowered_lemmas(
            mm,
            provider,
            [lemma],
            typecode="|-",
            wff_typecode="wff",
            floating_by_var={},
        )
    assert excinfo.value.diag.error_code == "E_MISSING_FLOATING_HYP"
