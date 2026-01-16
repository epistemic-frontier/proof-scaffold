# skfd/authoring/dsl.py
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import (
    Any,
    Literal,
    TypeAlias,
)

from skfd.core.symbols import SymbolInterner

from .formula import Wff, wff_atom
from .typing import PreludeTypingError, RuleSig, Sort

# -----------------------------------------------------------------------------
# Authoring layer: expressions and constructors
#
# This module is intentionally "author-friendly":
# - Authors manipulate Vars and Constructors to build Expr trees.
# - No Builtins / SymbolInterner in author-facing APIs.
# - A `require(...)` mechanism declares arity/sorts for Constructors.
# - A compile step can lower Expr -> token-level Formula (Wff).
# -----------------------------------------------------------------------------

# In this initial phase we only target propositional wff authoring.
ExprSort = Literal["wff"]
ExprSortAny = Literal["wff"]  # placeholder for future extension

# -----------------------------------------------------------------------------
# Expr AST
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Expr:
    """Base class for authoring expressions."""

    sort: ExprSortAny = field(default="wff", init=False)


@dataclass(frozen=True)
class Var(Expr):
    """A formal variable (author-facing), e.g. φ, ψ, χ.

    `name` is a human label used for pretty printing.
    Compilation will map it to a SymbolId via SymbolInterner.
    """

    name: str


@dataclass(frozen=True)
class App(Expr):
    """Application of a Constructor to argument Exprs."""

    ctor: Constructor = field(
        compare=False, default_factory=lambda: Constructor("<unset>", 0)
    )
    args: tuple[Expr, ...] = field(compare=False, default_factory=tuple)

    # keep Expr.sort default


# -----------------------------------------------------------------------------
# Constructors
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Constructor:
    """A named constructor used by authors to build Expr trees.

    Example:
      Imp = Constructor("→", arity=2)
      Not = Constructor("¬", arity=1)
      And = Constructor("∧", arity=2)

    Call syntax:
      Imp(phi, psi)  -> App(Imp, (phi, psi))
    """

    name: str
    arity: int

    def __call__(self, *args: Expr) -> App:
        if len(args) != self.arity:
            raise PreludeTypingError(
                f"constructor {self.name!r}: expects {self.arity} args, got {len(args)}"
            )
        return App(ctor=self, args=tuple(args))


# -----------------------------------------------------------------------------
# Require mechanism: declare the language skeleton
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class RequireSpec:
    """A declaration that a Constructor is a well-typed operator.

    `sig` is expressed using skfd.authoring.typing.RuleSig for consistency:
      - in_sorts: tuple of sorts
      - out_sort: sort
    """

    ctor: Constructor
    sig: RuleSig
    notes: str = ""


class RequireRegistry:
    """Registry for language requirements (constructor -> signature)."""

    def __init__(self) -> None:
        self._by_ctor: dict[Constructor, RequireSpec] = {}
        self._by_name: dict[str, RequireSpec] = {}

    def require(self, ctor: Constructor, sig: RuleSig, *, notes: str = "") -> None:
        if ctor.arity != sig.arity:
            raise PreludeTypingError(
                f"require {ctor.name!r}: ctor.arity={ctor.arity} != sig.arity={sig.arity}"
            )

        spec = RequireSpec(ctor=ctor, sig=sig, notes=notes)

        existing = self._by_ctor.get(ctor)
        if existing is not None and existing.sig != sig:
            raise PreludeTypingError(
                f"require {ctor.name!r}: conflicting signatures: {existing.sig} vs {sig}"
            )
        self._by_ctor[ctor] = spec

        existing_name = self._by_name.get(ctor.name)
        if existing_name is not None and existing_name.ctor is not ctor:
            # two distinct constructors with same name: forbid (authoring ambiguity)
            raise PreludeTypingError(f"duplicate constructor name: {ctor.name!r}")
        self._by_name[ctor.name] = spec

    def spec_for(self, ctor: Constructor) -> RequireSpec | None:
        return self._by_ctor.get(ctor)

    def specs(self) -> Mapping[Constructor, RequireSpec]:
        return dict(self._by_ctor)

    def describe(self) -> str:
        lines: list[str] = []
        for spec in sorted(self._by_ctor.values(), key=lambda s: s.ctor.name):
            ins = ", ".join(spec.sig.in_sorts)
            lines.append(f"{spec.ctor.name}: ({ins}) -> {spec.sig.out_sort}")
        return "\n".join(lines)


# A module-level "default registry" can be convenient for small systems,
# but you can also instantiate your own registry per logic system.
DEFAULT_REQUIRE = RequireRegistry()


def require(
    ctor: Constructor,
    *,
    in_sorts: tuple[Sort, ...],
    out_sort: Sort,
    notes: str = "",
    registry: RequireRegistry = DEFAULT_REQUIRE,
) -> None:
    """Declare a constructor signature in a registry."""
    registry.require(ctor, RuleSig(in_sorts=in_sorts, out_sort=out_sort), notes=notes)


# -----------------------------------------------------------------------------
# Lowering: compile Expr -> token-level Wff
#
# This is the bridge from authoring to implementation.
# Authors should not need to touch this unless they are exporting to IR/.mm.
# -----------------------------------------------------------------------------

# Generic builder function: (builtins, args) -> Wff
BuilderFn: TypeAlias = Callable[[Any, Sequence[Wff]], Wff]


@dataclass(frozen=True)
class CompileEnv:
    """Compilation environment for lowering authoring Expr to Wff tokens."""

    interner: SymbolInterner
    builtins: Any  # Opaque logic-specific builtins object
    ctor_builders: Mapping[str, BuilderFn]  # Must be provided by the logic system
    origin_module_id: str = "authoring"
    origin_ref: Any = None


def compile_wff(
    expr: Expr,
    *,
    env: CompileEnv,
    registry: RequireRegistry = DEFAULT_REQUIRE,
) -> Wff:
    """Compile an authoring Expr into a token-level Wff.

    Rules:
    - Var: interned as a Var symbol in env.interner
    - App(Constructor, args):
        * must be declared via require(...)
        * args must be wff
        * constructor name must have a builder in env.ctor_builders
    """
    if isinstance(expr, Var):
        sid = env.interner.intern(
            origin_module_id=env.origin_module_id,
            local_name=expr.name,
            kind="Var",
            origin_ref=env.origin_ref,
        )
        return wff_atom(sid)

    if isinstance(expr, App):
        spec = registry.spec_for(expr.ctor)
        if spec is None:
            raise PreludeTypingError(
                f"compile: constructor not required: {expr.ctor.name!r}"
            )

        # Sort check: currently only wff supported; keep generic for future.
        if spec.sig.out_sort != "wff":
            raise PreludeTypingError(
                f"compile: only wff out_sort supported (got {spec.sig.out_sort!r})"
            )
        if any(s != "wff" for s in spec.sig.in_sorts):
            raise PreludeTypingError(
                "compile: only wff in_sorts supported in this phase"
            )

        if len(expr.args) != spec.sig.arity:
            raise PreludeTypingError(
                f"compile: arity mismatch for {expr.ctor.name!r}: "
                f"expected {spec.sig.arity}, got {len(expr.args)}"
            )

        builder = env.ctor_builders.get(expr.ctor.name)
        if builder is None:
            raise PreludeTypingError(
                f"compile: no builder for constructor {expr.ctor.name!r}"
            )

        args_wff = [compile_wff(a, env=env, registry=registry) for a in expr.args]
        return builder(env.builtins, args_wff)

    raise PreludeTypingError(f"compile: unknown Expr node: {type(expr).__name__}")


# -----------------------------------------------------------------------------
# Pretty printing (author-facing)
# -----------------------------------------------------------------------------


def pretty(expr: Expr) -> str:
    """A minimal pretty printer for authoring expressions."""
    if isinstance(expr, Var):
        return expr.name
    if isinstance(expr, App):
        # Special-case common arities for readability
        if expr.ctor.arity == 1:
            return f"{expr.ctor.name}{pretty(expr.args[0])}"
        if expr.ctor.arity == 2:
            return f"({pretty(expr.args[0])} {expr.ctor.name} {pretty(expr.args[1])})"
        inner = ", ".join(pretty(a) for a in expr.args)
        return f"{expr.ctor.name}({inner})"
    return f"<{type(expr).__name__}>"


__all__ = [
    # AST
    "Expr",
    "Var",
    "App",
    # constructors
    "Constructor",
    # require
    "RequireSpec",
    "RequireRegistry",
    "DEFAULT_REQUIRE",
    "require",
    # compile
    "CompileEnv",
    "compile_wff",
    # util
    "pretty",
]
