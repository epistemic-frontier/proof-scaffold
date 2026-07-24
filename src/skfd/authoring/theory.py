"""Read-only Theory facade for the generated semantic source surface.

This module is the Phase 0 deliverable of Project 025.  It adds a thin,
additive layer over the existing semantic kernel:

- ``Theory``: registers assertion declarations (axiom / definition /
  primitive rule / theorem) made at module import time and resolves
  assertion references for proof elaboration.
- ``AssertionHandle``: the module-level binding returned by the
  declaration calls.  It carries the assertion signature, the lazily
  registered proof body, and interface-policy metadata (``deprecated``,
  ``internal``).
- ``TheoryProofAuthor``: a forward, linear proof author that resolves
  assertions against the *live* theory registry so that function-local
  imports inside proof bodies work with lazy elaboration.

Importing a module that declares assertions never elaborates proofs.
Elaboration happens on first ``AssertionHandle.implementation`` access,
in ``Theory.verify_all()``, or in explicit build/emission flows.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import TypeAlias, TypeVar, overload

from .assertion import (
    AssertionKind,
    AssertionSignature,
    AssertionStep,
    CheckedProofPrefix,
    CompleteProof,
    HypothesisStep,
    _apply_assertion_step,
    _finalize_proof,
    _validate_assertion_judgments,
    create_proof_prefix,
    signature_from_axiom,
    signature_from_definition,
    signature_from_primitive_rule,
)
from .errors import AuthoringSemanticError
from .ids import (
    AssertionId,
    Digest,
    JudgmentKindId,
    OwnerId,
    ProofId,
    RuleId,
    StepId,
    VariableKindId,
)
from .judgment import (
    AxiomDecl,
    CalculusInterface,
    DefinitionDecl,
    DistinctPair,
    Judgment,
    PrimitiveRuleDecl,
    resolve_axiom,
    resolve_definition,
)
from .language import LanguageInterface, is_semantic_subset
from .notation import NotationInterface
from .term import App, Term, Var, VariableRef

_T = TypeVar("_T")

ProofStep: TypeAlias = HypothesisStep | AssertionStep
FormulaLike: TypeAlias = "str | Term | Judgment"
ProofBody: TypeAlias = "Callable[[TheoryProofAuthor], CompleteProof]"


class TheoryError(AuthoringSemanticError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class UpstreamPin:
    """Expected interface digests for one upstream theory (fail closed)."""

    language: Digest | None = None
    calculus: Digest | None = None
    notation: Digest | None = None


@dataclass(frozen=True, slots=True)
class VerificationEntry:
    label: str
    kind: AssertionKind
    error: str | None


@dataclass(frozen=True, slots=True)
class VerificationReport:
    entries: tuple[VerificationEntry, ...]

    @property
    def ok(self) -> bool:
        return all(entry.error is None for entry in self.entries)

    @property
    def failures(self) -> tuple[VerificationEntry, ...]:
        return tuple(entry for entry in self.entries if entry.error is not None)

    def raise_if_failed(self) -> None:
        failures = self.failures
        if failures:
            details = "; ".join(
                f"{entry.label}: {entry.error}" for entry in failures
            )
            raise TheoryError(f"theory verification failed: {details}")


class AssertionHandle:
    """Module-level binding for one registered assertion.

    The handle is the only sanctioned channel to the proof body: the
    ``proof`` decorator registers the body without executing it, and
    ``implementation`` elaborates lazily (once, cached).
    """

    __slots__ = (
        "_body",
        "_declared_variables",
        "_dummy_variables",
        "_implementation",
        "_names",
        "_proof_distinct",
        "_signature",
        "_theory",
        "deprecated",
        "doc",
        "internal",
    )

    def __init__(
        self,
        theory: Theory,
        signature: AssertionSignature,
        *,
        declared_variables: tuple[VariableRef, ...],
        names: Mapping[str, VariableRef],
        doc: str | None,
        deprecated: str | None,
        internal: bool,
    ) -> None:
        self._theory = theory
        self._signature = signature
        self._declared_variables = declared_variables
        self._names: dict[str, VariableRef] = dict(names)
        self.doc = doc
        self.deprecated = deprecated
        self.internal = internal
        self._body: ProofBody | None = None
        self._dummy_variables: tuple[str, ...] = ()
        self._proof_distinct: tuple[tuple[str, str], ...] = ()
        self._implementation: CompleteProof | None = None

    @property
    def label(self) -> str:
        return self._signature.canonical_label

    @property
    def kind(self) -> AssertionKind:
        return self._signature.kind

    @property
    def id(self) -> AssertionId:
        return self._signature.id

    @property
    def signature(self) -> AssertionSignature:
        return self._signature

    @property
    def schema_variables(self) -> tuple[VariableRef, ...]:
        """Schema variables in declared (ABI) order."""
        return self._declared_variables

    @property
    def premises(self) -> tuple[Judgment, ...]:
        return self._signature.premises

    @property
    def conclusion(self) -> Judgment:
        return self._signature.conclusion

    @overload
    def proof(self, body: ProofBody) -> ProofBody: ...

    @overload
    def proof(
        self,
        *,
        dummy_variables: Sequence[str] = (),
        distinct: Sequence[tuple[str, str]] = (),
    ) -> Callable[[ProofBody], ProofBody]: ...

    def proof(
        self,
        body: ProofBody | None = None,
        *,
        dummy_variables: Sequence[str] = (),
        distinct: Sequence[tuple[str, str]] = (),
    ) -> ProofBody | Callable[[ProofBody], ProofBody]:
        """Register the proof body without executing it."""
        if body is not None:
            return self._register_body(body, (), ())

        def decorate(inner: ProofBody) -> ProofBody:
            return self._register_body(
                inner, tuple(dummy_variables), tuple(distinct)
            )

        return decorate

    def _register_body(
        self,
        body: ProofBody,
        dummy_variables: tuple[str, ...],
        distinct: tuple[tuple[str, str], ...],
    ) -> ProofBody:
        if self.kind != "theorem":
            raise TheoryError(
                f"{self.label}: only theorems accept a proof body"
            )
        if self._body is not None:
            raise TheoryError(
                f"{self.label}: proof body is already registered"
            )
        self._body = body
        self._dummy_variables = dummy_variables
        self._proof_distinct = distinct
        return body

    @property
    def has_implementation(self) -> bool:
        return self._body is not None

    @property
    def implementation(self) -> CompleteProof:
        """Elaborate the registered proof body (lazily, cached)."""
        if self._implementation is None:
            self._implementation = self._theory._elaborate(self)
        return self._implementation


class TheoryProofAuthor:
    """Forward, linear proof author bound to a live theory registry.

    Unlike ``ProofAuthor``, assertion references are resolved at each
    ``use`` call, so assertions registered by function-local imports
    inside the running proof body are visible.
    """

    def __init__(
        self,
        theory: Theory,
        signature: AssertionSignature,
        *,
        proof_id: ProofId,
        active_distinct: Sequence[DistinctPair],
        scope: Mapping[str, VariableRef],
    ) -> None:
        self._theory = theory
        self._calculus = theory.calculus
        self._base_prefix = create_proof_prefix(
            proof_id,
            self._calculus,
            signature.premises,
            active_distinct=active_distinct,
            signature=signature,
        )
        self._steps: list[AssertionStep] = []
        self._results: dict[StepId, Judgment] = {
            step.id: step.result for step in self._base_prefix.hypotheses
        }
        self._known_steps: dict[int, ProofStep] = {
            id(step): step for step in self._base_prefix.hypotheses
        }
        self._scope: dict[str, VariableRef] = dict(scope)

    @property
    def hypotheses(self) -> tuple[HypothesisStep, ...]:
        return self._base_prefix.hypotheses

    def hypothesis(self, index: int) -> HypothesisStep:
        return self._base_prefix.hypotheses[index]

    def use(
        self,
        assertion: AssertionHandle | AssertionSignature | AssertionId,
        *premises: ProofStep,
        target: FormulaLike | None = None,
        subst: Mapping[str | VariableRef, FormulaLike] | None = None,
    ) -> AssertionStep:
        signature, names = self._resolve(assertion)
        validation_key = (self._calculus.digest, signature.id)
        if validation_key not in self._theory._validated:
            _validate_assertion_judgments(self._calculus, signature)
            self._theory._validated.add(validation_key)
        premise_ids = tuple(self._known_step_id(step) for step in premises)
        step = _apply_assertion_step(
            self._base_prefix,
            self._calculus,
            signature,
            premise_ids,
            known_results=self._results,
            step_index=len(self._base_prefix.hypotheses) + len(self._steps),
            validate_assertion_judgments=False,
            target=None if target is None else self._theory._judgment(target, self._scope),
            subst=None if subst is None else self._convert_subst(signature, names, subst),
        )
        self._steps.append(step)
        self._results[step.id] = step.result
        self._known_steps[id(step)] = step
        return step

    def qed(self, root: ProofStep) -> CompleteProof:
        root_id = self._known_step_id(root)
        prefix = CheckedProofPrefix(
            proof_id=self._base_prefix.proof_id,
            calculus_digest=self._base_prefix.calculus_digest,
            signature=self._base_prefix.signature,
            hypotheses=self._base_prefix.hypotheses,
            steps=tuple(self._steps),
            active_distinct=self._base_prefix.active_distinct,
        )
        return _finalize_proof(
            prefix,
            self._calculus,
            root=root_id,
            validate_prefix_judgments=False,
        )

    def _resolve(
        self,
        assertion: AssertionHandle | AssertionSignature | AssertionId,
    ) -> tuple[AssertionSignature, Mapping[str, VariableRef] | None]:
        names: Mapping[str, VariableRef] | None = None
        if isinstance(assertion, AssertionHandle):
            if assertion.deprecated is not None:
                warnings.warn(
                    f"assertion {assertion.label} is deprecated: "
                    f"{assertion.deprecated}",
                    DeprecationWarning,
                    stacklevel=3,
                )
            signature = assertion.signature
            names = assertion._names
        elif isinstance(assertion, AssertionSignature):
            signature = assertion
        else:
            found = self._theory._signature_for(assertion)
            if found is None:
                raise TheoryError(f"unknown assertion: {assertion}")
            signature = found
        known = self._theory._signature_for(signature.id)
        if known != signature:
            raise TheoryError(
                f"assertion is not registered in this theory or its "
                f"upstream theories: {signature.id}"
            )
        return signature, names

    def _convert_subst(
        self,
        signature: AssertionSignature,
        names: Mapping[str, VariableRef] | None,
        subst: Mapping[str | VariableRef, FormulaLike],
    ) -> dict[VariableRef, Term]:
        by_name: Mapping[str, VariableRef]
        if names is not None:
            by_name = names
        else:
            by_name = {
                variable.local_key: variable
                for variable in signature.schema_variables
            }
        converted: dict[VariableRef, Term] = {}
        for key, value in subst.items():
            if isinstance(key, VariableRef):
                variable = key
            else:
                found = by_name.get(key)
                if found is None:
                    raise TheoryError(
                        f"unknown substitution variable for "
                        f"{signature.canonical_label}: {key!r}"
                    )
                variable = found
            if isinstance(value, (Var, App)):
                term = value
            elif isinstance(value, str):
                term = self._theory._parse_term(value, self._scope)
            else:
                raise TheoryError(
                    "substitution values must be notation strings or terms"
                )
            converted[variable] = term
        return converted

    def _known_step_id(self, step: ProofStep) -> StepId:
        known = self._known_steps.get(id(step))
        if known is not step:
            raise TheoryError(
                "proof steps must be created by this proof author"
            )
        return step.id


class Theory:
    """Read-only facade binding language, calculus, notation and the
    package-level assertion registry."""

    theory_id: str
    namespace: str
    language: LanguageInterface
    calculus: CalculusInterface
    notation: NotationInterface | None

    def __init__(
        self,
        *,
        theory_id: str,
        namespace: str,
        language: LanguageInterface,
        calculus: CalculusInterface,
        provable_judgment: JudgmentKindId,
        variable_kinds: Mapping[str, VariableKindId],
        notation: NotationInterface | None = None,
        upstreams: Sequence[Theory] = (),
    ) -> None:
        if not theory_id:
            raise TheoryError("theory_id must be non-empty")
        # Fail closed on namespaces that cannot form canonical ids.
        try:
            AssertionId(f"{namespace}#assertion:namespace-probe")
        except ValueError as error:
            raise TheoryError(f"invalid theory namespace: {namespace!r}") from error
        if calculus.language.semantic_digest != language.semantic_digest:
            raise TheoryError("calculus language does not match the theory language")
        if notation is not None and (
            notation.language.semantic_digest != language.semantic_digest
        ):
            raise TheoryError("notation language does not match the theory language")
        declaration = calculus.judgments.get(provable_judgment)
        if declaration is None:
            raise TheoryError(f"unknown provable judgment kind: {provable_judgment}")
        if len(declaration.arguments) != 1:
            raise TheoryError(
                f"provable judgment kind must take exactly one argument: "
                f"{provable_judgment}"
            )
        for kind_name, kind_id in variable_kinds.items():
            if not kind_name:
                raise TheoryError("variable kind names must be non-empty")
            if kind_id not in language.variable_kinds:
                raise TheoryError(f"unknown variable kind: {kind_id}")
        seen_namespaces = {namespace}
        for upstream in upstreams:
            if upstream.namespace in seen_namespaces:
                raise TheoryError(
                    f"duplicate theory namespace: {upstream.namespace}"
                )
            seen_namespaces.add(upstream.namespace)
            if not is_semantic_subset(upstream.language, language):
                raise TheoryError(
                    f"upstream theory language is not a semantic subset: "
                    f"{upstream.namespace}"
                )
        self.theory_id = theory_id
        self.namespace = namespace
        self.language = language
        self.calculus = calculus
        self.notation = notation
        self._provable = provable_judgment
        self._variable_kinds: dict[str, VariableKindId] = dict(variable_kinds)
        self._upstreams = tuple(upstreams)
        self._handles: dict[str, AssertionHandle] = {}
        self._by_id: dict[AssertionId, AssertionHandle] = {}
        self._validated: set[tuple[Digest, AssertionId]] = set()

    @classmethod
    def create(
        cls,
        *,
        theory_id: str,
        namespace: str,
        language: LanguageInterface,
        calculus: CalculusInterface,
        provable_judgment: JudgmentKindId,
        variable_kinds: Mapping[str, VariableKindId],
        notation: NotationInterface | None = None,
    ) -> Theory:
        return cls(
            theory_id=theory_id,
            namespace=namespace,
            language=language,
            calculus=calculus,
            provable_judgment=provable_judgment,
            variable_kinds=variable_kinds,
            notation=notation,
        )

    @classmethod
    def extend(
        cls,
        *upstreams: Theory,
        theory_id: str,
        namespace: str,
        language: LanguageInterface,
        calculus: CalculusInterface,
        provable_judgment: JudgmentKindId,
        variable_kinds: Mapping[str, VariableKindId],
        notation: NotationInterface | None = None,
        expected_upstream: Mapping[str, UpstreamPin] | None = None,
    ) -> Theory:
        if not upstreams:
            raise TheoryError("Theory.extend requires at least one upstream theory")
        if expected_upstream is not None:
            for upstream in upstreams:
                pin = expected_upstream.get(upstream.namespace)
                if pin is None:
                    raise TheoryError(
                        f"missing upstream pin: {upstream.namespace}"
                    )
                _check_pin(upstream, pin)
            unknown = set(expected_upstream) - {
                upstream.namespace for upstream in upstreams
            }
            if unknown:
                raise TheoryError(
                    f"upstream pin references unknown theory: {min(unknown)}"
                )
        return cls(
            theory_id=theory_id,
            namespace=namespace,
            language=language,
            calculus=calculus,
            provable_judgment=provable_judgment,
            variable_kinds=variable_kinds,
            notation=notation,
            upstreams=upstreams,
        )

    # ── declarations ─────────────────────────────────────────────────

    def theorem(
        self,
        label: str,
        *,
        assertion_id: AssertionId | str | None = None,
        schema: Sequence[str],
        conclusion: FormulaLike,
        premises: Sequence[FormulaLike] = (),
        distinct: Sequence[tuple[str, str]] = (),
        doc: str | None = None,
        deprecated: str | None = None,
        internal: bool = False,
    ) -> AssertionHandle:
        resolved_id = self._new_assertion_id(label, assertion_id)
        declared, names = self._schema(label, resolved_id, schema)
        signature = self._wrap(
            label,
            lambda: AssertionSignature(
                id=resolved_id,
                canonical_label=label,
                kind="theorem",
                schema_variables=declared,
                premises=tuple(
                    self._judgment(premise, names) for premise in premises
                ),
                conclusion=self._judgment(conclusion, names),
                mandatory_distinct=self._distinct(label, distinct, names),
            ),
        )
        return self._register(
            signature,
            declared_variables=declared,
            names=names,
            doc=doc,
            deprecated=deprecated,
            internal=internal,
        )

    def axiom(
        self,
        label: str,
        *,
        assertion_id: AssertionId | str | None = None,
        schema: Sequence[str],
        conclusion: FormulaLike,
        distinct: Sequence[tuple[str, str]] = (),
        doc: str | None = None,
        deprecated: str | None = None,
        internal: bool = False,
    ) -> AssertionHandle:
        resolved_id = self._new_assertion_id(label, assertion_id)
        declared, names = self._schema(label, resolved_id, schema)
        signature = self._wrap(
            label,
            lambda: replace(
                signature_from_axiom(
                    resolve_axiom(
                        AxiomDecl(
                            id=resolved_id,
                            schema_variables=declared,
                            conclusion=self._judgment(conclusion, names),
                            mandatory_distinct=self._distinct(label, distinct, names),
                        ),
                        self.calculus,
                    ),
                    canonical_label=label,
                ),
                schema_variables=declared,
            ),
        )
        return self._register(
            signature,
            declared_variables=declared,
            names=names,
            doc=doc,
            deprecated=deprecated,
            internal=internal,
        )

    def definition(
        self,
        label: str,
        *,
        assertion_id: AssertionId | str | None = None,
        schema: Sequence[str],
        conclusion: FormulaLike,
        distinct: Sequence[tuple[str, str]] = (),
        doc: str | None = None,
        deprecated: str | None = None,
        internal: bool = False,
    ) -> AssertionHandle:
        resolved_id = self._new_assertion_id(label, assertion_id)
        declared, names = self._schema(label, resolved_id, schema)
        signature = self._wrap(
            label,
            lambda: replace(
                signature_from_definition(
                    resolve_definition(
                        DefinitionDecl(
                            id=resolved_id,
                            schema_variables=declared,
                            conclusion=self._judgment(conclusion, names),
                            mandatory_distinct=self._distinct(label, distinct, names),
                        ),
                        self.calculus,
                    ),
                    canonical_label=label,
                ),
                schema_variables=declared,
            ),
        )
        return self._register(
            signature,
            declared_variables=declared,
            names=names,
            doc=doc,
            deprecated=deprecated,
            internal=internal,
        )

    def primitive_rule(
        self,
        label: str,
        *,
        assertion_id: AssertionId | str | None = None,
        doc: str | None = None,
        deprecated: str | None = None,
        internal: bool = False,
    ) -> AssertionHandle:
        resolved_id = self._new_assertion_id(label, assertion_id)
        rule_id = RuleId(f"{self.namespace}#rule:{label}")
        rule = self._wrap(label, lambda: self.calculus.rule(rule_id))
        if assertion_id is not None:
            rule = _rebind_primitive_rule(rule, resolved_id)
        signature = signature_from_primitive_rule(
            rule,
            assertion_id=resolved_id,
            canonical_label=label,
        )
        names = {
            variable.local_key: variable
            for variable in signature.schema_variables
        }
        return self._register(
            signature,
            declared_variables=signature.schema_variables,
            names=names,
            doc=doc,
            deprecated=deprecated,
            internal=internal,
        )

    # ── views ────────────────────────────────────────────────────────

    @property
    def assertions(self) -> Mapping[str, AssertionHandle]:
        """Registered assertions by canonical label, in registration order."""
        return MappingProxyType(self._handles)

    @property
    def upstreams(self) -> tuple[Theory, ...]:
        return self._upstreams

    def verify_all(self) -> VerificationReport:
        """Elaborate every registered theorem and report per-assertion errors."""
        entries: list[VerificationEntry] = []
        for handle in self._handles.values():
            error: str | None = None
            if handle.kind == "theorem":
                try:
                    handle.implementation
                except AuthoringSemanticError as failure:
                    error = str(failure)
            entries.append(VerificationEntry(handle.label, handle.kind, error))
        return VerificationReport(tuple(entries))

    # ── internals ────────────────────────────────────────────────────

    def _new_assertion_id(
        self,
        label: str,
        assertion_id: AssertionId | str | None,
    ) -> AssertionId:
        if not label:
            raise TheoryError("assertion label must be non-empty")
        try:
            default_id = AssertionId(f"{self.namespace}#assertion:{label}")
        except ValueError as error:
            raise TheoryError(f"invalid assertion label: {label!r}") from error
        if label in self._handles:
            raise TheoryError(f"duplicate assertion label: {label}")
        for upstream in self._upstreams:
            if upstream._owns_label(label):
                raise TheoryError(
                    f"assertion label conflicts with upstream theory "
                    f"{upstream.namespace}: {label}"
                )
        resolved_id = (
            default_id
            if assertion_id is None
            else self._explicit_assertion_id(label, assertion_id)
        )
        if resolved_id in self._by_id:
            raise TheoryError(f"duplicate assertion identifier: {resolved_id}")
        for upstream in self._upstreams:
            if upstream._signature_for(resolved_id) is not None:
                raise TheoryError(
                    f"assertion identifier conflicts with upstream theory "
                    f"{upstream.namespace}: {resolved_id}"
                )
        return resolved_id

    @staticmethod
    def _explicit_assertion_id(
        label: str,
        assertion_id: AssertionId | str,
    ) -> AssertionId:
        try:
            if isinstance(assertion_id, AssertionId):
                return AssertionId(assertion_id.value)
            if isinstance(assertion_id, str):
                return AssertionId(assertion_id)
        except ValueError as error:
            raise TheoryError(
                f"{label}: invalid assertion identifier: {assertion_id!r}"
            ) from error
        raise TheoryError(
            f"{label}: assertion_id must be an AssertionId or string"
        )

    def _owns_label(self, label: str) -> bool:
        if label in self._handles:
            return True
        return any(upstream._owns_label(label) for upstream in self._upstreams)

    def _signature_for(self, assertion_id: AssertionId) -> AssertionSignature | None:
        handle = self._by_id.get(assertion_id)
        if handle is not None:
            return handle.signature
        for upstream in self._upstreams:
            found = upstream._signature_for(assertion_id)
            if found is not None:
                return found
        return None

    def _register(
        self,
        signature: AssertionSignature,
        *,
        declared_variables: tuple[VariableRef, ...],
        names: Mapping[str, VariableRef],
        doc: str | None,
        deprecated: str | None,
        internal: bool,
    ) -> AssertionHandle:
        self._wrap(
            signature.canonical_label,
            lambda: _validate_assertion_judgments(self.calculus, signature),
        )
        self._validated.add((self.calculus.digest, signature.id))
        handle = AssertionHandle(
            self,
            signature,
            declared_variables=declared_variables,
            names=names,
            doc=doc,
            deprecated=deprecated,
            internal=internal,
        )
        self._handles[signature.canonical_label] = handle
        self._by_id[signature.id] = handle
        return handle

    def _schema(
        self,
        label: str,
        assertion_id: AssertionId,
        entries: Sequence[str],
    ) -> tuple[tuple[VariableRef, ...], dict[str, VariableRef]]:
        owner = OwnerId(str(assertion_id))
        declared: list[VariableRef] = []
        names: dict[str, VariableRef] = {}
        for entry in entries:
            name, separator, kind_name = entry.partition(":")
            name = name.strip()
            kind_name = kind_name.strip()
            if not separator or not name or not kind_name:
                raise TheoryError(
                    f"{label}: schema entries must be '<name>:<kind>', "
                    f"got {entry!r}"
                )
            kind = self._variable_kinds.get(kind_name)
            if kind is None:
                raise TheoryError(
                    f"{label}: unknown schema variable kind: {kind_name!r}"
                )
            if name in names:
                raise TheoryError(
                    f"{label}: duplicate schema variable: {name!r}"
                )
            reference = VariableRef("schema", owner, name, kind)
            declared.append(reference)
            names[name] = reference
        return tuple(declared), names

    def _distinct(
        self,
        label: str,
        pairs: Sequence[tuple[str, str]],
        names: Mapping[str, VariableRef],
    ) -> tuple[DistinctPair, ...]:
        resolved: list[DistinctPair] = []
        for left, right in pairs:
            left_variable = names.get(left)
            right_variable = names.get(right)
            if left_variable is None or right_variable is None:
                missing = left if left_variable is None else right
                raise TheoryError(
                    f"{label}: distinct endpoint is not a declared "
                    f"variable: {missing!r}"
                )
            resolved.append(DistinctPair(left_variable, right_variable))
        return tuple(resolved)

    def _judgment(
        self,
        value: FormulaLike,
        scope: Mapping[str, VariableRef],
    ) -> Judgment:
        if isinstance(value, Judgment):
            return self.calculus.judgment(value.kind, value.arguments)
        if isinstance(value, (Var, App)):
            return self.calculus.judgment(self._provable, (value,))
        if isinstance(value, str):
            return self.calculus.judgment(
                self._provable, (self._parse_term(value, scope),)
            )
        raise TheoryError(
            "premises and conclusions must be notation strings, terms, "
            "or judgments"
        )

    def _parse_term(self, text: str, scope: Mapping[str, VariableRef]) -> Term:
        if self.notation is None:
            raise TheoryError(
                "theory has no notation; pass terms or judgments instead "
                "of notation strings"
            )
        return self.notation.parse(text, scope)

    def _elaborate(self, handle: AssertionHandle) -> CompleteProof:
        body = handle._body
        if body is None:
            raise TheoryError(
                f"{handle.label}: no proof implementation registered"
            )
        proof_id = ProofId(f"{self.namespace}#proof:{handle.label}")
        scope: dict[str, VariableRef] = dict(handle._names)
        dummy_owner = OwnerId(str(proof_id))
        for entry in handle._dummy_variables:
            name, separator, kind_name = entry.partition(":")
            name = name.strip()
            kind_name = kind_name.strip()
            if not separator or not name or not kind_name:
                raise TheoryError(
                    f"{handle.label}: dummy variables must be "
                    f"'<name>:<kind>', got {entry!r}"
                )
            kind = self._variable_kinds.get(kind_name)
            if kind is None:
                raise TheoryError(
                    f"{handle.label}: unknown dummy variable kind: "
                    f"{kind_name!r}"
                )
            if name in scope:
                raise TheoryError(
                    f"{handle.label}: duplicate dummy variable: {name!r}"
                )
            scope[name] = VariableRef("local", dummy_owner, name, kind)
        active: list[DistinctPair] = list(handle.signature.mandatory_distinct)
        for left, right in handle._proof_distinct:
            left_variable = scope.get(left)
            right_variable = scope.get(right)
            if left_variable is None or right_variable is None:
                missing = left if left_variable is None else right
                raise TheoryError(
                    f"{handle.label}: proof distinct endpoint is not in "
                    f"scope: {missing!r}"
                )
            active.append(DistinctPair(left_variable, right_variable))
        author = TheoryProofAuthor(
            self,
            handle.signature,
            proof_id=proof_id,
            active_distinct=tuple(active),
            scope=scope,
        )
        result = self._wrap(handle.label, lambda: body(author))
        if not isinstance(result, CompleteProof):
            raise TheoryError(
                f"{handle.label}: proof body must return the value of "
                f"proof.qed(...)"
            )
        if result.signature != handle.signature:
            raise TheoryError(
                f"{handle.label}: proof does not prove its declared signature"
            )
        return result

    def _wrap(self, label: str, action: Callable[[], _T]) -> _T:
        try:
            return action()
        except TheoryError:
            raise
        except AuthoringSemanticError as error:
            raise TheoryError(f"{label}: {error}") from error


def _rebind_primitive_rule(
    rule: PrimitiveRuleDecl,
    assertion_id: AssertionId,
) -> PrimitiveRuleDecl:
    """Alpha-rebind a calculus rule to an explicit assertion identity.

    Calculus-owned variables remain the compatibility default. Generated
    providers that supply an upstream assertion identity instead receive a
    signature whose complete schema is owned by that identity.
    """
    owner = OwnerId(str(assertion_id))
    rebound = {
        variable: VariableRef(
            variable.scope,
            owner,
            variable.local_key,
            variable.kind,
        )
        for variable in rule.schema_variables
    }

    def term(value: Term) -> Term:
        if isinstance(value, Var):
            return Var(rebound[value.variable], value.sort)
        return App(
            value.constructor,
            tuple(term(argument) for argument in value.arguments),
            value.sort,
        )

    def judgment(value: Judgment) -> Judgment:
        return Judgment(value.kind, tuple(term(argument) for argument in value.arguments))

    return replace(
        rule,
        schema_variables=tuple(rebound[variable] for variable in rule.schema_variables),
        premises=tuple(judgment(premise) for premise in rule.premises),
        conclusion=judgment(rule.conclusion),
        mandatory_distinct=tuple(
            DistinctPair(rebound[pair.left], rebound[pair.right])
            for pair in rule.mandatory_distinct
        ),
    )


def _check_pin(upstream: Theory, pin: UpstreamPin) -> None:
    if pin.language is not None and (
        pin.language != upstream.language.semantic_digest
    ):
        raise TheoryError(
            f"upstream language digest mismatch: {upstream.namespace}"
        )
    if pin.calculus is not None and pin.calculus != upstream.calculus.digest:
        raise TheoryError(
            f"upstream calculus digest mismatch: {upstream.namespace}"
        )
    if pin.notation is not None:
        if upstream.notation is None or pin.notation != upstream.notation.digest:
            raise TheoryError(
                f"upstream notation digest mismatch: {upstream.namespace}"
            )
