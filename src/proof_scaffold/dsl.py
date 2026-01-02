# proof_scaffold/dsl.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator, Literal, Sequence, Union

from .theorem import Theorem

# -----------------------------
# Errors
# -----------------------------

class MMDSLError(ValueError):
    """Raised when the DSL detects an invalid Metamath construction."""


# -----------------------------
# Small helpers / types
# -----------------------------

TypeCode = str
Token = str
Label = str
KindHyp = Literal["$f", "$e"]
KindAssert = Literal["$a", "$p"]
ProofStep = Union[str, Theorem]


def _clean_comment_ascii(text: str) -> str:
    """
    Keep comments safe for strict tools:
    - strip Metamath comment delimiters
    - replace non-ascii chars with '?'
    """
    t = text.replace("$(", "").replace("$)", "")
    return "".join(ch if ord(ch) < 128 else "?" for ch in t)


def _join_tokens(tokens: Sequence[str]) -> str:
    return " ".join(tokens)


def expr(*tokens: str) -> tuple[str, ...]:
    """A tiny expression constructor."""
    if not tokens:
        raise MMDSLError("expr() must be non-empty")
    return tuple(tokens)


# -----------------------------
# Internal scope model
# -----------------------------

@dataclass
class _Scope:
    # labels declared in this scope (for visibility + leakage prevention)
    local_labels: set[Label] = field(default_factory=set)

    # active floating hypotheses labels (e.g. wph $f wff ph $.)
    # map variable token -> label
    active_f: dict[Token, Label] = field(default_factory=dict)

    # active essential hypotheses labels (ordered, as in Metamath)
    active_e: list[Label] = field(default_factory=list)

    # strict profile: forbid $e at top-level
    is_top_level: bool = False


# -----------------------------
# Builder
# -----------------------------

class MMBuilder:
    """
    A minimal typed-ish Metamath DSL with scope tracking.

    Supported statements:
      $c, $v, $f, $e, $a, $p, ${ ... $}, comments

    Notes:
    - This is not a full verifier.
    - Conservative checks:
        * tokens in expressions must be declared via $c or $v
        * label must not collide with any declared token
        * proof *string* labels must be visible at the point of use
        * $e is forbidden at top-level in strict mode (knife-friendly)
    - Cross-module proof steps may be passed as `Theorem` handles:
        * rendered as their Metamath `label`
        * their `fqname` is collected into builder.requires()
        * visibility is deferred to the linker stage
    """

    def __init__(self, *, strict: bool = True, ascii_comments: bool = True) -> None:
        self._lines: list[str] = []
        self._strict = strict
        self._ascii_comments = ascii_comments

        self._constants: set[Token] = set()
        self._variables: set[Token] = set()

        # All labels declared (global uniqueness).
        self._labels: set[Label] = set()

        # Scope stack
        self._scopes: list[_Scope] = [_Scope(is_top_level=True)]

        # Cross-module theorem dependencies (fqnames)
        self._requires: set[str] = set()

    # -------------
    # Scope helpers
    # -------------

    def block(self) -> "_BlockCtx":
        return _BlockCtx(self)

    @property
    def _scope(self) -> _Scope:
        return self._scopes[-1]

    def _push_scope(self) -> None:
        self._lines.append("${")
        self._scopes.append(_Scope(is_top_level=False))

    def _pop_scope(self) -> None:
        if len(self._scopes) <= 1:
            raise MMDSLError("unbalanced scope pop")
        self._scopes.pop()
        self._lines.append("$}")

    # -----------------
    # Core validations
    # -----------------

    def _check_label_fresh(self, label: Label) -> None:
        if label in self._labels:
            raise MMDSLError(f"duplicate label: {label}")
        if label in self._constants or label in self._variables:
            raise MMDSLError(f"label '{label}' conflicts with declared token")
        if label.startswith("$"):
            raise MMDSLError(f"invalid label startswith '$': {label}")

    def _register_label(self, label: Label) -> None:
        self._check_label_fresh(label)
        self._labels.add(label)
        self._scope.local_labels.add(label)

    def _check_expr_tokens_declared(self, tokens: Sequence[Token]) -> None:
        for t in tokens:
            if t not in self._constants and t not in self._variables:
                raise MMDSLError(f"undeclared token in expression: '{t}'")

    def _visible_labels(self) -> set[Label]:
        s: set[Label] = set()
        for sc in self._scopes:
            s |= sc.local_labels
        return s

    # -------------
    # Dependencies
    # -------------

    def requires(self) -> tuple[str, ...]:
        """Return collected cross-module theorem fqnames (stable order)."""
        return tuple(sorted(self._requires))

    # -------------
    # Rendering
    # -------------

    def render(self) -> str:
        if len(self._scopes) != 1:
            raise MMDSLError("unbalanced scopes: missing $}")
        return "\n".join(self._lines) + ("\n" if self._lines else "")

    def __str__(self) -> str:
        return self.render()

    # -------------
    # DSL methods
    # -------------

    def comment(self, text: str) -> "MMBuilder":
        t = _clean_comment_ascii(text) if self._ascii_comments else text
        self._lines.append(f"$( {t} $)")
        return self

    def c(self, *symbols: str) -> "MMBuilder":
        if not symbols:
            raise MMDSLError("$c must declare at least one symbol")
        for s in symbols:
            if s in self._variables:
                raise MMDSLError(f"token '{s}' already declared as $v")
            self._constants.add(s)
        self._lines.append(f"$c {_join_tokens(symbols)} $.")
        return self

    def v(self, *symbols: str) -> "MMBuilder":
        if not symbols:
            raise MMDSLError("$v must declare at least one symbol")
        for s in symbols:
            if s in self._constants:
                raise MMDSLError(f"token '{s}' already declared as $c")
            self._variables.add(s)
        self._lines.append(f"$v {_join_tokens(symbols)} $.")
        return self

    def f(self, label: str, typecode: TypeCode, var: str) -> "MMBuilder":
        if var not in self._variables:
            raise MMDSLError(f"$f variable '{var}' not declared via $v")
        if typecode not in self._constants:
            raise MMDSLError(f"$f typecode '{typecode}' not declared via $c")
        self._register_label(label)
        self._scope.active_f[var] = label
        self._lines.append(f"{label} $f {typecode} {var} $.")
        return self

    def e(self, label: str, typecode: TypeCode, eexpr: Sequence[str] | str) -> "MMBuilder":
        if self._strict and self._scope.is_top_level:
            raise MMDSLError("$e at top level is forbidden in strict mode; wrap it in ${ ... $}")
        if typecode not in self._constants:
            raise MMDSLError(f"$e typecode '{typecode}' not declared via $c")

        tokens = (eexpr.split() if isinstance(eexpr, str) else list(eexpr))
        if not tokens:
            raise MMDSLError("$e expression must be non-empty")
        self._check_expr_tokens_declared(tokens)

        self._register_label(label)
        self._scope.active_e.append(label)
        self._lines.append(f"{label} $e {typecode} {_join_tokens(tokens)} $.")
        return self

    def a(self, label: str, typecode: TypeCode, aexpr: Sequence[str] | str) -> "MMBuilder":
        if typecode not in self._constants:
            raise MMDSLError(f"$a typecode '{typecode}' not declared via $c")

        tokens = (aexpr.split() if isinstance(aexpr, str) else list(aexpr))
        if not tokens:
            raise MMDSLError("$a expression must be non-empty")
        self._check_expr_tokens_declared(tokens)

        self._register_label(label)
        self._lines.append(f"{label} $a {typecode} {_join_tokens(tokens)} $.")
        return self

    def p(
        self,
        label: str,
        typecode: TypeCode,
        pexpr: Sequence[str] | str,
        proof: Sequence[ProofStep] | str,
        *,
        comment: str | None = None,
    ) -> "MMBuilder":
        if typecode not in self._constants:
            raise MMDSLError(f"$p typecode '{typecode}' not declared via $c")

        expr_tokens = (pexpr.split() if isinstance(pexpr, str) else list(pexpr))
        if not expr_tokens:
            raise MMDSLError("$p expression must be non-empty")
        self._check_expr_tokens_declared(expr_tokens)

        # normalize proof
        proof_steps: list[ProofStep]
        if isinstance(proof, str):
            # string proof: legacy mode, steps are labels only
            proof_steps = proof.split()
        else:
            proof_steps = list(proof)
        if not proof_steps:
            raise MMDSLError("$p proof must be non-empty")

        visible = self._visible_labels()

        rendered_steps: list[str] = []
        for step in proof_steps:
            if isinstance(step, Theorem):
                # Cross-module: defer visibility to linker.
                # Render as its Metamath label.
                self._requires.add(step.fqname)
                rendered_steps.append(step.label)
            else:
                # Local label: must be visible now
                if step not in visible:
                    raise MMDSLError(f"proof step '{step}' is not a visible label at this point")
                rendered_steps.append(step)

        if comment:
            self.comment(comment)

        self._register_label(label)
        self._lines.append(f"{label} $p {typecode} {_join_tokens(expr_tokens)} $=")
        self._lines.append(f"  {_join_tokens(rendered_steps)}")
        self._lines.append("$.")
        return self


@dataclass
class _BlockCtx:
    mm: MMBuilder

    def __enter__(self) -> MMBuilder:
        self.mm._push_scope()
        return self.mm

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            self.mm._pop_scope()
        return False
