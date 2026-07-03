"""Regression tests for emitting/lowering beyond the ¬/→/∧ core.

Covers:
- ``skfd.proof.unify`` recognising an extra infix binary operator (∨) via the
  generic ``binops`` list.
- ``emit_lowered_lemmas`` building wff-construction proofs for a nullary
  constant (``F.`` -> ``wfal``) and for a disjunction (``\\/`` -> ``wo``), which
  is what lets a downstream logic emit theorems such as ``pm2.21fal`` and any
  ∨-shaped statement obtained purely by substitution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skfd.authoring.emit import emit_lowered_lemmas
from skfd.authoring.formula import Wff
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolId, SymbolInterner
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver
from skfd.proof.unify import UnifyCtx, parse, to_tokens, unify_tokens
from tests._sanity_utils import verify_expect_ok

from skfd.builder_v2 import MMBuilderV2  # isort: skip


@dataclass(frozen=True)
class _Builtins:
    lp: SymbolId
    rp: SymbolId
    imp: SymbolId
    neg: SymbolId
    and_: SymbolId
    or_: SymbolId
    fal: SymbolId


class _Provider:
    def __init__(
        self, *, interner: SymbolInterner, builtins: Any, axioms: dict[str, Wff]
    ) -> None:
        self.interner = interner
        self.builtins = builtins
        self._axioms = axioms

    def compile_axioms(self) -> dict[str, Wff]:
        return dict(self._axioms)


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


def test_unify_recognises_extra_binop() -> None:
    interner = SymbolInterner()

    def const(name: str) -> int:
        return interner.intern(
            origin_module_id="b", local_name=name, kind="Const", origin_ref=0
        )

    def var(name: str) -> int:
        return interner.intern(
            origin_module_id="b", local_name=name, kind="Var", origin_ref=0
        )

    lp, rp = const("("), const(")")
    imp, and_, or_ = const("->"), const("/\\"), const("\\/")
    neg = const("-.")
    ph, ps = var("ph"), var("ps")

    ctx = UnifyCtx(
        symtab=interner.symbol_table(),
        neg=neg,
        imp=imp,
        and_=and_,
        lp=lp,
        rp=rp,
        binops=[imp, and_, or_],
    )

    # ( ph \/ ps ) parses as a binary node and round-trips through to_tokens.
    disj = (lp, ph, or_, ps, rp)
    assert to_tokens(ctx, parse(ctx, disj)) == disj

    # A variable template unifies against a disjunction target.
    subst = unify_tokens(ctx, (ph,), disj)
    assert to_tokens(ctx, subst[ph]) == disj


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


def test_emit_lowers_nullary_const_and_disjunction(tmp_path: Any) -> None:
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

    def const(name: str) -> SymbolId:
        return interner.intern(
            origin_module_id="__b__", local_name=name, kind="Const", origin_ref=0
        )

    lp, rp = const("("), const(")")
    imp, neg, and_ = const("->"), const("-."), const("/\\")
    or_ = const("\\/")
    fal = const("F.")  # nullary falsum constant
    b = _Builtins(lp=lp, rp=rp, imp=imp, neg=neg, and_=and_, or_=or_, fal=fal)

    ph = mm.sym.var("ph")
    ch = mm.sym.var("ch")
    wph = mm.f(mm.sym.label("wph"), tc=wff, var=ph)
    mm.f(mm.sym.label("wch"), tc=wff, var=ch)
    floating_by_var: dict[SymbolId, SymbolId] = {ph: wph}

    # Syntax axioms the lowering will reference.
    mm.a(mm.sym.label("wi"), tc=wff, expr=[lp, ph, imp, mm.sym.var("ps"), rp])
    mm.a(mm.sym.label("wn"), tc=wff, expr=[neg, ph])
    mm.a(mm.sym.label("wo"), tc=wff, expr=[lp, ph, or_, mm.sym.var("ps"), rp])
    mm.a(mm.sym.label("wfal"), tc=wff, expr=[fal])

    # A bare axiom whose consequent is a variable, so we can instantiate it with
    # a nullary constant or a disjunction purely by substitution.
    triv_stmt = Wff("wff", (lp, ph, imp, ch, rp))
    mm.a(mm.sym.label("triv"), tc=provable, expr=triv_stmt.tokens)

    absurd = _Lemma(
        name="absurd",
        statement=Wff("wff", (lp, ph, imp, fal, rp)),
        steps=(
            _Step(
                label="res",
                op="ref",
                args=(),
                ref="triv",
                wff=Wff("wff", (lp, ph, imp, fal, rp)),
            ),
        ),
    )
    disj = _Lemma(
        name="selfdisj",
        statement=Wff("wff", (lp, ph, imp, lp, ph, or_, ph, rp, rp)),
        steps=(
            _Step(
                label="res",
                op="ref",
                args=(),
                ref="triv",
                wff=Wff("wff", (lp, ph, imp, lp, ph, or_, ph, rp, rp)),
            ),
        ),
    )

    provider = _Provider(interner=interner, builtins=b, axioms={"triv": triv_stmt})
    emit_lowered_lemmas(
        mm,
        provider,
        [absurd, disj],
        typecode=provable,
        wff_typecode=wff,
        label_ids=None,
        floating_by_var=floating_by_var,
    )

    verify_expect_ok(_write_linked_mm(tmp_path, mm, origin_table))
