from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, cast

from skfd.authoring.formula import Formula, Sort, Wff
from skfd.core.disjoint import DisjointSpecError, normalize_dv_pairs
from skfd.core.symbols import SymbolDef, SymbolId
from skfd.proof.ir import Proof, Step

from .errors import AuthoringSemanticError
from .ids import AssertionId, JudgmentKindId, SortId
from .judgment import Judgment
from .metamath_language import (
    LiteralAtom,
    ResolvedMetamathLanguageBinding,
    TokenRef,
)
from .replay import ReplaySequence
from .term import Term, VariableRef

MetamathProofOperation = Literal["ref", "apply"]


@dataclass(frozen=True, slots=True, kw_only=True)
class MetamathAssertionBinding:
    assertion: AssertionId
    backend_label: str
    operation: MetamathProofOperation
    legacy_rule: str | None = None

    def __post_init__(self) -> None:
        if self.operation not in ("ref", "apply"):
            raise AuthoringSemanticError(
                f"unsupported Metamath proof operation: {self.operation}"
            )
        if not self.backend_label:
            raise AuthoringSemanticError("Metamath assertion label must be non-empty")
        if self.operation == "apply" and self.legacy_rule != "mp":
            raise AuthoringSemanticError("Metamath proof only supports the mp apply rule")
        if self.operation == "ref" and self.legacy_rule is not None:
            raise AuthoringSemanticError("Metamath ref binding cannot override its rule name")


@dataclass(frozen=True, slots=True, kw_only=True)
class MetamathProofBinding:
    language: ResolvedMetamathLanguageBinding = field(
        compare=False, hash=False, repr=False
    )
    provable_judgment: JudgmentKindId
    assertions: tuple[MetamathAssertionBinding, ...]
    token_symbols: Mapping[TokenRef, SymbolId] = field(
        compare=False, hash=False, repr=False
    )
    variable_symbols: Mapping[VariableRef, SymbolId] = field(
        compare=False, hash=False, repr=False
    )
    legacy_sorts: Mapping[SortId, Sort] = field(
        compare=False, hash=False, repr=False
    )
    symbol_table: Mapping[SymbolId, SymbolDef] = field(
        compare=False, hash=False, repr=False
    )

    def __post_init__(self) -> None:
        by_assertion: dict[AssertionId, MetamathAssertionBinding] = {}
        for assertion in self.assertions:
            if assertion.assertion in by_assertion:
                raise AuthoringSemanticError(
                    f"duplicate Metamath assertion binding: {assertion.assertion}"
                )
            by_assertion[assertion.assertion] = assertion
        for token, symbol in self.token_symbols.items():
            definition = self.symbol_table.get(symbol)
            if definition is None or definition.kind != "Const":
                raise AuthoringSemanticError(
                    f"runtime token must resolve to a Const: {token.local_name}"
                )
        seen_variables: dict[SymbolId, VariableRef] = {}
        for variable, symbol in self.variable_symbols.items():
            definition = self.symbol_table.get(symbol)
            if definition is None or definition.kind != "Var":
                raise AuthoringSemanticError(
                    f"runtime variable must resolve to a Var: {variable.local_key}"
                )
            previous = seen_variables.get(symbol)
            if previous is not None and previous != variable:
                raise AuthoringSemanticError(
                    "distinct semantic variables cannot share a runtime symbol"
                )
            seen_variables[symbol] = variable
        object.__setattr__(self, "assertions", tuple(by_assertion.values()))
        object.__setattr__(self, "token_symbols", MappingProxyType(dict(self.token_symbols)))
        object.__setattr__(
            self, "variable_symbols", MappingProxyType(dict(self.variable_symbols))
        )
        object.__setattr__(self, "legacy_sorts", MappingProxyType(dict(self.legacy_sorts)))
        object.__setattr__(self, "symbol_table", MappingProxyType(dict(self.symbol_table)))

    def assertion(
        self, assertion_id: AssertionId
    ) -> MetamathAssertionBinding:
        for binding in self.assertions:
            if binding.assertion == assertion_id:
                return binding
        raise AuthoringSemanticError(
            f"no Metamath proof binding for assertion: {assertion_id}"
        )

    def lower_term(self, term: Term) -> Formula[Sort]:
        legacy_sort = self.legacy_sorts.get(term.sort)
        if legacy_sort is None:
            raise AuthoringSemanticError(f"no Metamath sort binding for: {term.sort}")
        tokens: list[SymbolId] = []
        for atom in self.language.lower(term):
            if isinstance(atom, LiteralAtom):
                symbol = self.token_symbols.get(atom.token)
                if symbol is None:
                    raise AuthoringSemanticError(
                        f"no runtime symbol for token: {atom.token.local_name}"
                    )
            else:
                symbol = self.variable_symbol(atom.variable)
            tokens.append(symbol)
        return Formula(legacy_sort, tuple(tokens))

    def variable_symbol(self, variable: VariableRef) -> SymbolId:
        symbol = self.variable_symbols.get(variable)
        if symbol is None:
            raise AuthoringSemanticError(
                f"no runtime symbol for variable: {variable.local_key}"
            )
        return symbol

    def lower_judgment(self, judgment: Judgment) -> Wff:
        if judgment.kind != self.provable_judgment or len(judgment.arguments) != 1:
            raise AuthoringSemanticError("Metamath lowering requires one provable term")
        formula = self.lower_term(judgment.arguments[0])
        if formula.sort != "wff":
            raise AuthoringSemanticError("Metamath proof conclusion must lower to wff")
        return cast(Wff, formula)


def lower_replay_to_metamath_proof(
    plan: ReplaySequence,
    binding: MetamathProofBinding,
    *,
    proof_name: str,
) -> Proof:
    if not proof_name:
        raise AuthoringSemanticError("Metamath proof name must be non-empty")
    final_position = len(plan.hypotheses) + len(plan.applications) - 1
    hypothesis_positions = {
        hypothesis.position for hypothesis in plan.hypotheses
    }
    if (
        plan.root_position != final_position
        and plan.root_position not in hypothesis_positions
    ):
        raise AuthoringSemanticError(
            "Metamath lowering requires an application root to be the final position"
        )

    labels: dict[int, str] = {
        hypothesis.position: (
            "res"
            if hypothesis.position == plan.root_position
            else f"{proof_name}.{index}"
        )
        for index, hypothesis in enumerate(plan.hypotheses, start=1)
    }
    next_step = 1
    for application in plan.applications:
        if application.position == plan.root_position:
            labels[application.position] = "res"
        else:
            labels[application.position] = f"s{next_step}"
            next_step += 1

    steps: list[Step] = [
        Step(
            labels[hypothesis.position],
            binding.lower_judgment(hypothesis.result),
            "Hypothesis",
            op="hyp",
        )
        for hypothesis in plan.hypotheses
    ]
    by_position = {hypothesis.position: hypothesis.result for hypothesis in plan.hypotheses}
    for application in plan.applications:
        assertion = binding.assertion(application.assertion)
        try:
            args = tuple(labels[position] for position in application.premise_positions)
        except KeyError as error:
            raise AuthoringSemanticError(
                f"Metamath proof references unknown position: {error.args[0]}"
            ) from error
        steps.append(
            Step(
                labels[application.position],
                binding.lower_judgment(application.result),
                assertion.backend_label,
                op=assertion.operation,
                args=args,
                ref=(
                    assertion.backend_label
                    if assertion.operation == "ref"
                    else assertion.legacy_rule
                ),
            )
        )
        by_position[application.position] = application.result

    root = by_position.get(plan.root_position)
    if root is None:
        raise AuthoringSemanticError("Metamath proof root position is unknown")
    statement = binding.lower_judgment(plan.signature.conclusion)
    if binding.lower_judgment(root) != statement:
        raise AuthoringSemanticError("Metamath proof root does not match its statement")
    try:
        active_distinct = normalize_dv_pairs(
            (
                (binding.variable_symbol(pair.left), binding.variable_symbol(pair.right))
                for pair in plan.replay_context.active_distinct
            ),
            symtab=binding.symbol_table,
        )
    except DisjointSpecError as error:
        raise AuthoringSemanticError(
            f"invalid Metamath proof distinct-variable relation: {error}"
        ) from error
    return Proof(proof_name, statement, tuple(steps), active_distinct)


# Compatibility aliases; the Metamath names are the implementation source.
LegacyReplayOperation = MetamathProofOperation
LegacyAssertionReplayBinding = MetamathAssertionBinding
LegacyReplayBinding = MetamathProofBinding
lower_semantic_replay_plan = lower_replay_to_metamath_proof
