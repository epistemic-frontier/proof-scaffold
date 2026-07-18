from __future__ import annotations

from collections.abc import Mapping

from .errors import AuthoringSemanticError
from .language import BinderDecl, BindingClause, LanguageInterface
from .term import App, Term, Var, VariableRef


def variables(term: Term) -> frozenset[VariableRef]:
    if isinstance(term, Var):
        return frozenset((term.variable,))
    return frozenset().union(*(variables(argument) for argument in term.arguments))


def _binding_groups(
    term: App,
    binder: BinderDecl,
) -> dict[VariableRef, tuple[BindingClause, ...]]:
    grouped: dict[VariableRef, list[BindingClause]] = {}
    for binding in binder.bindings:
        bound = term.arguments[binding.variable_argument]
        if not isinstance(bound, Var):
            raise AuthoringSemanticError(f"binder variable is not a Var: {term.constructor}")
        grouped.setdefault(bound.variable, []).append(binding)
    return {variable: tuple(bindings) for variable, bindings in grouped.items()}


def _bound_for_argument(
    term: App,
    binder: BinderDecl,
    argument_index: int,
) -> frozenset[VariableRef]:
    result: set[VariableRef] = set()
    for variable, bindings in _binding_groups(term, binder).items():
        if any(argument_index in binding.scoped_arguments for binding in bindings):
            result.add(variable)
    return frozenset(result)


def free_variables(term: Term, language: LanguageInterface) -> frozenset[VariableRef]:
    if isinstance(term, Var):
        return frozenset((term.variable,))
    binder = language.binders.get(term.constructor)
    if binder is None:
        return frozenset().union(
            *(free_variables(argument, language) for argument in term.arguments)
        )
    variable_arguments = {binding.variable_argument for binding in binder.bindings}
    result: frozenset[VariableRef] = frozenset()
    for index, argument in enumerate(term.arguments):
        if index in variable_arguments:
            continue
        found = free_variables(argument, language)
        result |= found - _bound_for_argument(term, binder, index)
    return result


def _rename_bound(
    term: Term,
    old: VariableRef,
    new: VariableRef,
    language: LanguageInterface,
) -> Term:
    if isinstance(term, Var):
        return language.variable(new) if term.variable == old else term
    binder = language.binders.get(term.constructor)
    if binder is None:
        return language.apply(
            term.constructor,
            tuple(_rename_bound(argument, old, new, language) for argument in term.arguments),
        )
    variable_arguments = {binding.variable_argument for binding in binder.bindings}
    shadowed_arguments: set[int] = set()
    for variable, bindings in _binding_groups(term, binder).items():
        if variable == old:
            shadowed_arguments.update(
                index
                for binding in bindings
                for index in binding.scoped_arguments
            )
    arguments = list(term.arguments)
    for index, argument in enumerate(arguments):
        if index in variable_arguments or index in shadowed_arguments:
            continue
        arguments[index] = _rename_bound(argument, old, new, language)
    return language.apply(term.constructor, arguments)


def alpha_rename(
    term: App,
    replacement: VariableRef,
    language: LanguageInterface,
    *,
    variable_argument: int | None = None,
) -> App:
    binder = language.binders.get(term.constructor)
    if binder is None:
        raise AuthoringSemanticError(f"not a binder application: {term.constructor}")
    selected: BindingClause | None
    if variable_argument is None:
        if len(binder.bindings) != 1:
            raise AuthoringSemanticError(
                f"binder {term.constructor} requires a variable_argument selector"
            )
        selected = binder.bindings[0]
    else:
        if type(variable_argument) is not int:
            raise AuthoringSemanticError("variable_argument selector must be an integer")
        selected = next(
            (
                binding
                for binding in binder.bindings
                if binding.variable_argument == variable_argument
            ),
            None,
        )
    if selected is None:
        raise AuthoringSemanticError(
            f"binder {term.constructor} has no variable argument {variable_argument}"
        )
    bound = term.arguments[selected.variable_argument]
    if not isinstance(bound, Var):
        raise AuthoringSemanticError(f"binder variable is not a Var: {term.constructor}")
    if replacement.kind != bound.variable.kind:
        raise AuthoringSemanticError("alpha-renaming variable kind mismatch")
    if replacement in variables(term):
        raise AuthoringSemanticError("alpha-renaming variable is not fresh")

    group = _binding_groups(term, binder)[bound.variable]
    arguments = list(term.arguments)
    for binding in group:
        arguments[binding.variable_argument] = language.variable(replacement)
    for index in {
        index
        for binding in group
        for index in binding.scoped_arguments
    }:
        arguments[index] = _rename_bound(
            arguments[index],
            bound.variable,
            replacement,
            language,
        )
    return language.apply(term.constructor, arguments)


def _fresh_variable(variable: VariableRef, forbidden: frozenset[VariableRef]) -> VariableRef:
    index = 1
    while True:
        candidate = VariableRef(
            variable.scope,
            variable.owner,
            f"{variable.local_key}_{index}",
            variable.kind,
        )
        if candidate not in forbidden:
            return candidate
        index += 1


def substitute(
    term: Term,
    substitutions: Mapping[VariableRef, Term],
    language: LanguageInterface,
) -> Term:
    if isinstance(term, Var):
        replacement = substitutions.get(term.variable)
        if replacement is None:
            return term
        if replacement.sort != term.sort:
            raise AuthoringSemanticError(f"substitution sort mismatch: {term.variable.local_key}")
        return replacement
    binder = language.binders.get(term.constructor)
    if binder is None:
        return language.apply(
            term.constructor,
            tuple(substitute(argument, substitutions, language) for argument in term.arguments),
        )

    current = term
    processed_variable_arguments: set[int] = set()
    for binding in binder.bindings:
        if binding.variable_argument in processed_variable_arguments:
            continue
        groups = _binding_groups(current, binder)
        bound = current.arguments[binding.variable_argument]
        if not isinstance(bound, Var):
            raise AuthoringSemanticError(f"binder variable is not a Var: {term.constructor}")
        group = groups[bound.variable]
        processed_variable_arguments.update(item.variable_argument for item in group)

        replacement_free: frozenset[VariableRef] = frozenset()
        for index in {
            index
            for item in group
            for index in item.scoped_arguments
        }:
            hidden = _bound_for_argument(current, binder, index)
            active = {
                variable: replacement
                for variable, replacement in substitutions.items()
                if variable not in hidden
            }
            relevant = free_variables(current.arguments[index], language) & active.keys()
            for variable in relevant:
                replacement_free |= free_variables(active[variable], language)
        if bound.variable not in replacement_free:
            continue

        forbidden = (
            variables(current)
            | frozenset(substitutions)
            | frozenset().union(
                *(variables(replacement) for replacement in substitutions.values())
            )
        )
        current = alpha_rename(
            current,
            _fresh_variable(bound.variable, forbidden),
            language,
            variable_argument=binding.variable_argument,
        )

    variable_arguments = {binding.variable_argument for binding in binder.bindings}
    arguments = list(current.arguments)
    for index, argument in enumerate(arguments):
        if index in variable_arguments:
            continue
        hidden = _bound_for_argument(current, binder, index)
        active = {
            variable: replacement
            for variable, replacement in substitutions.items()
            if variable not in hidden
        }
        arguments[index] = substitute(argument, active, language)
    return language.apply(current.constructor, arguments)
