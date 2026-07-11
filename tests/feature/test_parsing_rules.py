from __future__ import annotations

import pytest

from skfd.authoring import dsl
from skfd.authoring.parsing import Parser, wff
from skfd.authoring.rules import (
    PreludeRulesError,
    RuleEntry,
    build_catalog,
    debug_list,
    get_rule,
)
from skfd.authoring.typing import RuleSig


def _setup_registry() -> dsl.RequireRegistry:
    reg = dsl.RequireRegistry()
    Imp = dsl.Constructor("->", 2)
    Not = dsl.Constructor("-.", 1)
    reg.require(Imp, RuleSig(("wff", "wff"), "wff"), precedence=20, assoc="right")
    reg.require(Not, RuleSig(("wff",), "wff"), precedence=30, assoc="right")
    return reg


def test_parser_basic_infix_prefix() -> None:
    reg = _setup_registry()
    expr = wff("ph -> ps", registry=reg)
    assert isinstance(expr, dsl.App)
    # prefix
    expr2 = wff("-. ph", registry=reg)
    assert isinstance(expr2, dsl.App)


def test_parser_right_associates_chained_prefix_binders() -> None:
    reg = dsl.RequireRegistry()
    binder = dsl.Constructor("A.", 2)
    reg.require(
        binder,
        RuleSig(("wff", "wff"), "wff"),
        precedence=40,
        assoc="right",
    )

    expr = wff("A. x A. y ph", registry=reg)

    assert expr == binder(dsl.Var("x"), binder(dsl.Var("y"), dsl.Var("ph")))


def test_parser_accepts_bracketed_substitution_notation() -> None:
    reg = dsl.RequireRegistry()
    substitution = dsl.Constructor("[", 3)
    iff = dsl.Constructor("<->", 2)
    reg.require(substitution, RuleSig(("wff", "wff", "wff"), "wff"))
    reg.require(
        iff,
        RuleSig(("wff", "wff"), "wff"),
        precedence=10,
        assoc="right",
    )

    expr = wff("[ t / x ] ph", registry=reg)
    scoped = wff("[ t / x ] ph <-> ps", registry=reg)

    assert expr == substitution(dsl.Var("t"), dsl.Var("x"), dsl.Var("ph"))
    assert scoped == iff(expr, dsl.Var("ps"))


def test_parser_parens_and_error() -> None:
    reg = _setup_registry()
    expr = wff("( ph -> ps )", registry=reg)
    assert isinstance(expr, dsl.App)

    with pytest.raises(Exception):
        Parser("( ph", registry=reg).parse()


def test_parser_unicode_aliases() -> None:
    reg = dsl.RequireRegistry()
    builders = dsl.BuilderRegistry()

    @dsl.symbol(
        "->",
        2,
        ("wff", "wff"),
        "wff",
        registry=reg,
        builder_registry=builders,
        precedence=20,
        assoc="right",
        aliases=("→",),
    )
    def _imp(_b, args):
        return args[0]

    @dsl.symbol(
        "-.",
        1,
        ("wff",),
        "wff",
        registry=reg,
        builder_registry=builders,
        precedence=30,
        assoc="right",
        aliases=("¬",),
    )
    def _not(_b, args):
        return args[0]

    assert isinstance(wff("ph → ps", registry=reg), dsl.App)
    assert isinstance(wff("¬ ph", registry=reg), dsl.App)


def test_rules_catalog_and_get() -> None:
    def r1(x):
        return x

    entries = [RuleEntry(label="R1", kind="axiom", fn=r1)]
    cat = build_catalog(entries)
    assert get_rule(cat, "R1") is r1
    assert debug_list(cat)[0][0] == "R1"

    with pytest.raises(PreludeRulesError):
        build_catalog(
            [
                RuleEntry(label="R1", kind="axiom", fn=r1),
                RuleEntry(label="R1", kind="rule", fn=r1),
            ]
        )

    with pytest.raises(PreludeRulesError):
        get_rule(cat, "R2")
