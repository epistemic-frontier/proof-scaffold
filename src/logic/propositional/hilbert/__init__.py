# logic/propositional/hilbert/__init__.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence, TypeAlias

from prelude.axioms import AxiomSchema
from prelude.authoring import CompileEnv, Expr, RequireRegistry, compile_wff
from prelude.formula import Builtins, Wff
from prelude.symbols import SymbolInterner
from prelude.typing import Hypothesis, PreludeTypingError, RuleApp, Sort

from ._syntactic import RuleBundle, make_rules

RuleFn: TypeAlias = Callable[..., object]


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
    axioms: Mapping[str, AxiomSchema[Wff]]  # existing token-level schema view (optional)

    @classmethod
    def make(cls, *, interner: SymbolInterner, origin_ref: Any = None) -> HilbertSystem:
        b = Builtins.ensure(interner, origin_ref=origin_ref)

        bundle: RuleBundle = make_rules(b)
        rule_app = RuleApp(sigs=bundle.sigs)

        # You may keep the token-level schema view if you still want it.
        # If you are fully switching to authoring Expr axioms, you can drop this field.
        from .axioms import make_axioms  # token-level schema factory (optional)

        return cls(
            interner=interner,
            builtins=b,
            rule_app=rule_app,
            rules=bundle.rules,
            axioms=make_axioms(b),
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
        - registry defaults to prelude.authoring.DEFAULT_REQUIRE if not provided.
        """
        if registry is None:
            from prelude.authoring import DEFAULT_REQUIRE as registry_default
            registry = registry_default

        env = CompileEnv(
            interner=self.interner,
            builtins=self.builtins,
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

    def apply(self, label: str, hyps: Sequence[Hypothesis[Sort]], *, ctx: str) -> object:
        self.rule_app.check(label, hyps, ctx=ctx)
        fn = self.rules.get(label)
        if fn is None:
            raise PreludeTypingError(f"{ctx}: missing rule implementation for {label!r}")
        return fn(*hyps)  # type: ignore[misc]


def make(*, interner: SymbolInterner, origin_ref: Any = None) -> HilbertSystem:
    return HilbertSystem.make(interner=interner, origin_ref=origin_ref)


__all__ = ["HilbertSystem", "make"]
