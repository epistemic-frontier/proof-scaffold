from __future__ import annotations

from dataclasses import dataclass

import pytest

from skfd.authoring.rules import (
    PreludeRulesError,
    RuleRegistry,
    build_rule_bundle,
    build_rule_catalog,
    rule,
    rules_view,
)
from skfd.authoring.typing import WFF, HypWff, RuleSig
from skfd.authoring.formula import Wff


def test_rule_decorator_registers_and_builds_bundle() -> None:
    reg = RuleRegistry()

    @rule(label="r1", kind="axiom", sig=RuleSig(in_sorts=(WFF,), out_sort=WFF), registry=reg)
    @dataclass(frozen=True)
    class R1:
        label: str = "r1"
        sig: RuleSig = RuleSig(in_sorts=(WFF,), out_sort=WFF)

        def __call__(self, h1: HypWff) -> Wff:
            return h1.body

    bundle = build_rule_bundle(reg, bind=lambda cls: cls())
    assert "r1" in bundle.rules
    assert "r1" in bundle.sigs

    w = Wff("wff", ())
    out = bundle.rules["r1"](HypWff("h1", w))  # type: ignore[misc]
    assert out == w


def test_rule_decorator_builds_catalog() -> None:
    reg = RuleRegistry()

    @rule(label="r1", kind="axiom", sig=RuleSig(in_sorts=(WFF,), out_sort=WFF), registry=reg)
    @dataclass(frozen=True)
    class R1:
        label: str = "r1"
        sig: RuleSig = RuleSig(in_sorts=(WFF,), out_sort=WFF)

        def __call__(self, h1: HypWff) -> Wff:
            return h1.body

    cat = build_rule_catalog(reg, bind=lambda cls: cls())
    assert cat["r1"].kind == "axiom"
    assert "r1" in rules_view(cat)


def test_rule_decorator_rejects_duplicate_labels() -> None:
    reg = RuleRegistry()

    @rule(label="r1", kind="axiom", sig=RuleSig(in_sorts=(WFF,), out_sort=WFF), registry=reg)
    @dataclass(frozen=True)
    class R1:
        label: str = "r1"
        sig: RuleSig = RuleSig(in_sorts=(WFF,), out_sort=WFF)

        def __call__(self, h1: HypWff) -> Wff:
            return h1.body

    with pytest.raises(PreludeRulesError):

        @rule(label="r1", kind="rule", sig=RuleSig(in_sorts=(WFF,), out_sort=WFF), registry=reg)
        @dataclass(frozen=True)
        class R1b:
            label: str = "r1"
            sig: RuleSig = RuleSig(in_sorts=(WFF,), out_sort=WFF)

            def __call__(self, h1: HypWff) -> Wff:
                return h1.body


def test_rule_decorator_rejects_label_mismatch() -> None:
    reg = RuleRegistry()

    with pytest.raises(PreludeRulesError):

        @rule(label="r1", kind="axiom", sig=RuleSig(in_sorts=(WFF,), out_sort=WFF), registry=reg)
        @dataclass(frozen=True)
        class R1:
            label: str = "other"
            sig: RuleSig = RuleSig(in_sorts=(WFF,), out_sort=WFF)

            def __call__(self, h1: HypWff) -> Wff:
                return h1.body


def test_rule_decorator_rejects_sig_mismatch() -> None:
    reg = RuleRegistry()

    with pytest.raises(PreludeRulesError):

        @rule(label="r1", kind="axiom", sig=RuleSig(in_sorts=(WFF,), out_sort=WFF), registry=reg)
        @dataclass(frozen=True)
        class R1:
            label: str = "r1"
            sig: RuleSig = RuleSig(in_sorts=(WFF, WFF), out_sort=WFF)

            def __call__(self, h1: HypWff) -> Wff:
                return h1.body

