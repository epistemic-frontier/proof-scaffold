"""Regression tests for emitting/lowering beyond the ¬/→/∧ core.

Covers:
- ``skfd.proof.unify`` recognising an extra infix binary operator (∨) via the
  generic ``binops`` list.
- ternary conjunction/disjunction token shapes round-tripping distinctly from
  nested binary formulas.
- ``emit_lowered_lemmas`` building wff-construction proofs for a nullary
  constant (``F.`` -> ``wfal``), a biconditional (``<->`` -> ``wb``), and a
  disjunction (``\\/`` -> ``wo``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pytest

from skfd.authoring.emit import emit_lowered_lemmas
from skfd.authoring.formula import Wff
from skfd.authoring.dsl import App, Constructor, RequireRegistry, require
from skfd.authoring.parsing import wff as parse_wff
from skfd.authoring.typing import WFF
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolId, SymbolInterner
from skfd.linker.api import LinkerV1
from skfd.names import NameResolver
from skfd.proof.unify import UnifyCtx, apply_subst, parse, to_tokens, unify_tokens
from tests._sanity_utils import verify_expect_ok

from skfd.builder_v2 import MMBuilderV2  # isort: skip


@dataclass(frozen=True)
class _Builtins:
    lp: SymbolId
    rp: SymbolId
    imp: SymbolId
    neg: SymbolId
    and_: SymbolId
    iff: SymbolId
    or_: SymbolId
    fal: SymbolId
    cadd: SymbolId
    if_: SymbolId


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

    # Ternary syntax has two depth-zero operators inside one pair of parens.
    ternary_disj = (lp, ph, or_, ps, or_, ph, rp)
    assert to_tokens(ctx, parse(ctx, ternary_disj)) == ternary_disj
    ternary_conj = (lp, ph, and_, ps, and_, ph, rp)
    assert to_tokens(ctx, parse(ctx, ternary_conj)) == ternary_conj


def test_unifier_supports_delimited_substitution() -> None:
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
    imp, and_, neg = const("->"), const("/\\"), const("-.")
    sb_lb, sb_slash, sb_rb = const("["), const("/"), const("]")
    x, y, ph = var("x"), var("y"), var("ph")
    ctx = UnifyCtx(
        symtab=interner.symbol_table(),
        neg=neg,
        imp=imp,
        and_=and_,
        lp=lp,
        rp=rp,
        substitution=(sb_lb, sb_slash, sb_rb),
    )

    expression = (sb_lb, y, sb_slash, x, sb_rb, ph)
    assert to_tokens(ctx, parse(ctx, expression)) == expression


def test_unifier_handles_generic_formula_shapes_and_substitution() -> None:
    interner = SymbolInterner()

    def symbol(
        name: str, kind: Literal["Const", "Var", "Label"] = "Const"
    ) -> int:
        return interner.intern(
            origin_module_id="generic", local_name=name, kind=kind, origin_ref=0
        )

    lp, rp = symbol("("), symbol(")")
    imp, and_, neg = symbol("->"), symbol("/\\"), symbol("-.")
    forall, cadd, eq = symbol("A."), symbol("cadd"), symbol("=")
    sb_lb, sb_slash, sb_rb = symbol("["), symbol("/"), symbol("]")
    ph, ps, ch, x, y = (symbol(name, "Var") for name in ("ph", "ps", "ch", "x", "y"))
    ctx = UnifyCtx(
        symtab=interner.symbol_table(),
        neg=neg,
        imp=imp,
        and_=and_,
        lp=lp,
        rp=rp,
        bare_binops=[eq],
        prefix2=[forall],
        prefix3=[cadd],
        substitution=(sb_lb, sb_slash, sb_rb),
    )

    formulas = (
        (forall, x, neg, ph),
        (cadd, ph, (lp, ph, imp, ps, rp), neg, ch),
        (x, eq, y),
        (sb_lb, y, sb_slash, x, sb_rb, forall, x, ph),
    )
    flattened = (
        formulas[0],
        (cadd, ph, *formulas[1][2], neg, ch),
        formulas[2],
        formulas[3],
    )
    for tokens in flattened:
        ast = parse(ctx, tokens)
        assert to_tokens(ctx, ast) == tokens
        assert ast == parse(ctx, tokens)
        assert hash(ast) == hash(parse(ctx, tokens))

    targets = (
        (forall, x, neg, ps),
        (cadd, ps, lp, ps, imp, ch, rp, neg, ph),
        (x, eq, ch),
        (sb_lb, ch, sb_slash, y, sb_rb, forall, y, ps),
    )
    for template, target in zip(flattened, targets, strict=True):
        subst = unify_tokens(ctx, template, target)
        assert to_tokens(ctx, apply_subst(ctx, parse(ctx, template), subst)) == target

    # Reusing a metavariable enforces a consistent mathematical substitution.
    repeated = (lp, ph, and_, ph, and_, ph, rp)
    assert unify_tokens(ctx, repeated, (lp, ps, and_, ps, and_, ps, rp))[ph]
    with pytest.raises(ValueError, match="inconsistent substitution"):
        unify_tokens(ctx, repeated, (lp, ps, and_, ch, and_, ps, rp))
    with pytest.raises(ValueError, match="malformed binary prefix"):
        parse(ctx, (forall, x))
    with pytest.raises(ValueError, match="malformed ternary prefix"):
        parse(ctx, (cadd, ph, ps))


def test_authoring_parser_distinguishes_ternary_from_nested_binary() -> None:
    registry = RequireRegistry()
    binary = Constructor("op", 2)
    ternary = Constructor("op", 3)
    require(
        binary,
        in_sorts=(WFF, WFF),
        out_sort=WFF,
        registry=registry,
        precedence=20,
        assoc="left",
    )
    binary_spec = registry._by_name.pop("op")
    require(
        ternary,
        in_sorts=(WFF, WFF, WFF),
        out_sort=WFF,
        registry=registry,
        precedence=20,
        assoc="left",
    )
    registry._by_name["op"] = binary_spec

    flat = parse_wff("( ph op ps op ch )", registry)
    bare = parse_wff("ph op ps op ch", registry)
    nested = parse_wff("( ( ph op ps ) op ch )", registry)
    assert isinstance(flat, App) and flat.ctor is ternary
    assert isinstance(bare, App) and bare.ctor is ternary
    assert isinstance(nested, App) and nested.ctor is binary


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
    iff, or_ = const("<->"), const("\\/")
    fal = const("F.")  # nullary falsum constant
    cadd, if_ = const("cadd"), const("if-")
    b = _Builtins(
        lp=lp,
        rp=rp,
        imp=imp,
        neg=neg,
        and_=and_,
        iff=iff,
        or_=or_,
        fal=fal,
        cadd=cadd,
        if_=if_,
    )

    ph = mm.sym.var("ph")
    ch = mm.sym.var("ch")
    wph = mm.f(mm.sym.label("wph"), tc=wff, var=ph)
    mm.f(mm.sym.label("wch"), tc=wff, var=ch)
    floating_by_var: dict[SymbolId, SymbolId] = {ph: wph}

    # Syntax axioms the lowering will reference.
    mm.a(mm.sym.label("wi"), tc=wff, expr=[lp, ph, imp, mm.sym.var("ps"), rp])
    mm.a(mm.sym.label("wn"), tc=wff, expr=[neg, ph])
    mm.a(mm.sym.label("wb"), tc=wff, expr=[lp, ph, iff, mm.sym.var("ps"), rp])
    mm.a(mm.sym.label("wo"), tc=wff, expr=[lp, ph, or_, mm.sym.var("ps"), rp])
    mm.a(
        mm.sym.label("w3a"),
        tc=wff,
        expr=[lp, ph, and_, mm.sym.var("ps"), and_, ch, rp],
    )
    mm.a(
        mm.sym.label("w3o"),
        tc=wff,
        expr=[lp, ph, or_, mm.sym.var("ps"), or_, ch, rp],
    )
    mm.a(mm.sym.label("wcad"), tc=wff, expr=[cadd, ph, mm.sym.var("ps"), ch])
    mm.a(mm.sym.label("wif"), tc=wff, expr=[if_, ph, mm.sym.var("ps"), ch])
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
    biconditional = _Lemma(
        name="selfbi",
        statement=Wff("wff", (lp, ph, imp, lp, ph, iff, ph, rp, rp)),
        steps=(
            _Step(
                label="res",
                op="ref",
                args=(),
                ref="triv",
                wff=Wff("wff", (lp, ph, imp, lp, ph, iff, ph, rp, rp)),
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
    ternary_conj = _Lemma(
        name="self3conj",
        statement=Wff("wff", (lp, ph, imp, lp, ph, and_, ph, and_, ph, rp, rp)),
        steps=(
            _Step(
                label="res",
                op="ref",
                args=(),
                ref="triv",
                wff=Wff("wff", (lp, ph, imp, lp, ph, and_, ph, and_, ph, rp, rp)),
            ),
        ),
    )
    ternary_disj = _Lemma(
        name="self3disj",
        statement=Wff("wff", (lp, ph, imp, lp, ph, or_, ph, or_, ph, rp, rp)),
        steps=(
            _Step(
                label="res",
                op="ref",
                args=(),
                ref="triv",
                wff=Wff("wff", (lp, ph, imp, lp, ph, or_, ph, or_, ph, rp, rp)),
            ),
        ),
    )
    cadd_expr = _Lemma(
        name="selfcadd",
        statement=Wff("wff", (lp, ph, imp, cadd, ph, ph, ph, rp)),
        steps=(
            _Step(
                label="res",
                op="ref",
                args=(),
                ref="triv",
                wff=Wff("wff", (lp, ph, imp, cadd, ph, ph, ph, rp)),
            ),
        ),
    )
    if_expr = _Lemma(
        name="selfif",
        statement=Wff("wff", (lp, ph, imp, if_, ph, ph, ph, rp)),
        steps=(
            _Step(
                label="res",
                op="ref",
                args=(),
                ref="triv",
                wff=Wff("wff", (lp, ph, imp, if_, ph, ph, ph, rp)),
            ),
        ),
    )

    provider = _Provider(interner=interner, builtins=b, axioms={"triv": triv_stmt})
    emit_lowered_lemmas(
        mm,
        provider,
        [
            absurd,
            biconditional,
            disj,
            ternary_conj,
            ternary_disj,
            cadd_expr,
            if_expr,
        ],
        typecode=provable,
        wff_typecode=wff,
        label_ids=None,
        floating_by_var=floating_by_var,
    )

    verify_expect_ok(_write_linked_mm(tmp_path, mm, origin_table))
