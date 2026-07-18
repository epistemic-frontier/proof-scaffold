from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from ._canonical import JsonValue, canonical_digest
from .errors import AuthoringSemanticError
from .ids import ConstructorId, Digest, NotationId
from .language import LanguageInterface, LanguageRequirement, is_semantic_subset
from .term import App, Term, VariableRef

Associativity: TypeAlias = Literal["left", "right"]


@dataclass(frozen=True, slots=True, kw_only=True)
class PrefixForm:
    token: str
    precedence: int


@dataclass(frozen=True, slots=True, kw_only=True)
class InfixForm:
    token: str
    precedence: int
    associativity: Associativity


@dataclass(frozen=True, slots=True, kw_only=True)
class CallForm:
    token: str


@dataclass(frozen=True, slots=True, kw_only=True)
class BinderForm:
    token: str
    precedence: int


NotationForm: TypeAlias = PrefixForm | InfixForm | CallForm | BinderForm


@dataclass(frozen=True, slots=True, kw_only=True)
class NotationDecl:
    constructor: ConstructorId
    form: NotationForm
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class NotationRequirement:
    id: NotationId
    digest: Digest | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class NotationSpec:
    id: NotationId
    language: LanguageRequirement
    extends: tuple[NotationRequirement, ...] = ()
    declarations: tuple[NotationDecl, ...] = ()


def _normalized(declaration: NotationDecl) -> NotationDecl:
    return NotationDecl(
        constructor=declaration.constructor,
        form=declaration.form,
        aliases=tuple(sorted(declaration.aliases)),
    )


@dataclass(frozen=True, slots=True)
class NotationInterface:
    id: NotationId
    language: LanguageInterface = field(compare=False, hash=False, repr=False)
    declarations: tuple[NotationDecl, ...] = field(compare=False, hash=False)
    digest: Digest

    def render(self, term: Term, variable_names: Mapping[VariableRef, str]) -> str:
        def render_at(item: Term, *, nested: bool) -> str:
            if not isinstance(item, App):
                name = variable_names.get(item.variable)
                if name is None:
                    raise AuthoringSemanticError(
                        f"no display name for variable: {item.variable.local_key}"
                    )
                return name
            declaration = next(
                (entry for entry in self.declarations if entry.constructor == item.constructor),
                None,
            )
            if declaration is None:
                raise AuthoringSemanticError(f"no notation for constructor: {item.constructor}")
            form = declaration.form
            if isinstance(form, PrefixForm):
                return f"{form.token} {render_at(item.arguments[0], nested=True)}"
            if isinstance(form, BinderForm):
                variable = render_at(item.arguments[0], nested=False)
                body = render_at(item.arguments[1], nested=False)
                rendered = f"{form.token} {variable} {body}"
                return f"({rendered})" if nested else rendered
            if isinstance(form, CallForm):
                arguments = ", ".join(render_at(argument, nested=True) for argument in item.arguments)
                return f"{form.token}({arguments})"
            left = render_at(item.arguments[0], nested=True)
            right = render_at(item.arguments[1], nested=True)
            return f"({left} {form.token} {right})"

        return render_at(term, nested=False)

    def parse(self, text: str, variables: Mapping[str, VariableRef]) -> Term:
        aliases: dict[str, NotationDecl] = {}
        for declaration in self.declarations:
            for token in (declaration.form.token, *declaration.aliases):
                aliases[token] = declaration
        tokens = re.findall(r"[^\W\d]\w*|\d+|[(),]|[^\s\w(),]+", text, re.UNICODE)
        position = 0

        def expression(minimum: int) -> Term:
            nonlocal position
            if position >= len(tokens):
                raise AuthoringSemanticError("unexpected end of notation")
            token = tokens[position]
            position += 1
            declaration = aliases.get(token)
            if token == "(":
                left = expression(0)
                if position >= len(tokens) or tokens[position] != ")":
                    raise AuthoringSemanticError("missing closing parenthesis")
                position += 1
            elif declaration is not None and isinstance(declaration.form, PrefixForm):
                left = self.language.apply(declaration.constructor, (expression(declaration.form.precedence),))
            elif declaration is not None and isinstance(declaration.form, BinderForm):
                if position >= len(tokens):
                    raise AuthoringSemanticError(f"expected bound variable after {token}")
                variable_name = tokens[position]
                position += 1
                variable = variables.get(variable_name)
                if variable is None:
                    raise AuthoringSemanticError(f"unknown bound variable: {variable_name}")
                left = self.language.apply(
                    declaration.constructor,
                    (
                        self.language.variable(variable),
                        expression(declaration.form.precedence),
                    ),
                )
            elif declaration is not None and isinstance(declaration.form, CallForm):
                if position >= len(tokens) or tokens[position] != "(":
                    raise AuthoringSemanticError(f"expected '(' after {token}")
                position += 1
                args: list[Term] = []
                while position < len(tokens) and tokens[position] != ")":
                    args.append(expression(0))
                    if position < len(tokens) and tokens[position] == ",":
                        position += 1
                    elif position >= len(tokens) or tokens[position] != ")":
                        raise AuthoringSemanticError("expected comma")
                if position >= len(tokens):
                    raise AuthoringSemanticError("missing closing parenthesis")
                position += 1
                left = self.language.apply(declaration.constructor, args)
            else:
                variable = variables.get(token)
                if variable is None:
                    raise AuthoringSemanticError(f"unknown variable or notation: {token}")
                left = self.language.variable(variable)
            while position < len(tokens):
                infix = aliases.get(tokens[position])
                if infix is None or not isinstance(infix.form, InfixForm) or infix.form.precedence < minimum:
                    break
                position += 1
                next_minimum = infix.form.precedence + (1 if infix.form.associativity == "left" else 0)
                left = self.language.apply(infix.constructor, (left, expression(next_minimum)))
            return left

        result = expression(0)
        if position != len(tokens):
            raise AuthoringSemanticError(f"unexpected token: {tokens[position]}")
        return result


def resolve_notation(spec: NotationSpec, language: LanguageInterface, dependencies: Mapping[NotationId, NotationInterface]) -> NotationInterface:
    if spec.language.id != language.id or (spec.language.semantic_digest is not None and spec.language.semantic_digest != language.semantic_digest):
        raise AuthoringSemanticError("notation language requirement mismatch")
    declarations: dict[ConstructorId, NotationDecl] = {}
    for requirement in sorted(spec.extends, key=lambda item: item.id):
        dependency = dependencies.get(requirement.id)
        if dependency is None:
            raise AuthoringSemanticError(f"missing notation dependency: {requirement.id}")
        if requirement.digest is not None and requirement.digest != dependency.digest:
            raise AuthoringSemanticError(f"notation digest mismatch: {requirement.id}")
        if not is_semantic_subset(dependency.language, language):
            raise AuthoringSemanticError(f"notation dependency language mismatch: {requirement.id}")
        for declaration in dependency.declarations:
            declaration = _normalized(declaration)
            old = declarations.get(declaration.constructor)
            if old is not None and old != declaration:
                raise AuthoringSemanticError(f"conflicting notation: {declaration.constructor}")
            declarations[declaration.constructor] = declaration
    for declaration in spec.declarations:
        declaration = _normalized(declaration)
        old = declarations.get(declaration.constructor)
        if old is not None and old != declaration:
            raise AuthoringSemanticError(f"conflicting notation: {declaration.constructor}")
        declarations[declaration.constructor] = declaration
    tokens: set[str] = set()
    for declaration in declarations.values():
        constructor = language.constructors.get(declaration.constructor)
        expected = (
            1
            if isinstance(declaration.form, PrefixForm)
            else 2
            if isinstance(declaration.form, (InfixForm, BinderForm))
            else None
        )
        if constructor is None or (expected is not None and len(constructor.inputs) != expected):
            raise AuthoringSemanticError(f"notation arity/target mismatch: {declaration.constructor}")
        if isinstance(declaration.form, BinderForm):
            binder = language.binders.get(declaration.constructor)
            if (
                binder is None
                or len(binder.bindings) != 1
                or binder.bindings[0].variable_argument != 0
                or binder.bindings[0].scoped_arguments != (1,)
            ):
                raise AuthoringSemanticError(f"notation binder mismatch: {declaration.constructor}")
        for token in (declaration.form.token, *declaration.aliases):
            if not token or token in tokens:
                raise AuthoringSemanticError(f"notation alias collision: {token!r}")
            tokens.add(token)
    ordered = tuple(sorted(declarations.values(), key=lambda item: item.constructor))
    declarations_json: list[JsonValue] = []
    for declaration in ordered:
        form = declaration.form
        form_json: dict[str, JsonValue] = {"token": form.token}
        if isinstance(form, PrefixForm):
            form_json.update({"kind": "prefix", "precedence": form.precedence})
        elif isinstance(form, InfixForm):
            form_json.update({"kind": "infix", "precedence": form.precedence, "associativity": form.associativity})
        elif isinstance(form, BinderForm):
            form_json.update({"kind": "binder", "precedence": form.precedence})
        else:
            form_json["kind"] = "call"
        declarations_json.append(
            {"constructor": str(declaration.constructor), "form": form_json, "aliases": list(declaration.aliases)}
        )
    digest = canonical_digest(
        {
            "version": "skfd.notation.v1",
            "language_semantic_digest": str(language.semantic_digest),
            "declarations": declarations_json,
        }
    )
    return NotationInterface(spec.id, language, ordered, digest)
