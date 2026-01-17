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
# Operator Overloading Registry
# -----------------------------------------------------------------------------

OperatorKey = Literal[
    "rshift",  # >> (Implication)
    "and",     # &  (And)
    "or",      # |  (Or)
    "invert",  # ~  (Not)
    "eq",      # == (Equal)
    "le",      # <= (Subset/Leq)
]


class OperatorRegistry:
    """Registry for mapping Python operators to Constructors."""

    def __init__(self) -> None:
        self._ops: dict[OperatorKey, Constructor] = {}

    def register(self, key: OperatorKey, ctor: Constructor) -> None:
        self._ops[key] = ctor

    def get(self, key: OperatorKey) -> Constructor | None:
        return self._ops.get(key)
    
    def reset(self) -> None:
        self._ops.clear()


DEFAULT_OPERATORS = OperatorRegistry()


def register_operator(key: OperatorKey, ctor: Constructor) -> None:
    """Register a global operator mapping."""
    DEFAULT_OPERATORS.register(key, ctor)


# -----------------------------------------------------------------------------
# Expr AST
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Expr:
    """Base class for authoring expressions."""

    sort: ExprSortAny = field(default="wff", init=False)

    def _op(self, key: OperatorKey, *args: Expr) -> Expr:
        """Helper to dispatch operator to registered constructor."""
        ctor = DEFAULT_OPERATORS.get(key)
        if ctor is None:
            raise NotImplementedError(f"Operator {key!r} not registered")
        return ctor(self, *args)

    def __rshift__(self, other: Expr) -> Expr:
        """Overload >> for Implication (A >> B)."""
        return self._op("rshift", other)

    def __and__(self, other: Expr) -> Expr:
        """Overload & for And (A & B)."""
        return self._op("and", other)

    def __or__(self, other: Expr) -> Expr:
        """Overload | for Or (A | B)."""
        return self._op("or", other)

    def __invert__(self) -> Expr:
        """Overload ~ for Not (~A)."""
        ctor = DEFAULT_OPERATORS.get("invert")
        if ctor is None:
            raise NotImplementedError("Operator 'invert' not registered")
        return ctor(self)

    def __le__(self, other: Expr) -> Expr:
        """Overload <= for Subset/Leq (A <= B)."""
        return self._op("le", other)

    def __eq__(self, other: Any) -> Expr | bool:  # type: ignore[override]
        """Overload == for Equality (A == B).

        Note: returning Expr breaks Python's hash contract if Expr is hashable,
        but Expr is dataclass(frozen=True) so it has a generated __hash__.
        Python dataclasses generate __eq__ by default.
        We must be careful: if we return Expr, we break `if x == y:` checks used in
        sets/dicts or internal logic.
        
        Decision: For now, we will NOT overload __eq__ to avoid breaking
        dataclass structural equality. Authors should use Eq(A, B) or
        we can use a different operator like __matmul__ or introduce a .eq() method.
        """
        return super().__eq__(other)



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
    
    Parsing info:
      - precedence: higher binds tighter
      - assoc: associativity ("left", "right", "none")
    """

    ctor: Constructor
    sig: RuleSig
    notes: str = ""
    precedence: int = 0
    assoc: Literal["left", "right", "none"] = "left"


class RequireRegistry:
    """Registry for language requirements (constructor -> signature)."""

    def __init__(self) -> None:
        self._by_ctor: dict[Constructor, RequireSpec] = {}
        self._by_name: dict[str, RequireSpec] = {}

    def require(
        self,
        ctor: Constructor,
        sig: RuleSig,
        *,
        notes: str = "",
        precedence: int = 0,
        assoc: Literal["left", "right", "none"] = "left",
    ) -> None:
        if ctor.arity != sig.arity:
            raise PreludeTypingError(
                f"require {ctor.name!r}: ctor.arity={ctor.arity} != sig.arity={sig.arity}"
            )

        spec = RequireSpec(
            ctor=ctor, sig=sig, notes=notes, precedence=precedence, assoc=assoc
        )

        existing = self._by_ctor.get(ctor)
        if existing is not None and existing.sig != sig:
            raise PreludeTypingError(
                f"require {ctor.name!r}: conflicting signatures: {existing.sig} vs {sig}"
            )
        self._by_ctor[ctor] = spec

        existing_name = self._by_name.get(ctor.name)
        if existing_name is not None and existing_name.ctor is not ctor:
            # Allow compatible re-definition (e.g. from multiple packages sharing common symbols)
            if existing_name.sig != sig:
                 raise PreludeTypingError(f"duplicate constructor name: {ctor.name!r}")
            # If compatible, we just overwrite the name mapping to the new spec
            # This ensures the most recently registered constructor is canonical by name
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
    
    def reset(self) -> None:
        self._by_ctor.clear()
        self._by_name.clear()


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
    precedence: int = 0,
    assoc: Literal["left", "right", "none"] = "left",
) -> None:
    """Declare a constructor signature in a registry."""
    registry.require(
        ctor,
        RuleSig(in_sorts=in_sorts, out_sort=out_sort),
        notes=notes,
        precedence=precedence,
        assoc=assoc,
    )


# -----------------------------------------------------------------------------
# Lowering: compile Expr -> token-level Wff
#
# This is the bridge from authoring to implementation.
# Authors should not need to touch this unless they are exporting to IR/.mm.
# -----------------------------------------------------------------------------

Axiom: TypeAlias = Expr

# Generic builder function: (builtins, args) -> Wff
BuilderFn: TypeAlias = Callable[[Any, Sequence[Wff]], Wff]


class BuilderRegistry:
    """Registry for authoring -> implementation builder functions."""

    def __init__(self) -> None:
        self._builders: dict[str, BuilderFn] = {}

    def register(self, name: str, fn: BuilderFn) -> None:
        # Allow overwriting for reloading/common symbols support
        self._builders[name] = fn

    def get(self, name: str) -> BuilderFn | None:
        return self._builders.get(name)

    def all(self) -> dict[str, BuilderFn]:
        return dict(self._builders)
        
    def reset(self) -> None:
        self._builders.clear()


DEFAULT_BUILDERS = BuilderRegistry()


def symbol(
    name: str,
    arity: int,
    in_sorts: tuple[Sort, ...],
    out_sort: Sort,
    registry: RequireRegistry = DEFAULT_REQUIRE,
    builder_registry: BuilderRegistry = DEFAULT_BUILDERS,
    op: OperatorKey | None = None,
    notes: str = "",
    precedence: int = 0,
    assoc: Literal["left", "right", "none"] = "left",
    aliases: Sequence[str] = (),
) -> Callable[[BuilderFn], Constructor]:
    """Decorator to define a logical symbol, registering its signature and builder.

    Usage:
        @symbol("→", 2, (WFF, WFF), WFF, op="rshift", precedence=20, assoc="right", aliases=["->"])
        def Imp(b, args):
            return b.imp(args[0], args[1])
    """

    def decorator(fn: BuilderFn) -> Constructor:
        ctor = Constructor(name, arity)
        require(
            ctor,
            in_sorts=in_sorts,
            out_sort=out_sort,
            notes=notes,
            registry=registry,
            precedence=precedence,
            assoc=assoc,
        )
        builder_registry.register(name, fn)
        if op:
            register_operator(op, ctor)
            
        for alias in aliases:
            # Register aliases in RequireRegistry pointing to the SAME constructor logic
            alias_ctor = Constructor(alias, arity)
            require(
                alias_ctor,
                in_sorts=in_sorts,
                out_sort=out_sort,
                notes=f"Alias for {name}",
                registry=registry,
                precedence=precedence,
                assoc=assoc,
            )
            builder_registry.register(alias, fn)
            
        return ctor

    return decorator


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


def export_axioms(module_globals: dict[str, Any]) -> Mapping[str, Axiom]:
    """Auto-export axioms from module globals.

    Collects all global variables that are instances of `Expr` (but not `Var`)
    and returns a dictionary mapping variable names to expressions.
    This helps eliminate boilerplate `make_axioms` functions.
    """
    exported: dict[str, Axiom] = {}
    for name, val in module_globals.items():
        if name.startswith("_"):
            continue
        # We only export non-Var expressions (Vars are usually placeholders like phi)
        if isinstance(val, Expr) and not isinstance(val, Var):
            exported[name] = val
    return exported


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
    "symbol",
    "DEFAULT_BUILDERS",
    "BuilderRegistry",
    "BuilderFn",
    "Axiom",
    "export_axioms",
    # operators
    "DEFAULT_OPERATORS",
    "OperatorRegistry",
    "register_operator",
]
