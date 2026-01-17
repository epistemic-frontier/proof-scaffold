from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from skfd.builder import MMBuilder
from skfd.core.symbols import SymbolInterner

from .formula import Wff


class AxiomProvider(Protocol):
    interner: SymbolInterner

    def compile_axioms(self) -> Mapping[str, Wff]:
        ...


def emit_axioms(mm: MMBuilder, provider: AxiomProvider, typecode: str = "wff") -> None:
    axioms = provider.compile_axioms()
    symtab = provider.interner.symbol_table()

    const_ids: set[int] = set()
    var_ids: set[int] = set()

    for wff in axioms.values():
        for sid in wff.tokens:
            s = symtab[sid]
            if s.kind == "Const":
                const_ids.add(s.id)
            elif s.kind == "Var":
                var_ids.add(s.id)

    token_map: dict[int, str] = {}

    const_names: list[str] = []
    for sid in sorted(const_ids):
        name = f"c{sid}"
        token_map[sid] = name
        const_names.append(name)

    var_names: list[str] = []
    for sid in sorted(var_ids):
        name = f"v{sid}"
        token_map[sid] = name
        var_names.append(name)

    if const_names:
        mm.c(*const_names)

    if var_names:
        mm.v(*var_names)
        for name in var_names:
            mm.f(f"w_{name}", typecode, name)

    for label, wff in axioms.items():
        tokens = [token_map[sid] for sid in wff.tokens]
        expr = " ".join(tokens)
        mm.a(label, typecode, expr)


class LemmaStepLike(Protocol):
    wff: Wff


class LemmaLike(Protocol):
    name: str
    statement: Wff
    steps: Sequence[LemmaStepLike]


def emit_lemmas(
    mm: MMBuilder,
    provider: AxiomProvider,
    lemmas: Sequence[LemmaLike],
    typecode: str = "wff",
) -> None:
    axioms = provider.compile_axioms()
    symtab = provider.interner.symbol_table()

    const_ids: set[int] = set()
    var_ids: set[int] = set()

    for wff in axioms.values():
        for sid in wff.tokens:
            s = symtab[sid]
            if s.kind == "Const":
                const_ids.add(s.id)
            elif s.kind == "Var":
                var_ids.add(s.id)

    for lemma in lemmas:
        for sid in lemma.statement.tokens:
            s = symtab[sid]
            if s.kind == "Const":
                const_ids.add(s.id)
            elif s.kind == "Var":
                var_ids.add(s.id)
        for step in lemma.steps:
            for sid in step.wff.tokens:
                s = symtab[sid]
                if s.kind == "Const":
                    const_ids.add(s.id)
                elif s.kind == "Var":
                    var_ids.add(s.id)

    token_map: dict[int, str] = {}

    for sid in sorted(const_ids):
        token_map[sid] = f"c{sid}"

    for sid in sorted(var_ids):
        token_map[sid] = f"v{sid}"

    for lemma in lemmas:
        tokens = [token_map[sid] for sid in lemma.statement.tokens]
        expr = " ".join(tokens)
        ax_label = f"{lemma.name}_ax"
        mm.a(ax_label, typecode, expr)
        stmt_var_ids: list[int] = []
        seen: set[int] = set()
        for sid in lemma.statement.tokens:
            d = symtab[sid]
            if d.kind == "Var" and d.id not in seen:
                seen.add(d.id)
                stmt_var_ids.append(d.id)
        f_labels: list[str] = [f"w_{token_map[sid]}" for sid in stmt_var_ids]
        mm.p(lemma.name, typecode, expr, [*f_labels, ax_label])


class LoweredStepLike(LemmaStepLike, Protocol):
    label: str
    op: str
    args: Sequence[str]
    ref: str | None


class LoweredLemmaLike(LemmaLike, Protocol):
    steps: Sequence[LoweredStepLike]


def emit_lowered_lemmas(
    mm: MMBuilder,
    provider: AxiomProvider,
    lemmas: Sequence[LoweredLemmaLike],
    typecode: str = "wff",
) -> None:
    symtab = provider.interner.symbol_table()
    axioms = provider.compile_axioms()

    def _collect_tokens(w: Wff, *, const_ids: set[int], var_ids: set[int]) -> None:
        for sid in w.tokens:
            s = symtab[sid]
            if s.kind == "Const":
                const_ids.add(s.id)
            elif s.kind == "Var":
                var_ids.add(s.id)

    for lemma in lemmas:
        const_ids: set[int] = set()
        var_ids: set[int] = set()
        for w in axioms.values():
            _collect_tokens(w, const_ids=const_ids, var_ids=var_ids)
        _collect_tokens(lemma.statement, const_ids=const_ids, var_ids=var_ids)
        for step in lemma.steps:
            _collect_tokens(step.wff, const_ids=const_ids, var_ids=var_ids)

        token_map: dict[int, str] = {sid: f"c{sid}" for sid in sorted(const_ids)}
        token_map.update({sid: f"v{sid}" for sid in sorted(var_ids)})

        extra_consts = [f"c{sid}" for sid in sorted(const_ids) if f"c{sid}" not in mm._constants]
        if extra_consts:
            mm.c(*extra_consts)
        extra_vars = [f"v{sid}" for sid in sorted(var_ids) if f"v{sid}" not in mm._variables]
        if extra_vars:
            mm.v(*extra_vars)
            for v in extra_vars:
                mm.f(f"w_{v}", typecode, v)

        def _render_tokens(tokens: Sequence[int], _token_map: Mapping[int, str] = token_map) -> str:
            return " ".join(_token_map[sid] for sid in tokens)

        with mm.block():
            step_by_label: dict[str, LoweredStepLike] = {s.label: s for s in lemma.steps}

            for step in lemma.steps:
                if step.op == "hyp":
                    mm.e(step.label, typecode, _render_tokens(step.wff.tokens))

            b = getattr(provider, "builtins", None)
            if b is None:
                raise ValueError("emit_lowered_lemmas: provider is missing .builtins")
            lp = b.lp
            rp = b.rp
            imp_tok = b.imp

            def _split_binary(
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

            def _wff_proof(
                tokens: Sequence[int],
                *,
                _symtab: Mapping[int, Any] = symtab,
                _token_map: Mapping[int, str] = token_map,
                _b: Any = b,
            ) -> list[str]:
                toks = tuple(tokens)
                if not toks:
                    raise ValueError("wff proof: empty token seq")

                if len(toks) == 1 and _symtab[toks[0]].kind == "Var":
                    return [f"w_{_token_map[toks[0]]}"]

                if toks[0] == _b.neg:
                    return [*_wff_proof(toks[1:]), "wn"]

                imp_parts = _split_binary(toks, _b.imp, lp=_b.lp, rp=_b.rp)
                if imp_parts is not None:
                    left, right = imp_parts
                    return [*_wff_proof(left), *_wff_proof(right), "wi"]

                and_parts = _split_binary(toks, _b.and_, lp=_b.lp, rp=_b.rp)
                if and_parts is not None:
                    left, right = and_parts
                    return [*_wff_proof(left), *_wff_proof(right), "wa"]

                raise ValueError(f"wff proof: unsupported token shape (len={len(toks)})")

            def _var_wff_labels(
                tokens: Sequence[int],
                *,
                _symtab: Mapping[int, Any] = symtab,
                _token_map: Mapping[int, str] = token_map,
            ) -> list[str]:
                seen: set[int] = set()
                var_ids: list[int] = []
                for sid in tokens:
                    d = _symtab[sid]
                    if d.kind != "Var":
                        continue
                    if d.id in seen:
                        continue
                    seen.add(d.id)
                    var_ids.append(d.id)
                return [f"w_{_token_map[i]}" for i in sorted(var_ids)]

            def _emit_step(
                label: str,
                *,
                visiting: set[str],
                _steps: Mapping[str, LoweredStepLike] = step_by_label,
                _imp_tok: int = imp_tok,
                _lp: int = lp,
                _rp: int = rp,
            ) -> list[str]:
                if label in visiting:
                    raise ValueError(f"cycle detected at step {label!r}")
                step = _steps.get(label)
                if step is None:
                    raise ValueError(f"unknown step label {label!r}")

                if step.op == "hyp":
                    return [label]

                visiting.add(label)
                try:
                    if step.op == "ref":
                        if step.ref is None:
                            raise ValueError(f"step {label!r}: missing ref label")
                        return [*_var_wff_labels(step.wff.tokens), step.ref]

                    if step.op == "mp":
                        if len(step.args) != 2:
                            raise ValueError(
                                f"step {label!r}: mp expects 2 args, got {len(step.args)}"
                            )
                        maj, minor = step.args[0], step.args[1]
                        maj_step = _steps.get(maj)
                        minor_step = _steps.get(minor)
                        if maj_step is None or minor_step is None:
                            raise ValueError(f"step {label!r}: mp args must reference prior steps")

                        minor_parts = _split_binary(minor_step.wff.tokens, _imp_tok, lp=_lp, rp=_rp)
                        if minor_parts is None:
                            raise ValueError(f"step {label!r}: mp minor is not an implication")
                        antecedent, consequent = minor_parts
                        if tuple(maj_step.wff.tokens) != antecedent:
                            raise ValueError(f"step {label!r}: mp antecedent mismatch")
                        return [
                            *_wff_proof(maj_step.wff.tokens),
                            *_wff_proof(consequent),
                            *_emit_step(maj, visiting=visiting),
                            *_emit_step(minor, visiting=visiting),
                            "mp",
                        ]

                    raise ValueError(f"step {label!r}: unknown op {step.op!r}")
                finally:
                    visiting.remove(label)

            if not lemma.steps:
                raise ValueError(f"lemma {lemma.name!r}: has no steps")

            last = lemma.steps[-1].label
            stmt_expr = _render_tokens(lemma.statement.tokens)
            mm.p(lemma.name, typecode, stmt_expr, _emit_step(last, visiting=set()))
