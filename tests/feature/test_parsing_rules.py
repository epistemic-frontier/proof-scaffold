from __future__ import annotations

import pytest

from skfd.authoring import dsl
from skfd.authoring.parsing import Parser, wff
from skfd.authoring.rules import PreludeRulesError, RuleEntry, build_catalog, debug_list, get_rule
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


def test_parser_parens_and_error() -> None:
    reg = _setup_registry()
    expr = wff("( ph -> ps )", registry=reg)
    assert isinstance(expr, dsl.App)

    with pytest.raises(Exception):
        Parser("( ph", registry=reg).parse()


def test_rules_catalog_and_get() -> None:
    def r1(x):
        return x

    entries = [RuleEntry(label="R1", kind="axiom", fn=r1)]
    cat = build_catalog(entries)
    assert get_rule(cat, "R1") is r1
    assert debug_list(cat)[0][0] == "R1"

    with pytest.raises(PreludeRulesError):
        build_catalog([RuleEntry(label="R1", kind="axiom", fn=r1), RuleEntry(label="R1", kind="rule", fn=r1)])

    with pytest.raises(PreludeRulesError):
        get_rule(cat, "R2")
