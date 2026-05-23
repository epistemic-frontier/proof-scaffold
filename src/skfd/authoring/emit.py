from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, cast

from skfd.builder_v2 import MMBuilderV2
from skfd.core.diag import Diagnostic, LinkerDiagError
from skfd.core.symbols import SymbolId
from skfd.core.symbols import SymbolInterner

from .formula import Wff


class AxiomProvider(Protocol):
    @property
    def interner(self) -> SymbolInterner:
        ...

    def compile_axioms(self) -> Mapping[str, Wff]:
        ...


def emit_axioms(
    mm: MMBuilderV2,
    provider: AxiomProvider,
    typecode: str | SymbolId = "wff",
    *,
    label_ids: Mapping[str, SymbolId] | None = None,
) -> None:
    if provider.interner is not mm.interner:
        raise LinkerDiagError(
            Diagnostic(
                error_code="E_INTERNER_MISMATCH",
                message="provider.interner must be the same global interner as ctx.mm.interner",
                primary_origin_ref=-1,
                related_origin_refs=(),
                origin_chain=(),
                details={},
            )
        )
    tc = typecode if isinstance(typecode, int) else mm.sym.const(typecode)
    for label, wff in provider.compile_axioms().items():
        label_id = mm.sym.label(label)
        if label_ids is not None:
            label_id = label_ids.get(label, label_id)
        mm.a(label_id, tc=tc, expr=wff.tokens)


class LemmaStepLike(Protocol):
    @property
    def wff(self) -> Wff:
        ...


class LemmaLike(Protocol):
    @property
    def name(self) -> str:
        ...

    @property
    def statement(self) -> Wff:
        ...

    @property
    def steps(self) -> Sequence[LemmaStepLike]:
        ...


def emit_lemmas(
    mm: MMBuilderV2,
    provider: AxiomProvider,
    lemmas: Sequence[LemmaLike],
    typecode: str | SymbolId = "wff",
) -> None:
    if provider.interner is not mm.interner:
        raise LinkerDiagError(
            Diagnostic(
                error_code="E_INTERNER_MISMATCH",
                message="provider.interner must be the same global interner as ctx.mm.interner",
                primary_origin_ref=-1,
                related_origin_refs=(),
                origin_chain=(),
                details={},
            )
        )
    if lemmas:
        steps0 = getattr(lemmas[0], "steps", ())
        if steps0 and getattr(steps0[0], "op", None) is not None:
            emit_lowered_lemmas(mm, provider, cast(Sequence[LoweredLemmaLike], lemmas), typecode=typecode)
            return

    tc = typecode if isinstance(typecode, int) else mm.sym.const(typecode)
    for lemma in lemmas:
        mm.a(mm.sym.label(lemma.name), tc=tc, expr=lemma.statement.tokens)


class LoweredStepLike(LemmaStepLike, Protocol):
    @property
    def label(self) -> str:
        ...

    @property
    def op(self) -> str:
        ...

    @property
    def args(self) -> Sequence[str]:
        ...

    @property
    def ref(self) -> str | None:
        ...


class LoweredLemmaLike(LemmaLike, Protocol):
    @property
    def steps(self) -> Sequence[LoweredStepLike]:
        ...


def emit_lowered_lemmas(
    mm: MMBuilderV2,
    provider: AxiomProvider,
    lemmas: Sequence[LemmaLike],
    typecode: str | SymbolId = "wff",
    wff_typecode: str | SymbolId = "wff",
    *,
    label_ids: Mapping[str, SymbolId] | None = None,
    floating_by_var: Mapping[SymbolId, SymbolId] | None = None,
) -> None:
    lemmas = cast(Sequence[LoweredLemmaLike], lemmas)
    if provider.interner is not mm.interner:
        raise LinkerDiagError(
            Diagnostic(
                error_code="E_INTERNER_MISMATCH",
                message="provider.interner must be the same global interner as ctx.mm.interner",
                primary_origin_ref=-1,
                related_origin_refs=(),
                origin_chain=(),
                details={},
            )
        )

    theorem_tc = typecode if isinstance(typecode, int) else mm.sym.const(typecode)
    wff_tc = wff_typecode if isinstance(wff_typecode, int) else mm.sym.const(wff_typecode)

    def v2_resolve_label(name: str) -> SymbolId:
        if label_ids is not None:
            sid = label_ids.get(name)
            if sid is not None:
                return sid
        return mm.sym.label(name)

    b = getattr(provider, "builtins", None)
    if b is None:
        raise ValueError("emit_lowered_lemmas: provider is missing .builtins")
    b2 = cast(Any, b)

    lp = b2.lp
    rp = b2.rp
    imp_tok = b2.imp

    stmt_by_label: dict[str, tuple[int, ...]] = {
        k: tuple(v.tokens) for k, v in provider.compile_axioms().items()
    }
    hyps_by_label: dict[str, tuple[tuple[int, ...], ...]] = {}
    for lemma in lemmas:
        stmt_by_label[lemma.name] = tuple(lemma.statement.tokens)
        hyps: list[tuple[int, ...]] = []
        for st in lemma.steps:
            if getattr(st, "op", None) == "hyp":
                hyps.append(tuple(st.wff.tokens))
        if hyps:
            hyps_by_label[lemma.name] = tuple(hyps)
    ph_tpl = mm.interner.intern(
        origin_module_id="__tpl__",
        local_name="__ph",
        kind="Var",
        origin_ref=0,
    )
    ps_tpl = mm.interner.intern(
        origin_module_id="__tpl__",
        local_name="__ps",
        kind="Var",
        origin_ref=0,
    )
    stmt_by_label.setdefault("wi", (lp, ph_tpl, b2.imp, ps_tpl, rp))
    stmt_by_label.setdefault("wn", (b2.neg, ph_tpl))
    stmt_by_label.setdefault("wa", (lp, ph_tpl, b2.and_, ps_tpl, rp))
    symtab = provider.interner.symbol_table()

    def floating_var_order() -> list[SymbolId]:
        if floating_by_var is not None:
            return list(floating_by_var)
        return mm.active_floating_vars()

    def mandatory_vars_for_templates(
        templates: Sequence[Sequence[SymbolId]],
    ) -> list[SymbolId]:
        needed: set[SymbolId] = set()
        for template in templates:
            needed |= set(mm.auto.vars_in(template))

        ordered: list[SymbolId] = []
        for var in floating_var_order():
            if var in needed:
                ordered.append(var)
                needed.remove(var)
        ordered.extend(sorted(needed))
        return ordered

    def ph_ps_mandatory_substs(
        ph_subst: tuple[int, ...],
        ps_subst: tuple[int, ...],
    ) -> list[tuple[int, ...]]:
        order = floating_var_order()
        names = {var: symtab[var].local_name for var in order if var in symtab}
        ph_idx = next((i for i, var in enumerate(order) if names.get(var) == "ph"), None)
        ps_idx = next((i for i, var in enumerate(order) if names.get(var) == "ps"), None)
        if ph_idx is not None and ps_idx is not None and ps_idx < ph_idx:
            return [ps_subst, ph_subst]
        return [ph_subst, ps_subst]

    def v2_split_binary(
        tokens: Sequence[int], op_token: int, *, lp: int, rp: int
    ) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
        toks = tuple(tokens)
        if len(toks) < 5 or toks[0] != lp or toks[-1] != rp:
            return None
        inner = toks[1:-1]
        depth = 0
        split_at: int | None = None
        for i, t in enumerate(inner):
            if t == lp:
                depth += 1
            elif t == rp:
                depth -= 1
                if depth < 0:
                    return None
            elif t == op_token and depth == 0:
                split_at = i
                break
        if depth != 0 or split_at is None:
            return None
        left = inner[:split_at]
        right = inner[split_at + 1 :]
        if not left or not right:
            return None
        return tuple(left), tuple(right)

    def v2_wff_proof(tokens: Sequence[int]) -> list[SymbolId]:
        toks = tuple(tokens)
        if not toks:
            raise ValueError("wff proof: empty token seq")

        if len(toks) == 1 and symtab[toks[0]].kind == "Var":
            if floating_by_var is not None:
                f = floating_by_var.get(toks[0])
                if f is None:
                    d = symtab.get(toks[0])
                    raise LinkerDiagError(
                        Diagnostic(
                            error_code="E_MISSING_FLOATING_HYP",
                            message="missing floating hypothesis for Var symbol",
                            primary_origin_ref=-1,
                            related_origin_refs=(),
                            origin_chain=(),
                            details={
                                "var_id": toks[0],
                                "var_local_name": None if d is None else d.local_name,
                            },
                        )
                    )
                return [f]
            return [mm.auto.floating(toks[0], tc=wff_tc)]

        if toks[0] == b2.neg:
            return [*v2_wff_proof(toks[1:]), v2_resolve_label("wn")]

        imp_parts = v2_split_binary(toks, b2.imp, lp=b2.lp, rp=b2.rp)
        if imp_parts is not None:
            left, right = imp_parts
            imp_proof: list[SymbolId] = []
            for subst_tokens in ph_ps_mandatory_substs(left, right):
                imp_proof.extend(v2_wff_proof(subst_tokens))
            imp_proof.append(v2_resolve_label("wi"))
            return imp_proof

        and_parts = v2_split_binary(toks, b2.and_, lp=b2.lp, rp=b2.rp)
        if and_parts is not None:
            left, right = and_parts
            and_proof: list[SymbolId] = []
            for subst_tokens in ph_ps_mandatory_substs(left, right):
                and_proof.extend(v2_wff_proof(subst_tokens))
            and_proof.append(v2_resolve_label("wa"))
            return and_proof

        raise ValueError(f"wff proof: unsupported token shape (len={len(toks)})")

    class _Ast:
        __slots__ = ()

    class _Atom(_Ast):
        __slots__ = ("tok",)

        def __init__(self, tok: int) -> None:
            self.tok = tok

        def __eq__(self, other: object) -> bool:
            return isinstance(other, _Atom) and self.tok == other.tok

    class _Not(_Ast):
        __slots__ = ("x",)

        def __init__(self, x: _Ast) -> None:
            self.x = x

        def __eq__(self, other: object) -> bool:
            return isinstance(other, _Not) and self.x == other.x

    class _Bin(_Ast):
        __slots__ = ("op", "l", "r")

        def __init__(self, op: int, left: _Ast, right: _Ast) -> None:
            self.op = op
            self.l = left
            self.r = right

        def __eq__(self, other: object) -> bool:
            return (
                isinstance(other, _Bin)
                and self.op == other.op
                and self.l == other.l
                and self.r == other.r
            )

    def _parse(tokens: Sequence[int]) -> _Ast:
        toks = tuple(tokens)
        if not toks:
            raise ValueError("parse: empty tokens")
        if len(toks) == 1:
            return _Atom(toks[0])
        if toks[0] == b2.neg:
            return _Not(_parse(toks[1:]))
        imp_parts = v2_split_binary(toks, b2.imp, lp=lp, rp=rp)
        if imp_parts is not None:
            left, right = imp_parts
            return _Bin(b2.imp, _parse(left), _parse(right))
        and_parts = v2_split_binary(toks, b2.and_, lp=lp, rp=rp)
        if and_parts is not None:
            left, right = and_parts
            return _Bin(b2.and_, _parse(left), _parse(right))
        raise ValueError("parse: unsupported token shape")

    def _to_tokens(ast: _Ast) -> tuple[int, ...]:
        if isinstance(ast, _Atom):
            return (ast.tok,)
        if isinstance(ast, _Not):
            return (b2.neg, *_to_tokens(ast.x))
        if isinstance(ast, _Bin):
            if ast.op == b2.imp:
                return (lp, *_to_tokens(ast.l), b2.imp, *_to_tokens(ast.r), rp)
            if ast.op == b2.and_:
                return (lp, *_to_tokens(ast.l), b2.and_, *_to_tokens(ast.r), rp)
        raise ValueError("to_tokens: unsupported ast")

    def _apply_subst(ast: _Ast, subst: Mapping[int, _Ast]) -> _Ast:
        if isinstance(ast, _Atom) and symtab[ast.tok].kind == "Var":
            return subst.get(ast.tok, ast)
        if isinstance(ast, _Not):
            return _Not(_apply_subst(ast.x, subst))
        if isinstance(ast, _Bin):
            return _Bin(ast.op, _apply_subst(ast.l, subst), _apply_subst(ast.r, subst))
        return ast

    def _unify(template: _Ast, target: _Ast, subst: dict[int, _Ast]) -> None:
        if isinstance(template, _Atom) and symtab[template.tok].kind == "Var":
            existing = subst.get(template.tok)
            if existing is None:
                subst[template.tok] = target
                return
            if existing != target:
                raise ValueError("unify: inconsistent substitution")
            return
        if type(template) is not type(target):
            raise ValueError("unify: node kind mismatch")
        if isinstance(template, _Atom):
            if template.tok != cast(_Atom, target).tok:
                raise ValueError("unify: atom mismatch")
            return
        if isinstance(template, _Not):
            _unify(template.x, cast(_Not, target).x, subst)
            return
        if isinstance(template, _Bin):
            t = cast(_Bin, target)
            if template.op != t.op:
                raise ValueError("unify: op mismatch")
            _unify(template.l, t.l, subst)
            _unify(template.r, t.r, subst)
            return
        raise ValueError("unify: unsupported ast")

    def v2_emit_step(
        label: str, *, visiting: set[str], steps: Mapping[str, LoweredStepLike]
    ) -> list[SymbolId]:
        if label in visiting:
            raise ValueError(f"cycle detected at step {label!r}")
        step = steps.get(label)
        if step is None:
            raise ValueError(f"unknown step label {label!r}")

        if step.op == "hyp":
            return [mm.sym.label(label)]

        visiting.add(label)
        try:
            if step.op == "ref":
                if step.ref is None:
                    raise ValueError(f"step {label!r}: missing ref label")
                tmpl_tokens = stmt_by_label.get(step.ref)
                if tmpl_tokens is None:
                    raise LinkerDiagError(
                        Diagnostic(
                            error_code="E_UNKNOWN_LABEL_NAME",
                            message="unknown proof label name",
                            primary_origin_ref=-1,
                            related_origin_refs=(),
                            origin_chain=(),
                            details={"label": step.ref},
                        )
                    )
                hyp_templates = hyps_by_label.get(step.ref, ())
                subst: dict[int, _Ast] = {}
                try:
                    _unify(_parse(tmpl_tokens), _parse(step.wff.tokens), subst)
                except ValueError as e:
                    raise ValueError(
                        f"step {label!r}: ref unify failed for {step.ref!r}: {e}"
                    ) from e

                if step.args:
                    if len(step.args) != len(hyp_templates):
                        raise ValueError(
                            f"step {label!r}: ref to {step.ref!r} expects {len(hyp_templates)} hyp args, got {len(step.args)}"
                        )
                    for arg_label, hyp_toks in zip(step.args, hyp_templates, strict=True):
                        arg_step = steps.get(arg_label)
                        if arg_step is None:
                            raise ValueError(
                                f"step {label!r}: unknown ref arg step label {arg_label!r}"
                            )
                        try:
                            _unify(_parse(hyp_toks), _parse(arg_step.wff.tokens), subst)
                        except ValueError as e:
                            raise ValueError(
                                f"step {label!r}: ref hyp unify failed for {step.ref!r}: {e}"
                            ) from e
                elif hyp_templates:
                    raise ValueError(
                        f"step {label!r}: ref to {step.ref!r} requires {len(hyp_templates)} hyp arg(s)"
                    )

                mandatory_vars = mandatory_vars_for_templates((tmpl_tokens, *hyp_templates))
                proof: list[SymbolId] = []
                for v in mandatory_vars:
                    proof.extend(v2_wff_proof(_to_tokens(subst.get(v, _Atom(v)))))

                if step.args:
                    for arg_label, hyp_toks in zip(step.args, hyp_templates, strict=True):
                        instantiated = _to_tokens(_apply_subst(_parse(hyp_toks), subst))
                        arg_step = steps.get(arg_label)
                        if arg_step is None:
                            raise ValueError(
                                f"step {label!r}: unknown ref arg step label {arg_label!r}"
                            )
                        if tuple(arg_step.wff.tokens) != instantiated:
                            raise ValueError(
                                f"step {label!r}: ref hyp mismatch for {step.ref!r}"
                            )
                        proof.extend(v2_emit_step(arg_label, visiting=visiting, steps=steps))

                proof.append(v2_resolve_label(step.ref))
                return proof

            if step.op in {"mp", "apply"}:
                if step.op == "apply":
                    if step.ref is None:
                        raise ValueError(f"step {label!r}: apply is missing rule label")
                    if step.ref != "mp":
                        raise ValueError(
                            f"step {label!r}: unsupported apply rule {step.ref!r} for lowering"
                        )

                if len(step.args) != 2:
                    raise ValueError(f"step {label!r}: mp expects 2 args, got {len(step.args)}")
                maj, minor = step.args[0], step.args[1]
                maj_step = steps.get(maj)
                minor_step = steps.get(minor)
                if maj_step is None or minor_step is None:
                    raise ValueError(f"step {label!r}: mp args must reference prior steps")

                minor_parts = v2_split_binary(minor_step.wff.tokens, imp_tok, lp=lp, rp=rp)
                if minor_parts is None:
                    raise ValueError(f"step {label!r}: mp minor is not an implication")
                antecedent, consequent = minor_parts
                if tuple(maj_step.wff.tokens) != antecedent:
                    raise ValueError(f"step {label!r}: mp antecedent mismatch")
                mandatory_proofs: list[SymbolId] = []
                for subst_tokens in ph_ps_mandatory_substs(antecedent, consequent):
                    mandatory_proofs.extend(v2_wff_proof(subst_tokens))
                return [
                    *mandatory_proofs,
                    *v2_emit_step(maj, visiting=visiting, steps=steps),
                    *v2_emit_step(minor, visiting=visiting, steps=steps),
                    v2_resolve_label("mp"),
                ]

            raise ValueError(f"step {label!r}: unknown op {step.op!r}")
        finally:
            visiting.remove(label)

    lemma_by_name: dict[str, LoweredLemmaLike] = {lemma.name: lemma for lemma in lemmas}
    allowed_ops_for_theorem: set[str] = {"hyp", "ref", "mp", "apply"}
    emit_as_axiom: set[str] = set()
    for lemma in lemmas:
        unsupported: list[dict[str, Any]] = []
        for step in lemma.steps:
            op = getattr(step, "op", None)
            if op not in allowed_ops_for_theorem:
                unsupported.append({"step": step.label, "op": op})
        if unsupported:
            if mm.cfg.forbid_raw:
                raise LinkerDiagError(
                    Diagnostic(
                        error_code="E_RAW_NOT_ALLOWED",
                        message="raw/unsupported proof steps are forbidden at this conformance level",
                        primary_origin_ref=-1,
                        related_origin_refs=(),
                        origin_chain=(),
                        details={"lemma": lemma.name, "unsupported": unsupported},
                    )
                )
            if mm.cfg.warn_raw:
                warnings.warn(
                    f"raw/unsupported proof steps in lemma {lemma.name!r}; emitting it as an axiom",
                    RuntimeWarning,
                    stacklevel=2,
                )
            emit_as_axiom.add(lemma.name)

    deps_by_name: dict[str, set[str]] = {}
    for lemma in lemmas:
        deps: set[str] = set()
        if lemma.name in emit_as_axiom:
            deps_by_name[lemma.name] = deps
            continue
        for step in lemma.steps:
            if getattr(step, "op", None) != "ref":
                continue
            ref = getattr(step, "ref", None)
            if not isinstance(ref, str) or not ref:
                continue
            if ref == lemma.name:
                raise LinkerDiagError(
                    Diagnostic(
                        error_code="E_SELF_REFERENCE",
                        message="lemma proof references itself",
                        primary_origin_ref=-1,
                        related_origin_refs=(),
                        origin_chain=(),
                        details={"lemma": lemma.name, "ref": ref, "step": step.label},
                    )
                )
            if ref in lemma_by_name:
                deps.add(ref)
        deps_by_name[lemma.name] = deps

    pending: dict[str, set[str]] = {k: set(v) for k, v in deps_by_name.items()}
    ready: list[str] = sorted([name for name, deps in pending.items() if not deps])
    in_ready: set[str] = set(ready)
    ordered: list[LoweredLemmaLike] = []
    while ready:
        name = ready.pop(0)
        in_ready.remove(name)
        ordered.append(lemma_by_name[name])
        pending.pop(name, None)
        for other, deps in pending.items():
            if name in deps:
                deps.remove(name)
                if not deps and other not in in_ready:
                    ready.append(other)
                    in_ready.add(other)
        ready.sort()
    if pending:
        cycle_nodes = sorted(pending.keys())
        raise LinkerDiagError(
            Diagnostic(
                error_code="E_CIRCULAR_DEPENDENCY",
                message="circular lemma dependency detected",
                primary_origin_ref=-1,
                related_origin_refs=(),
                origin_chain=(),
                details={"cycle": cycle_nodes},
            )
        )

    for lemma in ordered:
        if lemma.name in emit_as_axiom:
            mm.a(mm.sym.label(lemma.name), tc=theorem_tc, expr=lemma.statement.tokens)
            continue
        with mm.block():
            step_by_label_v2: dict[str, LoweredStepLike] = {s.label: s for s in lemma.steps}

            vars_needed: set[SymbolId] = set(mm.auto.vars_in(lemma.statement.tokens))
            for step in lemma.steps:
                if step.op == "hyp":
                    vars_needed |= set(mm.auto.vars_in(step.wff.tokens))
            for v in sorted(vars_needed):
                if floating_by_var is not None and v in floating_by_var:
                    continue
                mm.auto.floating(v, tc=wff_tc)

            for step in lemma.steps:
                if step.op == "hyp":
                    mm.e(mm.sym.label(step.label), tc=theorem_tc, expr=step.wff.tokens)

            if not lemma.steps:
                raise ValueError(f"lemma {lemma.name!r}: has no steps")

            last = lemma.steps[-1].label
            mm.p(
                mm.sym.label(lemma.name),
                tc=theorem_tc,
                expr=lemma.statement.tokens,
                proof=v2_emit_step(last, visiting=set(), steps=step_by_label_v2),
            )
