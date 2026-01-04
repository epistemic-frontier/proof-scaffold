# skfd/builder/builder.py
from __future__ import annotations

from collections.abc import Sequence
from types import TracebackType
from typing import Literal

from skfd.core.errors import MMDSLError
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolId, SymbolInterner
from skfd.core.unit import ProofUnitIR

from .origin_adapter import InspectOriginAdapter, OriginProvider
from .scope import ScopeStack
from .visitor import BuilderVisitor
from .visitor_lir import LIRVisitor
from .visitor_text import TextVisitor


class MMBuilder:
    """
    Orchestrator for the Metamath DSL.
    Adapts local string-based API to global Symbol/Origin tables.
    """

    def __init__(
        self,
        *,
        interner: SymbolInterner,
        origin_table: OriginTable,
        module_id: str,
        ascii_comments: bool = True,
    ) -> None:
        # Tables
        self._interner = interner
        self._origin_table = origin_table
        self._module_id = module_id

        # Internal state
        self._constants: set[str] = set()
        self._variables: set[str] = set()
        self._labels: set[str] = set()
        
        # Origin provider
        self._origin: OriginProvider = InspectOriginAdapter(origin_table, module_id)

        # Exports
        self._exports: set[SymbolId] = set()

        # Visitors
        self._scope = ScopeStack()
        self._text = TextVisitor(ascii_comments=ascii_comments)
        self._lir = LIRVisitor()
        self._visitors: list[BuilderVisitor] = [self._text, self._lir]

    # -----------------
    # Interning Helpers
    # -----------------
    def _intern_const(self, name: str) -> SymbolId:
        """Resolve a local const string to a global SymbolId."""
        return self._interner.intern(
            origin_module_id=self._module_id,
            local_name=name,
            kind="Const",
            origin_ref=self._origin.here_ref(depth=3), # depth adjusted for caller
        )

    def _intern_var(self, name: str) -> SymbolId:
        """Resolve a local var string to a global SymbolId."""
        return self._interner.intern(
            origin_module_id=self._module_id,
            local_name=name,
            kind="Var",
            origin_ref=self._origin.here_ref(depth=3),
        )

    def _intern_label(self, name: str) -> SymbolId:
        """Resolve a local label string to a global SymbolId."""
        return self._interner.intern(
            origin_module_id=self._module_id,
            local_name=name,
            kind="Label",
            origin_ref=self._origin.here_ref(depth=3),
        )

    def _resolve_token(self, name: str) -> SymbolId:
        """
        Resolve a math token (const or var) that MUST already be declared.
        """
        if name in self._constants:
            return self._intern_const(name)
        if name in self._variables:
            return self._intern_var(name)
        raise MMDSLError(f"undeclared token: '{name}'")

    def _resolve_proof_token(self, name: str) -> SymbolId:
        """
        Resolve a proof token (label).
        In this builder version, we assume local lookups or explicit imports.
        For now, we only support LOCAL labels or explicit SymbolIds passed in.
        """
        # TODO: Support imports from other modules.
        # For now, simplistic check:
        if name in self._labels:
            return self._intern_label(name)
        # If not local, we might try to intern it as a Label from this module,
        # but that assumes it's being DEFINED or it's a forward ref?
        # Actually, standard Metamath allows forward ref of labels? No, must be declared.
        raise MMDSLError(f"unknown label in proof: '{name}'")

    # -----------------
    # Scope helpers
    # -----------------
    def block(self) -> _BlockCtx:
        return _BlockCtx(self)

    def _push_scope(self) -> None:
        o = self._origin.here_ref()
        for v in self._visitors:
            v.open_scope(o)
        self._scope.push()

    def _pop_scope(self) -> None:
        if self._scope.depth <= 1:
            raise MMDSLError("unbalanced scope pop")
        self._scope.pop()
        o = self._origin.here_ref()
        for v in self._visitors:
            v.close_scope(o)

    # -----------------
    # Exports
    # -----------------
    def export(self, *labels: str) -> MMBuilder:
        """Mark local labels as exported."""
        for lab in labels:
            if lab not in self._labels:
                raise MMDSLError(f"cannot export unknown label '{lab}'")
            # We must look up the ID. Since it's in _labels, we can intern it to get ID.
            # (interning is idempotent)
            lid = self._intern_label(lab)
            self._exports.add(lid)
        return self

    # -----------------
    # DSL methods
    # -----------------
    def comment(self, text: str) -> MMBuilder:
        o = self._origin.here_ref()
        for v in self._visitors:
            v.comment(text, o)
        return self

    def c(self, *symbols: str) -> MMBuilder:
        if not symbols:
            raise MMDSLError("$c must declare at least one symbol")
        ids: list[SymbolId] = []
        o = self._origin.here_ref()
        for s in symbols:
            if s in self._variables:
                raise MMDSLError(f"token '{s}' already declared as $v")
            self._constants.add(s)
            # Re-intern with correct depth or reuse? 
            # Ideally we intern here.
            sid = self._interner.intern(
                origin_module_id=self._module_id,
                local_name=s,
                kind="Const",
                origin_ref=o,
            )
            ids.append(sid)
        
        for v in self._visitors:
            v.const_decl(symbols, ids, o)
        return self

    def v(self, *symbols: str) -> MMBuilder:
        if not symbols:
            raise MMDSLError("$v must declare at least one symbol")
        ids: list[SymbolId] = []
        o = self._origin.here_ref()
        for s in symbols:
            if s in self._constants:
                raise MMDSLError(f"token '{s}' already declared as $c")
            self._variables.add(s)
            sid = self._interner.intern(
                origin_module_id=self._module_id,
                local_name=s,
                kind="Var",
                origin_ref=o,
            )
            ids.append(sid)

        for v in self._visitors:
            v.var_decl(symbols, ids, o)
        return self

    def f(self, label: str, typecode: str, var: str) -> MMBuilder:
        o = self._origin.here_ref()
        if var not in self._variables:
            raise MMDSLError(f"$f variable '{var}' not declared via $v")
        if typecode not in self._constants:
            raise MMDSLError(f"$f typecode '{typecode}' not declared via $c")
        
        self._labels.add(label)
        self._scope.register_local_label(label)
        self._scope.activate_f(var, label)

        lid = self._interner.intern(
            origin_module_id=self._module_id,
            local_name=label,
            kind="Label",
            origin_ref=o
        )
        tid = self._intern_const(typecode)
        vid = self._intern_var(var)

        for v in self._visitors:
            v.floating_hyp(label, typecode, var, lid, tid, vid, o)
        return self

    def e(self, label: str, typecode: str, eexpr: Sequence[str] | str) -> MMBuilder:
        o = self._origin.here_ref()
        if typecode not in self._constants:
             raise MMDSLError(f"$e typecode '{typecode}' not declared via $c")
        
        tokens = eexpr.split() if isinstance(eexpr, str) else list(eexpr)
        token_ids = [self._resolve_token(t) for t in tokens]
        
        self._labels.add(label)
        self._scope.register_local_label(label)
        self._scope.activate_e(label)

        lid = self._interner.intern(
            origin_module_id=self._module_id,
            local_name=label,
            kind="Label",
            origin_ref=o
        )
        
        for v in self._visitors:
            v.essential_hyp(label, typecode, tokens, lid, token_ids, o)
        return self

    def a(self, label: str, typecode: str, aexpr: Sequence[str] | str) -> MMBuilder:
        o = self._origin.here_ref()
        if typecode not in self._constants:
             raise MMDSLError(f"$a typecode '{typecode}' not declared via $c")
        
        tokens = aexpr.split() if isinstance(aexpr, str) else list(aexpr)
        token_ids = [self._resolve_token(t) for t in tokens]
        
        self._labels.add(label)
        self._scope.register_local_label(label)

        lid = self._interner.intern(
            origin_module_id=self._module_id,
            local_name=label,
            kind="Label",
            origin_ref=o
        )
        
        for v in self._visitors:
            v.axiom(label, typecode, tokens, lid, token_ids, o)
        return self

    def p(
        self,
        label: str,
        typecode: str,
        pexpr: Sequence[str] | str,
        proof: Sequence[str | SymbolId] | str,
        *,
        comment: str | None = None,
    ) -> MMBuilder:
        o = self._origin.here_ref()
        if typecode not in self._constants:
             raise MMDSLError(f"$p typecode '{typecode}' not declared via $c")
        
        tokens = pexpr.split() if isinstance(pexpr, str) else list(pexpr)
        token_ids = [self._resolve_token(t) for t in tokens]

        # Proof normalization
        raw_proof: Sequence[str | SymbolId]
        if isinstance(proof, str):
            raw_proof = proof.split()
        else:
            raw_proof = proof
            
        proof_ids: list[SymbolId] = []
        proof_strs: list[str] = []
        
        for step in raw_proof:
            if isinstance(step, int): # SymbolId
                # It's an imported/explicit symbol ID
                # We need to know its name for TextEmitter?
                # This is tricky. TextEmitter needs strings.
                # If we pass a SymbolId, we might not know its name easily unless we reverse lookup?
                # Or we assume the user passes (SymbolId, name) tuple?
                # For now, let's assume we REQUIRE strings for text, or we skip text?
                # No, text is debugging.
                # Let's assume we can lookup name from interner?
                # SymbolInterner has `_defs[sid].local_name`.
                proof_ids.append(step)
                defn = self._interner.symbol_table().get(step)
                proof_strs.append(defn.local_name if defn else f"ID<{step}>")
            else:
                # String step - must be local label
                if step not in self._scope.visible_labels():
                    raise MMDSLError(f"proof step '{step}' is not visible/known")
                proof_strs.append(step)
                proof_ids.append(self._intern_label(step))

        if comment:
            self.comment(comment)

        self._labels.add(label)
        self._scope.register_local_label(label)

        lid = self._interner.intern(
            origin_module_id=self._module_id,
            local_name=label,
            kind="Label",
            origin_ref=o
        )

        for v in self._visitors:
            v.theorem(label, typecode, tokens, proof_strs, lid, token_ids, proof_ids, o)
        return self

    # -----------------
    # Output
    # -----------------
    def render(self) -> str:
        return self._text.render()

    def to_proof_unit(self, unit_id: str) -> ProofUnitIR:
        # Create final ProofUnitIR
        o = self._origin.here_ref()
        
        return ProofUnitIR(
            unit_id=unit_id,
            origin_ref=o,
            origin_module_id=self._module_id,
            lir_stmts=self._lir.lir(),
            exports=list(self._exports),
        )


class _BlockCtx:
    def __init__(self, mm: MMBuilder) -> None:
        self.mm = mm

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
