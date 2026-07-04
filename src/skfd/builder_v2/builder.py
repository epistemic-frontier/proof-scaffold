from __future__ import annotations

import re
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from types import TracebackType
from typing import Literal

from skfd.builder.origin_adapter import InspectOriginAdapter, OriginProvider
from skfd.builder.visitor_lir import LIRVisitor
from skfd.core.diag import Diagnostic, LinkerDiagError
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolDef, SymbolId, SymbolInterner, SymbolKind
from skfd.core.unit import ProofUnitIR
from skfd.names import NameResolver


@dataclass(frozen=True)
class BuildConfig:
    auto_f: bool = True
    warn_raw: bool = True
    forbid_raw: bool = False


@dataclass
class _ScopeV2:
    local_label_names: set[str]
    active_f: dict[SymbolId, SymbolId]


class _ScopeStackV2:
    def __init__(self) -> None:
        self._scopes: list[_ScopeV2] = [_ScopeV2(local_label_names=set(), active_f={})]

    @property
    def depth(self) -> int:
        return len(self._scopes)

    def push(self) -> None:
        self._scopes.append(_ScopeV2(local_label_names=set(), active_f={}))

    def pop(self) -> None:
        if len(self._scopes) <= 1:
            raise LinkerDiagError(
                Diagnostic(
                    error_code="E_UNBALANCED_SCOPE",
                    message="unbalanced scope pop",
                    primary_origin_ref=-1,
                    related_origin_refs=(),
                    origin_chain=(),
                    details={},
                )
            )
        self._scopes.pop()

    def register_local_label_name(self, name: str) -> None:
        self._scopes[-1].local_label_names.add(name)

    def label_name_is_visible(self, name: str) -> bool:
        return any(name in s.local_label_names for s in self._scopes)

    def get_active_f(self, var: SymbolId) -> SymbolId | None:
        for s in reversed(self._scopes):
            found = s.active_f.get(var)
            if found is not None:
                return found
        return None

    def active_floating_vars(self) -> list[SymbolId]:
        vars_: list[SymbolId] = []
        seen: set[SymbolId] = set()
        for scope in self._scopes:
            for var in scope.active_f:
                if var in seen:
                    continue
                vars_.append(var)
                seen.add(var)
        return vars_

    def activate_f(self, var: SymbolId, floating_label: SymbolId) -> None:
        self._scopes[-1].active_f[var] = floating_label


class SymFacade:
    def __init__(
        self,
        *,
        interner: SymbolInterner,
        origin: OriginProvider,
        origin_module_id: str,
        names: NameResolver,
    ) -> None:
        self._interner = interner
        self._origin = origin
        self._origin_module_id = origin_module_id
        self._names = names

    def const(self, name: str) -> SymbolId:
        canonical = self._names.canonicalize("Const", name)
        return self._interner.intern(
            origin_module_id=self._origin_module_id,
            local_name=canonical,
            kind="Const",
            origin_ref=self._origin.here_ref(depth=3),
        )

    def var(self, name: str) -> SymbolId:
        canonical = self._names.canonicalize("Var", name)
        return self._interner.intern(
            origin_module_id=self._origin_module_id,
            local_name=canonical,
            kind="Var",
            origin_ref=self._origin.here_ref(depth=3),
        )

    def label(self, name: str) -> SymbolId:
        canonical = self._names.canonicalize("Label", name)
        return self._interner.intern(
            origin_module_id=self._origin_module_id,
            local_name=canonical,
            kind="Label",
            origin_ref=self._origin.here_ref(depth=3),
        )


class Auto:
    def __init__(self, mm: MMBuilderV2) -> None:
        self._mm = mm

    def vars_in(self, expr: Sequence[SymbolId]) -> list[SymbolId]:
        symtab = self._mm.interner.symbol_table()
        vars_: set[SymbolId] = set()
        for t in expr:
            d = symtab.get(t)
            if d is None:
                raise LinkerDiagError(
                    Diagnostic(
                        error_code="E_UNKNOWN_SYMBOL_ID",
                        message="unknown SymbolId in expr",
                        primary_origin_ref=-1,
                        related_origin_refs=(),
                        origin_chain=(),
                        details={"symbol_id": t},
                    )
                )
            if d.kind == "Var":
                vars_.add(t)
        return sorted(vars_)

    def floating(self, var: SymbolId, *, tc: SymbolId) -> SymbolId:
        existing = self._mm._scope.get_active_f(var)
        if existing is not None:
            return existing

        symtab = self._mm.interner.symbol_table()
        var_def = symtab.get(var)
        if var_def is None or var_def.kind != "Var":
            raise LinkerDiagError(
                Diagnostic(
                    error_code="E_EXPECT_VAR",
                    message="auto.floating expects a Var symbol",
                    primary_origin_ref=-1,
                    related_origin_refs=(),
                    origin_chain=(),
                    details={"symbol_id": var},
                )
            )

        base = f"w{var_def.local_name}"
        label_name = base
        suffix = 0
        while self._mm._scope.label_name_is_visible(label_name) or self._mm._label_name_used(
            label_name
        ):
            label_name = f"{base}{suffix}"
            suffix += 1

        label_id = self._mm.sym.label(label_name)
        self._mm.f(label_id, tc=tc, var=var)
        return label_id

    def use_existing_floating(self, var: SymbolId, *, label: SymbolId) -> SymbolId:
        """Mark an already-emitted `$f` label as active for auto-$f lookup."""
        self._mm._require_kind(var, "Var")
        self._mm._require_kind(label, "Label")
        self._mm._scope.activate_f(var, label)
        return label

    def mandatory_f(self, expr: Sequence[SymbolId], *, tc: SymbolId) -> list[SymbolId]:
        return [self.floating(v, tc=tc) for v in self.vars_in(expr)]


class MMBuilderV2:
    def __init__(
        self,
        *,
        interner: SymbolInterner,
        origin_table: OriginTable,
        names: NameResolver,
        unit_id: str,
        origin_module_id: str,
        cfg: BuildConfig | None = None,
    ) -> None:
        self.interner = interner
        self._origin_table = origin_table
        self._origin_module_id = origin_module_id
        self._unit_id = unit_id
        self.cfg = cfg if cfg is not None else BuildConfig()
        self.names = names

        self._origin: OriginProvider = InspectOriginAdapter(origin_table, origin_module_id)
        self._lir = LIRVisitor()
        self._scope = _ScopeStackV2()
        self._exports: set[SymbolId] = set()
        self._labels_used: dict[str, int] = {}

        self.sym = SymFacade(
            interner=self.interner,
            origin=self._origin,
            origin_module_id=self._origin_module_id,
            names=self.names,
        )
        self.auto = Auto(self)

    def block(self) -> _BlockCtxV2:
        return _BlockCtxV2(self)

    def _push_scope(self) -> None:
        o = self._origin.here_ref()
        self._lir.open_scope(o)
        self._scope.push()

    def _pop_scope(self) -> None:
        self._scope.pop()
        o = self._origin.here_ref()
        self._lir.close_scope(o)

    def _label_name_used(self, local_name: str) -> bool:
        return local_name in self._labels_used

    def _first_label_origin(self, local_name: str) -> int:
        return self._labels_used.get(local_name, -1)

    @staticmethod
    def _suspect_label_name(label_name: str) -> bool:
        """Return True for generic label names likely to collide across functions."""
        _SUSPECT = frozenset({"hyp", "h1", "h2", "h3"})
        if label_name in _SUSPECT:
            return True
        # Single-word labels without theorem-scoping delimiter
        if not re.search(r"[._]", label_name):
            return True
        return False

    def _duplicate_label_error(self, label_name: str) -> LinkerDiagError:
        first_origin = self._first_label_origin(label_name)
        current_origin = self._origin.here_ref()
        return LinkerDiagError(
            Diagnostic(
                error_code="E_DUPLICATE_LABEL",
                message=f'duplicate label "{label_name}" in unit',
                primary_origin_ref=first_origin,
                related_origin_refs=(current_origin,) if current_origin != -1 else (),
                origin_chain=(
                    {"label": label_name, "origin_ref": first_origin, "role": "first_definition"},
                    {"label": label_name, "origin_ref": current_origin, "role": "duplicate"},
                ) if first_origin != -1 else (),
                details={"label": label_name, "first_origin_ref": first_origin},
            )
        )

    def _require_kind(self, sid: SymbolId, kind: SymbolKind) -> SymbolDef:
        symtab = self.interner.symbol_table()
        d = symtab.get(sid)
        if d is None or d.kind != kind:
            raise LinkerDiagError(
                Diagnostic(
                    error_code="E_SYMBOL_KIND_MISMATCH",
                    message="symbol kind mismatch",
                    primary_origin_ref=-1,
                    related_origin_refs=(),
                    origin_chain=(),
                    details={
                        "symbol_id": sid,
                        "expected_kind": kind,
                        "actual_kind": d.kind if d is not None else None,
                    },
                )
            )
        return d

    def _require_local_label(self, label: SymbolId) -> str:
        d = self._require_kind(label, "Label")
        if d.origin_module_id != self._origin_module_id:
            raise LinkerDiagError(
                Diagnostic(
                    error_code="E_NONLOCAL_LABEL",
                    message="statement label must be local to the unit",
                    primary_origin_ref=-1,
                    related_origin_refs=(),
                    origin_chain=(),
                    details={
                        "label_id": label,
                        "label_origin_module_id": d.origin_module_id,
                        "unit_origin_module_id": self._origin_module_id,
                    },
                )
            )
        return d.local_name

    def comment(self, text: str) -> None:
        o = self._origin.here_ref()
        self._lir.comment(text, o)

    def d(self, *vars: SymbolId) -> None:
        if len(vars) < 2:
            raise LinkerDiagError(
                Diagnostic(
                    error_code="E_BAD_DISJOINT",
                    message="$d must have at least 2 variables",
                    primary_origin_ref=-1,
                    related_origin_refs=(),
                    origin_chain=(),
                    details={"vars": list(vars)},
                )
            )
        for v in vars:
            self._require_kind(v, "Var")
        o = self._origin.here_ref()
        self._lir.disjoint_var(tuple("" for _ in vars), list(vars), o)

    def export(self, *symbols: SymbolId) -> None:
        for sid in symbols:
            self._exports.add(sid)

    def exports(self) -> set[SymbolId]:
        return set(self._exports)

    def active_floating_vars(self) -> list[SymbolId]:
        return self._scope.active_floating_vars()

    def f(self, label: SymbolId, *, tc: SymbolId, var: SymbolId) -> SymbolId:
        label_name = self._require_local_label(label)
        self._require_kind(tc, "Const")
        self._require_kind(var, "Var")

        if self._label_name_used(label_name):
            raise self._duplicate_label_error(label_name)
        self._labels_used[label_name] = self._origin.here_ref()
        self._scope.register_local_label_name(label_name)
        self._scope.activate_f(var, label)

        o = self._origin.here_ref()
        self._lir.floating_hyp(label_name, "", "", label, tc, var, o)
        return label

    def e(self, label: SymbolId, *, tc: SymbolId, expr: Sequence[SymbolId]) -> SymbolId:
        label_name = self._require_local_label(label)
        self._require_kind(tc, "Const")
        for t in expr:
            self._require_kind(t, "Const" if self._is_const(t) else "Var")

        if self._label_name_used(label_name):
            raise self._duplicate_label_error(label_name)
        if self._suspect_label_name(label_name):
            warnings.warn(
                f'label "{label_name}" in hypothesis is generic and will collide '
                f"across prove_* functions during multi-proof emit. "
                f"This is not a framework error, but consider using a scoped label: "
                "lb.hyp('<theorem>.1', ...) instead.",
                RuntimeWarning,
                stacklevel=3,
            )
        self._labels_used[label_name] = self._origin.here_ref()
        self._scope.register_local_label_name(label_name)

        o = self._origin.here_ref()
        self._lir.essential_hyp(label_name, "", ["" for _ in expr], label, tc, list(expr), o)
        return label

    def a(self, label: SymbolId, *, tc: SymbolId, expr: Sequence[SymbolId]) -> SymbolId:
        label_name = self._require_local_label(label)
        self._require_kind(tc, "Const")
        for t in expr:
            self._require_token(t)

        if self._label_name_used(label_name):
            raise self._duplicate_label_error(label_name)
        self._labels_used[label_name] = self._origin.here_ref()
        self._scope.register_local_label_name(label_name)

        if self.cfg.auto_f:
            symtab = self.interner.symbol_table()
            tc_def = symtab.get(tc)
            if tc_def is not None and tc_def.kind == "Const" and tc_def.local_name == "wff":
                self.auto.mandatory_f(expr, tc=tc)

        o = self._origin.here_ref()
        self._lir.axiom(label_name, "", ["" for _ in expr], label, tc, list(expr), o)
        return label

    def p(
        self,
        label: SymbolId,
        *,
        tc: SymbolId,
        expr: Sequence[SymbolId],
        proof: Sequence[SymbolId],
    ) -> SymbolId:
        label_name = self._require_local_label(label)
        self._require_kind(tc, "Const")
        for t in expr:
            self._require_token(t)
        for step in proof:
            self._require_kind(step, "Label")

        if self._label_name_used(label_name):
            raise self._duplicate_label_error(label_name)
        self._labels_used[label_name] = self._origin.here_ref()
        self._scope.register_local_label_name(label_name)

        if self.cfg.auto_f:
            symtab = self.interner.symbol_table()
            tc_def = symtab.get(tc)
            if tc_def is not None and tc_def.kind == "Const" and tc_def.local_name == "wff":
                self.auto.mandatory_f(expr, tc=tc)

        o = self._origin.here_ref()
        self._lir.theorem(
            label_name,
            "",
            ["" for _ in expr],
            ["" for _ in proof],
            label,
            tc,
            list(expr),
            list(proof),
            o,
        )
        return label

    def _is_const(self, sid: SymbolId) -> bool:
        symtab = self.interner.symbol_table()
        d = symtab.get(sid)
        if d is None:
            return False
        return d.kind == "Const"

    def _require_token(self, sid: SymbolId) -> None:
        symtab = self.interner.symbol_table()
        d = symtab.get(sid)
        if d is None or d.kind not in ("Const", "Var"):
            raise LinkerDiagError(
                Diagnostic(
                    error_code="E_BAD_MATH_TOKEN",
                    message="math token must be Const or Var",
                    primary_origin_ref=-1,
                    related_origin_refs=(),
                    origin_chain=(),
                    details={
                        "symbol_id": sid,
                        "actual_kind": d.kind if d is not None else None,
                    },
                )
            )

    def finish(self) -> ProofUnitIR:
        o = self._origin.here_ref()
        return ProofUnitIR(
            unit_id=self._unit_id,
            origin_ref=o,
            origin_module_id=self._origin_module_id,
            lir_stmts=self._lir.lir(),
            exports=sorted(self._exports),
        )


class _BlockCtxV2:
    def __init__(self, mm: MMBuilderV2) -> None:
        self._mm = mm

    def __enter__(self) -> MMBuilderV2:
        self._mm._push_scope()
        return self._mm

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> Literal[False]:
        if exc_type is None:
            self._mm._pop_scope()
        return False
