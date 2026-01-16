# logic/propositional/hilbert/__init__.py
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeAlias

from prelude.formula import Builtins
from prelude.formula import imp as mk_imp
from prelude.formula import wa as mk_wa
from prelude.formula import wn as mk_wn
from skfd.authoring.dsl import BuilderFn, CompileEnv, Expr, RequireRegistry, compile_wff
from skfd.authoring.formula import Wff
from skfd.authoring.typing import HypothesisAny, PreludeTypingError, RuleApp
from skfd.core.symbols import SymbolInterner

from ._syntactic import RuleBundle, make_rules

RuleFn: TypeAlias = Callable[..., Wff]


# -----------------------------------------------------------------------------
# Builders for authoring -> token lowering
# -----------------------------------------------------------------------------

def _hilbert_builders() -> dict[str, BuilderFn]:
    """Map authoring constructor names to token builders."""
    # We match the names defined in _structures.py (→, ¬, ∧)
    return {
        "→": lambda b, xs: mk_imp(b, xs[0], xs[1]),
        "¬": lambda b, xs: mk_wn(b, xs[0]),
        "∧": lambda b, xs: mk_wa(b, xs[0], xs[1]),
    }


# -----------------------------------------------------------------------------
# System
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class HilbertSystem:
    """Hilbert propositional logic bundle.

    Authoring bridge:
      - author_env(): returns CompileEnv bound to this system
      - compile(expr): lowers authoring Expr -> token-level Wff
    """
    interner: SymbolInterner
    builtins: Builtins
    rule_app: RuleApp
    rules: Mapping[str, RuleFn]
    axioms: Mapping[str, Expr]

    @classmethod
    def make(cls, *, interner: SymbolInterner, origin_ref: Any = None) -> HilbertSystem:
        b = Builtins.ensure(interner, origin_ref=origin_ref)

        bundle: RuleBundle = make_rules(b)
        rule_app = RuleApp(sigs=bundle.sigs)

        # You may keep the token-level schema view if you still want it.
        # If you are fully switching to authoring Expr axioms, you can drop this field.
        from .axioms import make_axioms  # authoring Expr axioms

        return cls(
            interner=interner,
            builtins=b,
            rule_app=rule_app,
            rules=bundle.rules,
            axioms=make_axioms(),
        )

    # -------------------------------------------------------------------------
    # Authoring bridge
    # -------------------------------------------------------------------------

    def author_env(
        self,
        *,
        origin_module_id: str = "hilbert",
        origin_ref: Any = None,
        registry: RequireRegistry | None = None,
    ) -> tuple[CompileEnv, RequireRegistry]:
        """Return a CompileEnv + RequireRegistry for authoring compilation.

        - origin_module_id controls where authoring Vars are interned.
        - registry defaults to skfd.authoring.dsl.DEFAULT_REQUIRE if not provided.
        """
        if registry is None:
            from skfd.authoring.dsl import DEFAULT_REQUIRE as registry_default
            registry = registry_default

        env = CompileEnv(
            interner=self.interner,
            builtins=self.builtins,
            ctor_builders=_hilbert_builders(),  # Injected here!
            origin_module_id=origin_module_id,
            origin_ref=origin_ref,
        )
        return env, registry

    def compile(self, expr: Expr, *, ctx: str = "compile") -> Wff:
        """Compile an authoring Expr into token-level Wff."""
        env, registry = self.author_env()
        try:
            return compile_wff(expr, env=env, registry=registry)
        except Exception as e:
            # Keep a narrow, readable surface for users
            raise PreludeTypingError(f"{ctx}: {e}") from e

    def compile_axioms(self) -> Mapping[str, Wff]:
        """Compile the author-facing axioms (Expr) into token-level Wff."""
        return {k: self.compile(v, ctx=f"compile_axiom[{k}]") for k, v in self.axioms.items()}

    # -------------------------------------------------------------------------
    # Typed rule application (optional convenience)
    # -------------------------------------------------------------------------

    def apply(self, label: str, hyps: Sequence[HypothesisAny], *, ctx: str) -> Wff:
        self.rule_app.check(label, hyps, ctx=ctx)
        fn = self.rules.get(label)
        if fn is None:
            raise PreludeTypingError(f"{ctx}: missing rule implementation for {label!r}")
        return fn(*hyps)


def make(*, interner: SymbolInterner, origin_ref: Any = None) -> HilbertSystem:
    return HilbertSystem.make(interner=interner, origin_ref=origin_ref)


__all__ = ["HilbertSystem", "make"]
