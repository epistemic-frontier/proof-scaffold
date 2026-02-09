from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, cast

from skfd.builder_v2 import MMBuilderV2
from skfd.core.diag import Diagnostic, LinkerDiagError
from skfd.core.symbols import SymbolId
from skfd.core.symbols import SymbolInterner

from .formula import Wff


class AxiomProvider(Protocol):
    interner: SymbolInterner

    def compile_axioms(self) -> Mapping[str, Wff]:
        ...


def emit_axioms(
    mm: MMBuilderV2,
    provider: AxiomProvider,
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
    tc = typecode if isinstance(typecode, int) else mm.sym.const(typecode)
    for label, wff in provider.compile_axioms().items():
        mm.a(mm.sym.label(label), tc=tc, expr=wff.tokens)


class LemmaStepLike(Protocol):
    wff: Wff


class LemmaLike(Protocol):
    name: str
    statement: Wff
    steps: Sequence[LemmaStepLike]


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
    tc = typecode if isinstance(typecode, int) else mm.sym.const(typecode)
    for lemma in lemmas:
        ax_label_id = mm.sym.label(f"{lemma.name}_ax")
        mm.a(ax_label_id, tc=tc, expr=lemma.statement.tokens)
        proof = [*mm.auto.mandatory_f(lemma.statement.tokens, tc=tc), ax_label_id]
        mm.p(
            mm.sym.label(lemma.name),
            tc=tc,
            expr=lemma.statement.tokens,
            proof=proof,
        )


class LoweredStepLike(LemmaStepLike, Protocol):
    label: str
    op: str
    args: Sequence[str]
    ref: str | None


class LoweredLemmaLike(LemmaLike, Protocol):
    steps: Sequence[LoweredStepLike]


def emit_lowered_lemmas(
    mm: MMBuilderV2,
    provider: AxiomProvider,
    lemmas: Sequence[LoweredLemmaLike],
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

    symtab = provider.interner.symbol_table()
    tc = typecode if isinstance(typecode, int) else mm.sym.const(typecode)

    v2_label_by_name: dict[str, list[SymbolId]] = {}
    for sid, d in mm.interner.symbol_table().items():
        if d.kind != "Label":
            continue
        v2_label_by_name.setdefault(d.local_name, []).append(sid)

    def v2_resolve_label(name: str) -> SymbolId:
        canonical = mm.names.canonicalize("Label", name)
        matches = v2_label_by_name.get(canonical, [])
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise LinkerDiagError(
                Diagnostic(
                    error_code="E_UNKNOWN_LABEL_NAME",
                    message="unknown proof label name",
                    primary_origin_ref=-1,
                    related_origin_refs=(),
                    origin_chain=(),
                    details={"label": canonical},
                )
            )
        raise LinkerDiagError(
            Diagnostic(
                error_code="E_AMBIGUOUS_LABEL_NAME",
                message="ambiguous proof label name",
                primary_origin_ref=-1,
                related_origin_refs=(),
                origin_chain=(),
                details={"label": canonical, "candidates": sorted(matches)},
            )
        )

    b = getattr(provider, "builtins", None)
    if b is None:
        raise ValueError("emit_lowered_lemmas: provider is missing .builtins")
    b2 = cast(Any, b)

    lp = b2.lp
    rp = b2.rp
    imp_tok = b2.imp

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
            return [mm.auto.floating(toks[0], tc=tc)]

        if toks[0] == b2.neg:
            return [*v2_wff_proof(toks[1:]), v2_resolve_label("wn")]

        imp_parts = v2_split_binary(toks, b2.imp, lp=b2.lp, rp=b2.rp)
        if imp_parts is not None:
            left, right = imp_parts
            return [*v2_wff_proof(left), *v2_wff_proof(right), v2_resolve_label("wi")]

        and_parts = v2_split_binary(toks, b2.and_, lp=b2.lp, rp=b2.rp)
        if and_parts is not None:
            left, right = and_parts
            return [*v2_wff_proof(left), *v2_wff_proof(right), v2_resolve_label("wa")]

        raise ValueError(f"wff proof: unsupported token shape (len={len(toks)})")

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
                mand = mm.auto.mandatory_f(step.wff.tokens, tc=tc)
                return [*mand, v2_resolve_label(step.ref)]

            if step.op == "mp":
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
                return [
                    *v2_wff_proof(maj_step.wff.tokens),
                    *v2_wff_proof(consequent),
                    *v2_emit_step(maj, visiting=visiting, steps=steps),
                    *v2_emit_step(minor, visiting=visiting, steps=steps),
                    v2_resolve_label("mp"),
                ]

            raise ValueError(f"step {label!r}: unknown op {step.op!r}")
        finally:
            visiting.remove(label)

    for lemma in lemmas:
        with mm.block():
            step_by_label_v2: dict[str, LoweredStepLike] = {s.label: s for s in lemma.steps}

            for step in lemma.steps:
                if step.op == "hyp":
                    mm.e(mm.sym.label(step.label), tc=tc, expr=step.wff.tokens)

            if not lemma.steps:
                raise ValueError(f"lemma {lemma.name!r}: has no steps")

            last = lemma.steps[-1].label
            mm.p(
                mm.sym.label(lemma.name),
                tc=tc,
                expr=lemma.statement.tokens,
                proof=v2_emit_step(last, visiting=set(), steps=step_by_label_v2),
            )
