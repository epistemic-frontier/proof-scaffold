"""Deterministic Metamath emission for semantic theories."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, TypeVar, cast

from skfd.builder_v2 import MMBuilderV2
from skfd.core.symbols import SymbolId
from skfd.proof.ir import Proof

from .catalog import AssertionCatalogInterface
from .errors import AuthoringSemanticError
from .formula import Sort
from .ids import (
    AssertionCatalogId,
    AssertionProfileId,
    Digest,
    JudgmentKindId,
    SortId,
)
from .metamath_language import ResolvedMetamathLanguageBinding, TokenRef
from .metamath_lowering import (
    MetamathAssertionBinding,
    MetamathProofBinding,
    lower_replay_to_metamath_proof,
)
from .replay import ReplaySequence, replay_proof
from .term import App, Term, Var, VariableRef
from .theory import AssertionHandle, Theory

HYPOTHESIS_LABEL_POLICY_V1 = "mm-transpiler-hypotheses-v1"
FLOATING_ORDER_POLICY_V1 = "mm-transpiler-primitive-floating-source-order-v1"
_Key = TypeVar("_Key")


class MetamathEmissionError(AuthoringSemanticError):
    pass


@dataclass(frozen=True, slots=True)
class MetamathFloatingEmission:
    sort: SortId
    variable: str

    def __post_init__(self) -> None:
        if not self.variable:
            raise MetamathEmissionError("floating variable must be non-empty")


@dataclass(frozen=True, slots=True)
class MetamathFormationEmission:
    label: str
    typecode: str
    expression: tuple[str, ...]
    mandatory_floating: tuple[MetamathFloatingEmission, ...]

    def __post_init__(self) -> None:
        if not self.label or not self.typecode or not self.expression:
            raise MetamathEmissionError(
                "formation label, typecode, and expression must be non-empty"
            )
        variables = tuple(item.variable for item in self.mandatory_floating)
        if len(set(variables)) != len(variables):
            raise MetamathEmissionError(
                f"duplicate formation floating variable: {self.label}"
            )


EmissionEntryKind = Literal["formation", "assertion"]


@dataclass(frozen=True, slots=True)
class MetamathEmissionEntry:
    kind: EmissionEntryKind
    label: str

    def __post_init__(self) -> None:
        if self.kind not in ("formation", "assertion"):
            raise MetamathEmissionError(
                f"unsupported emission entry kind: {self.kind}"
            )
        if not self.label:
            raise MetamathEmissionError("emission entry label must be non-empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class MetamathEmissionBinding:
    """Versioned declaration-level data needed to emit one semantic theory."""

    language: ResolvedMetamathLanguageBinding = field(
        compare=False, hash=False, repr=False
    )
    provable_judgment: JudgmentKindId
    provable_typecode: str
    token_names: Mapping[TokenRef, str] = field(
        compare=False, hash=False, repr=False
    )
    variable_names: Mapping[str, str] = field(
        compare=False, hash=False, repr=False
    )
    sort_typecodes: Mapping[SortId, str] = field(
        compare=False, hash=False, repr=False
    )
    formations: tuple[MetamathFormationEmission, ...]
    primitive_rule_floating: Mapping[
        str, tuple[MetamathFloatingEmission, ...]
    ] = field(compare=False, hash=False, repr=False)
    sequence: tuple[MetamathEmissionEntry, ...]
    hypothesis_label_policy: str = HYPOTHESIS_LABEL_POLICY_V1
    floating_order_policy: str = FLOATING_ORDER_POLICY_V1

    def __post_init__(self) -> None:
        if not self.provable_typecode:
            raise MetamathEmissionError("provable typecode must be non-empty")
        if self.hypothesis_label_policy != HYPOTHESIS_LABEL_POLICY_V1:
            raise MetamathEmissionError(
                "unsupported hypothesis label policy: "
                f"{self.hypothesis_label_policy}"
            )
        if self.floating_order_policy != FLOATING_ORDER_POLICY_V1:
            raise MetamathEmissionError(
                "unsupported floating order policy: "
                f"{self.floating_order_policy}"
            )
        _require_non_empty_mapping(self.token_names, "runtime token")
        _require_non_empty_mapping(self.variable_names, "runtime variable")
        _require_non_empty_mapping(self.sort_typecodes, "sort typecode")
        formation_labels = tuple(item.label for item in self.formations)
        if len(set(formation_labels)) != len(formation_labels):
            raise MetamathEmissionError("duplicate formation emission label")
        sequence_formations = tuple(
            item.label for item in self.sequence if item.kind == "formation"
        )
        unknown_formations = set(sequence_formations) - set(formation_labels)
        if unknown_formations:
            raise MetamathEmissionError(
                f"emission sequence references unknown formation: "
                f"{min(unknown_formations)}"
            )
        expected_formation_order = tuple(
            label for label in formation_labels if label in set(sequence_formations)
        )
        if sequence_formations != expected_formation_order:
            raise MetamathEmissionError(
                "emission sequence formations do not preserve declaration order"
            )
        sequence_labels = tuple(item.label for item in self.sequence)
        if len(set(sequence_labels)) != len(sequence_labels):
            raise MetamathEmissionError("duplicate label in emission sequence")
        object.__setattr__(
            self, "token_names", MappingProxyType(dict(self.token_names))
        )
        object.__setattr__(
            self, "variable_names", MappingProxyType(dict(self.variable_names))
        )
        object.__setattr__(
            self, "sort_typecodes", MappingProxyType(dict(self.sort_typecodes))
        )
        object.__setattr__(
            self,
            "primitive_rule_floating",
            MappingProxyType(dict(self.primitive_rule_floating)),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class MetamathEmissionContext:
    """Builder context plus already-exported upstream assertion labels."""

    mm: MMBuilderV2
    external_assertions: Mapping[str, SymbolId] = field(default_factory=dict)
    external_constants: Mapping[str, SymbolId] = field(default_factory=dict)
    external_variables: Mapping[str, SymbolId] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for attribute in (
            "external_assertions",
            "external_constants",
            "external_variables",
        ):
            value = cast(Mapping[str, SymbolId], getattr(self, attribute))
            object.__setattr__(self, attribute, MappingProxyType(dict(value)))


def emit_semantic_metamath_theory(
    theory: Theory,
    binding: MetamathEmissionBinding,
    ctx: MetamathEmissionContext,
) -> None:
    """Emit local theory declarations through semantic replay and BuilderV2."""
    emitter = _TheoryEmitter(theory, binding, ctx)
    emitter.emit()


def _require_non_empty_mapping(
    mapping: Mapping[_Key, str], subject: str
) -> None:
    for value in mapping.values():
        if not value:
            raise MetamathEmissionError(f"{subject} name must be non-empty")


class _TheoryEmitter:
    def __init__(
        self,
        theory: Theory,
        binding: MetamathEmissionBinding,
        ctx: MetamathEmissionContext,
    ) -> None:
        self.theory = theory
        self.binding = binding
        self.mm = ctx.mm
        self.external_assertions = ctx.external_assertions
        self.external_constants = ctx.external_constants
        self.external_variables = ctx.external_variables
        self.handles = _all_handles(theory)
        self.local_handles = dict(theory.assertions)
        self.formations = {item.label: item for item in binding.formations}
        self.local_formation_labels = tuple(
            item.label for item in binding.sequence if item.kind == "formation"
        )
        self.constants: dict[str, SymbolId] = {}
        self.variables: dict[str, SymbolId] = {}
        self.local_labels: dict[str, SymbolId] = {}
        self.floating_labels: dict[VariableRef, SymbolId] = {}
        self._hypothesis_counter = 0
        self._reserved_labels = {
            *self.handles,
            *(item.label for item in binding.formations),
            *self.external_assertions,
        }
        self.catalog, self.profile = _catalog(theory, self.handles)

    def emit(self) -> None:
        assertion_order = tuple(
            item.label for item in self.binding.sequence if item.kind == "assertion"
        )
        if assertion_order != tuple(self.local_handles):
            raise MetamathEmissionError(
                "emission assertion order does not match theory registration order"
            )
        primitive_labels = {
            label
            for label, handle in self.handles.items()
            if handle.kind == "primitive_rule"
        }
        supplied_labels = set(self.binding.primitive_rule_floating)
        if primitive_labels != supplied_labels:
            missing = primitive_labels - supplied_labels
            extra = supplied_labels - primitive_labels
            detail = min(missing) if missing else min(extra)
            raise MetamathEmissionError(
                f"primitive rule floating sequence is missing or unused: {detail}"
            )
        self._intern_symbols()
        for entry in self.binding.sequence:
            if entry.kind == "formation":
                self._emit_formation(self.formations[entry.label])
            else:
                self._emit_assertion(self.local_handles[entry.label])
        self.mm.export(
            *self.constants.values(),
            *self.variables.values(),
            *self.local_labels.values(),
        )

    def _intern_symbols(self) -> None:
        variable_names = set(self.binding.variable_names.values())
        constant_names = {
            *self.binding.token_names.values(),
            *self.binding.sort_typecodes.values(),
            self.binding.provable_typecode,
        }
        for formation in self.binding.formations:
            constant_names.add(formation.typecode)
            for token in formation.expression:
                if token not in variable_names:
                    constant_names.add(token)
        overlap = constant_names & variable_names
        if overlap:
            raise MetamathEmissionError(
                f"tokens cannot be both constants and variables: {min(overlap)}"
            )
        self.constants = self._symbols(
            constant_names, self.external_constants, "Const"
        )
        self.variables = self._symbols(
            variable_names, self.external_variables, "Var"
        )
        self.local_labels = {
            label: self.mm.sym.label(label, exact=True)
            for label in (
                *self.local_formation_labels,
                *self.local_handles,
            )
        }

    def _symbols(
        self,
        names: set[str],
        external: Mapping[str, SymbolId],
        kind: Literal["Const", "Var"],
    ) -> dict[str, SymbolId]:
        symbols: dict[str, SymbolId] = {}
        for name in sorted(names):
            symbol = external.get(name)
            if symbol is None:
                symbol = (
                    self.mm.sym.const(name, exact=True)
                    if kind == "Const"
                    else self.mm.sym.var(name, exact=True)
                )
            definition = self.mm.interner.get(symbol)
            if (
                definition is None
                or definition.kind != kind
                or definition.local_name != name
            ):
                raise MetamathEmissionError(
                    f"external {kind} mapping does not match symbol name: {name}"
                )
            symbols[name] = symbol
        unknown = set(external) - names
        if unknown:
            raise MetamathEmissionError(
                f"external {kind} mapping is unused: {min(unknown)}"
            )
        return symbols

    def _emit_formation(self, formation: MetamathFormationEmission) -> None:
        with self.mm.block():
            for floating in formation.mandatory_floating:
                variable = self._variable_symbol_name(floating.variable)
                typecode = self._sort_typecode(floating.sort)
                self.mm.f(self._next_hypothesis_label(), tc=typecode, var=variable)
            self.mm.a(
                self.local_labels[formation.label],
                tc=self._constant(formation.typecode),
                expr=tuple(self._expression_symbol(token) for token in formation.expression),
            )

    def _emit_assertion(self, handle: AssertionHandle) -> None:
        signature = handle.signature
        with self.mm.block():
            self.floating_labels = {}
            lowered_theorem: tuple[ReplaySequence, Proof] | None = None
            variables = signature.schema_variables
            active_distinct = signature.mandatory_distinct
            if handle.kind == "theorem":
                lowered_theorem = self._lower_theorem(handle)
                plan, _lowered = lowered_theorem
                proof_variables = _replay_variables(plan)
                variables = (
                    *signature.schema_variables,
                    *tuple(
                        sorted(
                            proof_variables - set(signature.schema_variables),
                            key=_variable_key,
                        )
                    ),
                )
                active_distinct = plan.replay_context.active_distinct
            if handle.kind == "primitive_rule":
                variables = self._primitive_rule_variables(handle)
            for variable in variables:
                symbol = self._semantic_variable_symbol(variable)
                kind = self.theory.language.variable_kinds[variable.kind]
                label = self._next_hypothesis_label()
                self.mm.f(label, tc=self._sort_typecode(kind.sort), var=symbol)
                self.floating_labels[variable] = label
            essential_labels: dict[int, SymbolId] = {}
            for position, premise in enumerate(signature.premises):
                label = self._next_hypothesis_label()
                self.mm.e(
                    label,
                    tc=self._constant(self.binding.provable_typecode),
                    expr=self._lower_judgment(premise),
                )
                essential_labels[position] = label
            for pair in active_distinct:
                self.mm.d(
                    self._semantic_variable_symbol(pair.left),
                    self._semantic_variable_symbol(pair.right),
                )
            expression = self._lower_judgment(signature.conclusion)
            label = self.local_labels[handle.label]
            if handle.kind != "theorem":
                self.mm.a(
                    label,
                    tc=self._constant(self.binding.provable_typecode),
                    expr=expression,
                )
                return
            if lowered_theorem is None:
                raise MetamathEmissionError(
                    f"theorem lowering was not initialized: {handle.label}"
                )
            plan, lowered = lowered_theorem
            proof = self._proof_tokens(plan, lowered, essential_labels)
            self.mm.p(
                label,
                tc=self._constant(self.binding.provable_typecode),
                expr=expression,
                proof=proof,
            )

    def _primitive_rule_variables(
        self, handle: AssertionHandle
    ) -> tuple[VariableRef, ...]:
        source = self.binding.primitive_rule_floating[handle.label]
        by_emission_name = {
            self.binding.variable_names.get(variable.local_key): variable
            for variable in handle.signature.schema_variables
        }
        resolved: list[VariableRef] = []
        for floating in source:
            variable = by_emission_name.get(floating.variable)
            if variable is None:
                raise MetamathEmissionError(
                    "primitive rule floating variables do not match calculus rule: "
                    f"{handle.label}"
                )
            kind = self.theory.language.variable_kinds[variable.kind]
            if kind.sort != floating.sort:
                raise MetamathEmissionError(
                    "primitive rule floating sort does not match calculus rule: "
                    f"{handle.label}"
                )
            resolved.append(variable)
        if set(resolved) != set(handle.signature.schema_variables) or len(resolved) != len(
            handle.signature.schema_variables
        ):
            raise MetamathEmissionError(
                "primitive rule floating variables do not match calculus rule: "
                f"{handle.label}"
            )
        return tuple(resolved)

    def _lower_theorem(self, handle: AssertionHandle) -> tuple[ReplaySequence, Proof]:
        plan = replay_proof(
            handle.implementation,
            self.theory.calculus,
            self.catalog,
            self.profile,
        )
        proof_binding = self._proof_binding(plan)
        lowered = lower_replay_to_metamath_proof(
            plan, proof_binding, proof_name=handle.label
        )
        return plan, lowered

    def _proof_binding(self, plan: ReplaySequence) -> MetamathProofBinding:
        variables = {
            variable
            for judgment in (
                *plan.signature.premises,
                plan.signature.conclusion,
                *(item.result for item in plan.applications),
            )
            for term in judgment.arguments
            for variable in _term_variables(term)
        }
        variable_symbols = {
            variable: self._semantic_variable_symbol(variable)
            for variable in variables
        }
        token_symbols = {
            token: self._constant(name)
            for token, name in self.binding.token_names.items()
        }
        legacy_sorts: dict[SortId, Sort] = {}
        for sort, typecode in self.binding.sort_typecodes.items():
            if typecode not in ("wff", "class", "setvar"):
                raise MetamathEmissionError(
                    f"Metamath lowering has no legacy sort for typecode: {typecode}"
                )
            legacy_sorts[sort] = cast(Sort, typecode)
        assertions = tuple(
            MetamathAssertionBinding(
                assertion=handle.id,
                backend_label=handle.label,
                operation="ref",
            )
            for handle in self.handles.values()
        )
        return MetamathProofBinding(
            language=self.binding.language,
            provable_judgment=self.binding.provable_judgment,
            assertions=assertions,
            token_symbols=token_symbols,
            variable_symbols=variable_symbols,
            legacy_sorts=legacy_sorts,
            symbol_table=self.mm.interner.symbol_table(),
        )

    def _proof_tokens(
        self,
        plan: ReplaySequence,
        lowered: Proof,
        essential_labels: Mapping[int, SymbolId],
    ) -> tuple[SymbolId, ...]:
        expected_steps = len(plan.hypotheses) + len(plan.applications)
        if len(lowered.steps) != expected_steps:
            raise MetamathEmissionError("lowered proof step count does not match replay")
        step_by_label = {step.label: step for step in lowered.steps}
        if len(step_by_label) != len(lowered.steps):
            raise MetamathEmissionError("lowered proof contains duplicate step labels")
        position_by_label = {
            step.label: position for position, step in enumerate(lowered.steps)
        }
        applications = {item.position: item for item in plan.applications}

        def emit_step(label: str, visiting: frozenset[str]) -> tuple[SymbolId, ...]:
            if label in visiting:
                raise MetamathEmissionError(f"lowered proof contains a cycle: {label}")
            step = step_by_label.get(label)
            position = position_by_label.get(label)
            if step is None or position is None:
                raise MetamathEmissionError(
                    f"lowered proof references unknown step: {label}"
                )
            if step.op == "hyp":
                hypothesis = essential_labels.get(position)
                if hypothesis is None:
                    raise MetamathEmissionError(
                        f"lowered hypothesis has no essential label: {label}"
                    )
                return (hypothesis,)
            if step.op != "ref":
                raise MetamathEmissionError(
                    f"unsupported lowered proof operation: {step.op}"
                )
            application = applications.get(position)
            if application is None:
                raise MetamathEmissionError(
                    f"lowered application has no replay position: {label}"
                )
            assertion = self.handles.get(step.note)
            if assertion is None or assertion.id != application.assertion:
                raise MetamathEmissionError(
                    f"lowered assertion mapping is missing: {application.canonical_label}"
                )
            substitution = dict(application.substitution)
            tokens: list[SymbolId] = []
            application_variables = assertion.signature.schema_variables
            if assertion.kind == "primitive_rule":
                application_variables = self._primitive_rule_variables(assertion)
            for variable in application_variables:
                term = substitution.get(variable)
                if term is None:
                    raise MetamathEmissionError(
                        f"assertion substitution is missing variable: {variable.local_key}"
                    )
                tokens.extend(self._term_proof(term))
            for premise_label in step.args:
                tokens.extend(emit_step(premise_label, visiting | {label}))
            tokens.append(self._assertion_label(assertion.label))
            return tuple(tokens)

        root = step_by_label.get("res")
        if root is None:
            raise MetamathEmissionError("lowered proof has no res root step")
        return emit_step(root.label, frozenset())

    def _term_proof(self, term: Term) -> tuple[SymbolId, ...]:
        if isinstance(term, Var):
            label = self.floating_labels.get(term.variable)
            if label is None:
                raise MetamathEmissionError(
                    f"no active floating for variable: {term.variable.local_key}"
                )
            return (label,)
        formation_binding = self.binding.language.formations.get(term.constructor)
        if formation_binding is None:
            raise MetamathEmissionError(
                f"no Metamath formation for constructor: {term.constructor}"
            )
        formation = self.formations.get(formation_binding.syntax_assertion_label)
        if formation is None:
            raise MetamathEmissionError(
                "missing formation emission: "
                f"{formation_binding.syntax_assertion_label}"
            )
        expected_sorts = tuple(item.sort for item in formation.mandatory_floating)
        actual_sorts = tuple(argument.sort for argument in term.arguments)
        if expected_sorts != actual_sorts:
            raise MetamathEmissionError(
                f"formation floating order does not match constructor inputs: "
                f"{formation.label}"
            )
        tokens: list[SymbolId] = []
        for argument in term.arguments:
            tokens.extend(self._term_proof(argument))
        tokens.append(self._assertion_label(formation.label))
        return tuple(tokens)

    def _lower_judgment(self, judgment: object) -> tuple[SymbolId, ...]:
        from .judgment import Judgment

        if not isinstance(judgment, Judgment):
            raise MetamathEmissionError("expected a semantic judgment")
        if (
            judgment.kind != self.binding.provable_judgment
            or len(judgment.arguments) != 1
        ):
            raise MetamathEmissionError(
                "Metamath emission requires one provable term"
            )
        symbols: list[SymbolId] = []
        for atom in self.binding.language.lower(judgment.arguments[0]):
            from .metamath_language import LiteralAtom

            if isinstance(atom, LiteralAtom):
                name = self.binding.token_names.get(atom.token)
                if name is None:
                    raise MetamathEmissionError(
                        f"no emission symbol for token: {atom.token.local_name}"
                    )
                symbols.append(self._constant(name))
            else:
                symbols.append(self._semantic_variable_symbol(atom.variable))
        return tuple(symbols)

    def _semantic_variable_symbol(self, variable: VariableRef) -> SymbolId:
        name = self.binding.variable_names.get(variable.local_key)
        if name is None:
            raise MetamathEmissionError(
                f"no emission symbol for variable: {variable.local_key}"
            )
        return self._variable_symbol_name(name)

    def _sort_typecode(self, sort: SortId) -> SymbolId:
        name = self.binding.sort_typecodes.get(sort)
        if name is None:
            raise MetamathEmissionError(f"no Metamath typecode for sort: {sort}")
        return self._constant(name)

    def _constant(self, name: str) -> SymbolId:
        symbol = self.constants.get(name)
        if symbol is None:
            raise MetamathEmissionError(f"unknown constant emission symbol: {name}")
        return symbol

    def _variable_symbol_name(self, name: str) -> SymbolId:
        symbol = self.variables.get(name)
        if symbol is None:
            raise MetamathEmissionError(f"unknown variable emission symbol: {name}")
        return symbol

    def _expression_symbol(self, name: str) -> SymbolId:
        variable = self.variables.get(name)
        if variable is not None:
            return variable
        return self._constant(name)

    def _assertion_label(self, label: str) -> SymbolId:
        local = self.local_labels.get(label)
        if local is not None:
            return local
        external = self.external_assertions.get(label)
        if external is not None:
            return external
        raise MetamathEmissionError(
            f"no emitted or external assertion label mapping: {label}"
        )

    def _next_hypothesis_label(self) -> SymbolId:
        while True:
            name = f"mmtranspiler.h{self._hypothesis_counter}"
            self._hypothesis_counter += 1
            if name not in self._reserved_labels:
                self._reserved_labels.add(name)
                return self.mm.sym.label(name, exact=True)


def _all_handles(theory: Theory) -> dict[str, AssertionHandle]:
    handles: dict[str, AssertionHandle] = {}
    for upstream in theory.upstreams:
        for label, handle in _all_handles(upstream).items():
            existing = handles.get(label)
            if existing is not None and existing.id != handle.id:
                raise MetamathEmissionError(
                    f"conflicting upstream assertion label: {label}"
                )
            handles[label] = handle
    handles.update(theory.assertions)
    return handles


def _catalog(
    theory: Theory,
    handles: Mapping[str, AssertionHandle],
) -> tuple[AssertionCatalogInterface, AssertionProfileId]:
    profile = AssertionProfileId(f"{theory.namespace}#profile:emission")
    assertions = {handle.id: handle.signature for handle in handles.values()}
    return (
        AssertionCatalogInterface(
            AssertionCatalogId(f"{theory.namespace}#catalog:emission"),
            Digest("0" * 64),
            assertions,
            {handle.label: handle.id for handle in handles.values()},
            {profile: frozenset(assertions)},
        ),
        profile,
    )


def _term_variables(term: Term) -> set[VariableRef]:
    if isinstance(term, Var):
        return {term.variable}
    variables: set[VariableRef] = set()
    for argument in cast(App, term).arguments:
        variables.update(_term_variables(argument))
    return variables


def _replay_variables(plan: ReplaySequence) -> set[VariableRef]:
    variables = {
        variable
        for judgment in (
            *plan.signature.premises,
            plan.signature.conclusion,
            *(item.result for item in plan.applications),
        )
        for term in judgment.arguments
        for variable in _term_variables(term)
    }
    for application in plan.applications:
        for _schema_variable, term in application.substitution:
            variables.update(_term_variables(term))
    for pair in plan.replay_context.active_distinct:
        variables.add(pair.left)
        variables.add(pair.right)
    return variables


def _variable_key(variable: VariableRef) -> tuple[str, str, str, str]:
    return (
        variable.scope,
        str(variable.owner),
        variable.local_key,
        str(variable.kind),
    )
