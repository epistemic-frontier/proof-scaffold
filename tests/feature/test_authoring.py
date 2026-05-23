from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from skfd.authoring import dsl
from skfd.authoring.emit import emit_axioms, emit_lemmas
from skfd.authoring.formula import Wff, wff_atom, render
from skfd.authoring.typing import Context, Hypothesis, PreludeTypingError, RuleApp, RuleSig
from skfd.builder_v2 import MMBuilderV2
from skfd.core.diag import LinkerDiagError
from skfd.core.lir import Axiom
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.names import NameResolver


@dataclass(frozen=True)
class _FakeSym:
    id: int
    local_name: str
    kind: str


def _make_env() -> dsl.CompileEnv:
    interner = SymbolInterner()

    def _builder(_b: Any, args: list[Wff]) -> Wff:
        tokens = tuple(t for w in args for t in w.tokens)
        return Wff("wff", tokens)

    return dsl.CompileEnv(
        interner=interner,
        names=NameResolver(),
        builtins=object(),
        ctor_builders={"IMP": _builder},
        origin_module_id="test",
    )


def test_operator_registry_and_pretty() -> None:
    dsl.DEFAULT_OPERATORS.reset()
    Imp = dsl.Constructor("IMP", 2)
    dsl.register_operator("rshift", Imp)

    a = dsl.Var("a")
    b = dsl.Var("b")
    expr = a >> b

    assert isinstance(expr, dsl.App)
    assert dsl.pretty(expr) == "(a IMP b)"


def test_constructor_arity_error() -> None:
    ctor = dsl.Constructor("C", 2)
    with pytest.raises(PreludeTypingError):
        ctor(dsl.Var("x"))


def test_require_registry_conflict() -> None:
    reg = dsl.RequireRegistry()
    ctor = dsl.Constructor("C", 1)
    reg.require(ctor, RuleSig(("wff",), "wff"))
    with pytest.raises(PreludeTypingError):
        reg.require(ctor, RuleSig(("wff", "wff"), "wff"))


def test_compile_wff_var_and_app() -> None:
    reg = dsl.RequireRegistry()
    Imp = dsl.Constructor("IMP", 2)
    reg.require(Imp, RuleSig(("wff", "wff"), "wff"))

    env = _make_env()
    a = dsl.Var("a")
    b = dsl.Var("b")
    expr = Imp(a, b)

    out = dsl.compile_wff(expr, env=env, registry=reg)
    assert out.sort == "wff"
    assert len(out.tokens) == 2


def test_compile_wff_missing_builder() -> None:
    reg = dsl.RequireRegistry()
    And = dsl.Constructor("AND", 2)
    reg.require(And, RuleSig(("wff", "wff"), "wff"))
    env = dsl.CompileEnv(
        interner=SymbolInterner(),
        names=NameResolver(),
        builtins=object(),
        ctor_builders={},
        origin_module_id="test",
    )

    with pytest.raises(PreludeTypingError):
        dsl.compile_wff(And(dsl.Var("a"), dsl.Var("b")), env=env, registry=reg)


def test_context_require_and_sort_checks() -> None:
    a = wff_atom(1)
    h = Hypothesis(label="h1", body=a)
    ctx = Context().extend(h)

    assert ctx.require("h1", ctx="ctx").label == "h1"

    app = RuleApp({"r1": RuleSig(("wff",), "wff")})
    sig = app.check("r1", [h], ctx="ctx")
    assert sig.out_sort == "wff"


def test_render_and_emit_axioms() -> None:
    interner = SymbolInterner()
    c = interner.intern(origin_module_id="t", local_name="c", kind="Const", origin_ref=None)
    v = interner.intern(origin_module_id="t", local_name="v", kind="Var", origin_ref=None)
    wff = Wff("wff", (c, v))
    s = render(wff.tokens, symtab={c: _FakeSym(c, "c", "Const"), v: _FakeSym(v, "v", "Var")})
    assert s == "c v"

    class Provider:
        def __init__(self, interner: SymbolInterner) -> None:
            self.interner = interner

        def compile_axioms(self) -> dict[str, Wff]:
            return {"ax": wff}

    mm = MMBuilderV2(
        interner=interner,
        origin_table=OriginTable(),
        names=NameResolver(),
        unit_id="t",
        origin_module_id="t",
    )
    emit_axioms(mm, Provider(interner))
    unit = mm.finish()
    assert any(isinstance(s, Axiom) for s in unit.lir_stmts)


def test_emit_lemmas_basic() -> None:
    interner = SymbolInterner()
    c = interner.intern(origin_module_id="t", local_name="c", kind="Const", origin_ref=None)
    v = interner.intern(origin_module_id="t", local_name="v", kind="Var", origin_ref=None)
    wff = Wff("wff", (c, v))

    class Provider:
        def __init__(self, interner: SymbolInterner) -> None:
            self.interner = interner

        def compile_axioms(self) -> dict[str, Wff]:
            return {"ax": wff}

    class Step:
        def __init__(self, wff: Wff) -> None:
            self.wff = wff

    class Lemma:
        def __init__(self, name: str, statement: Wff, steps: list[Step]) -> None:
            self.name = name
            self.statement = statement
            self.steps = steps

    mm = MMBuilderV2(
        interner=interner,
        origin_table=OriginTable(),
        names=NameResolver(),
        unit_id="t",
        origin_module_id="t",
    )
    emit_lemmas(mm, Provider(interner), [Lemma("L1", wff, [Step(wff)])])
    unit = mm.finish()
    assert any(isinstance(s, Axiom) for s in unit.lir_stmts)


def test_emit_axioms_and_lemmas_reject_interner_mismatch() -> None:
    interner = SymbolInterner()
    other = SymbolInterner()
    v = interner.intern(origin_module_id="t", local_name="v", kind="Var", origin_ref=None)
    wff = Wff("wff", (v,))

    class Provider:
        def __init__(self, interner: SymbolInterner) -> None:
            self.interner = interner

        def compile_axioms(self) -> dict[str, Wff]:
            return {"ax": wff}

    class Lemma:
        name = "L"
        statement = wff
        steps = []

    mm = MMBuilderV2(
        interner=interner,
        origin_table=OriginTable(),
        names=NameResolver(),
        unit_id="t",
        origin_module_id="t",
    )

    with pytest.raises(LinkerDiagError):
        emit_axioms(mm, Provider(other))
    with pytest.raises(LinkerDiagError):
        emit_lemmas(mm, Provider(other), [Lemma()])


def test_export_axioms_and_symbol_aliases() -> None:
    reg = dsl.RequireRegistry()
    builders = dsl.BuilderRegistry()
    dsl.DEFAULT_OPERATORS.reset()

    @dsl.symbol("IMP", 2, ("wff", "wff"), "wff", registry=reg, builder_registry=builders, op="rshift", aliases=["->"])
    def _imp(_b: object, args: list[Wff]) -> Wff:
        tokens = tuple(t for w in args for t in w.tokens)
        return Wff("wff", tokens)

    a = dsl.Var("a")
    b = dsl.Var("b")
    expr = a >> b
    assert isinstance(expr, dsl.App)

    exported = dsl.export_axioms({"ax1": expr, "phi": a})
    assert "ax1" in exported
    assert "phi" not in exported


def test_pretty_and_registry_helpers() -> None:
    reg = dsl.RequireRegistry()
    c1 = dsl.Constructor("N", 1)
    c2 = dsl.Constructor("F", 3)
    reg.require(c1, RuleSig(("wff",), "wff"))
    reg.require(c2, RuleSig(("wff", "wff", "wff"), "wff"))

    a = dsl.Var("a")
    expr1 = c1(a)
    expr2 = c2(a, a, a)
    assert dsl.pretty(expr1) == "Na"
    assert dsl.pretty(expr2).startswith("F(")

    desc = reg.describe()
    assert "N" in desc and "F" in desc

    reg.reset()
    assert reg.specs() == {}
