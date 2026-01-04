# scaffold/dsl/builder.py
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from types import TracebackType
from typing import Literal

from proof_scaffold.ir import ProofUnitIR
from proof_scaffold.theorem import Theorem

from .emitter import CompositeEmitter, LIREmitter, TextEmitter
from .errors import MMDSLError
from .origin import InspectOriginProvider, OriginProvider
from .scope import ScopeStack
from .types import Label, ProofStep, Token, TypeCode


class MMBuilder:
    """
    Orchestrator for the Metamath DSL. Delegates to:
      - ScopeStack for visibility/activation
      - OriginProvider for origin capture
      - TextEmitter/LIREmitter for output (single call per DSL method)
    """

    def __init__(
        self,
        *,
        strict: bool = True,
        ascii_comments: bool = True,
        origin_provider: OriginProvider | None = None,
    ) -> None:
        # settings
        self._strict = strict

        # state
        self._constants: set[Token] = set()
        self._variables: set[Token] = set()
        self._labels: set[Label] = set()
        self._requires: set[str] = set()

        # collaborators
        self._scope = ScopeStack()
        self._origin: OriginProvider = origin_provider or InspectOriginProvider()
        self._text = TextEmitter(ascii_comments=ascii_comments)
        self._lir = LIREmitter()
        self._emit = CompositeEmitter(self._text, self._lir)

        # Debug Slice Path A support: allocate stable step_id for each proof token.
        # This is intentionally minimal (LIR-only) and does not introduce HIR.
        self._next_step_id: int = 1

    # -----------------
    # Scope helpers
    # -----------------
    def block(self) -> _BlockCtx:
        return _BlockCtx(self)

    def _push_scope(self) -> None:
        o = self._origin.here()
        self._emit.open_scope(o)
        self._scope.push()

    def _pop_scope(self) -> None:
        if self._scope.depth <= 1:
            raise MMDSLError("unbalanced scope pop")
        self._scope.pop()
        o = self._origin.here()
        self._emit.close_scope(o)

    # -------------
    # Dependencies
    # -------------
    def requires(self) -> tuple[str, ...]:
        return tuple(sorted(self._requires))

    # -------------
    # Rendering
    # -------------
    def render(self) -> str:
        if self._scope.depth != 1:
            raise MMDSLError("unbalanced scopes: missing $}")
        return self._text.render()

    def __str__(self) -> str:  # pragma: no cover
        return self.render()

    # -------------
    # IR exposure
    # -------------
    def to_proof_unit(self, unit_id: str) -> ProofUnitIR:
        return ProofUnitIR(
            unit_id=unit_id,
            lir=self._lir.lir(),
            origin=self._origin.here(),
            symtab=self._emit.symtab(),
        )

    # -----------------
    # Core validations (kept local for now; will migrate to validate.py)
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
        self._scope.register_local_label(label)

    def _check_expr_tokens_declared(self, tokens: Sequence[Token]) -> None:
        for t in tokens:
            if t not in self._constants and t not in self._variables:
                raise MMDSLError(f"undeclared token in expression: '{t}'")

    # -----------------
    # DSL methods
    # -----------------
    def comment(self, text: str) -> MMBuilder:
        self._emit.comment(text, self._origin.here())
        return self

    def c(self, *symbols: str) -> MMBuilder:
        if not symbols:
            raise MMDSLError("$c must declare at least one symbol")
        for s in symbols:
            if s in self._variables:
                raise MMDSLError(f"token '{s}' already declared as $v")
            self._constants.add(s)
        self._emit.const_decl(symbols, self._origin.here())
        return self

    def v(self, *symbols: str) -> MMBuilder:
        if not symbols:
            raise MMDSLError("$v must declare at least one symbol")
        for s in symbols:
            if s in self._constants:
                raise MMDSLError(f"token '{s}' already declared as $c")
            self._variables.add(s)
        self._emit.var_decl(symbols, self._origin.here())
        return self

    def f(self, label: str, typecode: TypeCode, var: str) -> MMBuilder:
        if var not in self._variables:
            raise MMDSLError(f"$f variable '{var}' not declared via $v")
        if typecode not in self._constants:
            raise MMDSLError(f"$f typecode '{typecode}' not declared via $c")
        self._register_label(label)
        self._scope.activate_f(var, label)
        self._emit.floating_hyp(label, typecode, var, self._origin.here())
        return self

    def e(
        self, label: str, typecode: TypeCode, eexpr: Sequence[str] | str
    ) -> MMBuilder:
        if self._strict and self._scope.is_top_level:
            raise MMDSLError(
                "$e at top level is forbidden in strict mode; wrap it in ${ ... $}"
            )
        if typecode not in self._constants:
            raise MMDSLError(f"$e typecode '{typecode}' not declared via $c")
        tokens = eexpr.split() if isinstance(eexpr, str) else list(eexpr)
        if not tokens:
            raise MMDSLError("$e expression must be non-empty")
        self._check_expr_tokens_declared(tokens)
        self._register_label(label)
        self._scope.activate_e(label)
        self._emit.essential_hyp(label, typecode, tokens, self._origin.here())
        return self

    def a(
        self, label: str, typecode: TypeCode, aexpr: Sequence[str] | str
    ) -> MMBuilder:
        if typecode not in self._constants:
            raise MMDSLError(f"$a typecode '{typecode}' not declared via $c")
        tokens = aexpr.split() if isinstance(aexpr, str) else list(aexpr)
        if not tokens:
            raise MMDSLError("$a expression must be non-empty")
        self._check_expr_tokens_declared(tokens)
        self._register_label(label)
        self._emit.axiom(label, typecode, tokens, self._origin.here())
        return self

    def p(
        self,
        label: str,
        typecode: TypeCode,
        pexpr: Sequence[str] | str,
        proof: Sequence[ProofStep] | str,
        *,
        comment: str | None = None,
    ) -> MMBuilder:
        if typecode not in self._constants:
            raise MMDSLError(f"$p typecode '{typecode}' not declared via $c")
        expr_tokens = pexpr.split() if isinstance(pexpr, str) else list(pexpr)
        if not expr_tokens:
            raise MMDSLError("$p expression must be non-empty")
        self._check_expr_tokens_declared(expr_tokens)

        # normalize proof
        proof_steps: Sequence[ProofStep]
        if isinstance(proof, str):
            proof_steps = tuple(proof.split())
        else:
            proof_steps = tuple(proof)
        if not proof_steps:
            raise MMDSLError("$p proof must be non-empty")

        visible = self._scope.visible_labels()
        rendered_steps: list[str] = []
        rendered_step_ids: list[int] = []
        for step in proof_steps:
            sid = self._next_step_id
            self._next_step_id += 1
            if isinstance(step, Theorem):
                self._requires.add(step.fqname)
                rendered_steps.append(step.label)
            else:
                if step not in visible:
                    raise MMDSLError(
                        f"proof step '{step}' is not a visible label at this point"
                    )
                rendered_steps.append(step)
            rendered_step_ids.append(sid)

        if comment:
            self.comment(comment)

        self._register_label(label)
        self._emit.theorem(
            label,
            typecode,
            expr_tokens,
            rendered_steps,
            self._origin.here(),
            proof_step_ids=rendered_step_ids,
        )
        return self


@dataclass
class _BlockCtx:
    mm: MMBuilder

    def __enter__(self) -> MMBuilder:
        self.mm._push_scope()
        return self.mm

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> Literal[False]:
        if exc_type is None:
            self.mm._pop_scope()
        return False
