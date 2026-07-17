from __future__ import annotations

from collections.abc import Mapping

from .errors import AuthoringSemanticError
from .language import LanguageInterface
from .term import App, Term, Var, VariableRef


def variables(term: Term) -> frozenset[VariableRef]:
    if isinstance(term, Var):
        return frozenset((term.variable,))
    return frozenset().union(*(variables(argument) for argument in term.arguments))


def free_variables(term: Term, language: LanguageInterface) -> frozenset[VariableRef]:
    if isinstance(term, Var):
        return frozenset((term.variable,))
    binder = language.binders.get(term.constructor)
    if binder is None:
        return frozenset().union(
            *(free_variables(argument, language) for argument in term.arguments)
        )
    bound = term.arguments[binder.variable_argument]
    if not isinstance(bound, Var):
        raise AuthoringSemanticError(f"binder variable is not a Var: {term.constructor}")
    result: frozenset[VariableRef] = frozenset()
    for index, argument in enumerate(term.arguments):
        if index == binder.variable_argument:
            continue
        found = free_variables(argument, language)
        if index in binder.scoped_arguments:
            found -= frozenset((bound.variable,))
        result |= found
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
    if binder is not None:
        bound = term.arguments[binder.variable_argument]
        if isinstance(bound, Var) and bound.variable == old:
            arguments = list(term.arguments)
            for index, argument in enumerate(arguments):
                if index != binder.variable_argument and index not in binder.scoped_arguments:
                    arguments[index] = _rename_bound(argument, old, new, language)
            return language.apply(term.constructor, arguments)
    return language.apply(
        term.constructor,
        tuple(_rename_bound(argument, old, new, language) for argument in term.arguments),
    )


def alpha_rename(
    term: App,
    replacement: VariableRef,
    language: LanguageInterface,
) -> App:
    binder = language.binders.get(term.constructor)
    if binder is None:
        raise AuthoringSemanticError(f"not a binder application: {term.constructor}")
    bound = term.arguments[binder.variable_argument]
    if not isinstance(bound, Var):
        raise AuthoringSemanticError(f"binder variable is not a Var: {term.constructor}")
    if replacement.kind != bound.variable.kind:
        raise AuthoringSemanticError("alpha-renaming variable kind mismatch")
    if replacement in variables(term):
        raise AuthoringSemanticError("alpha-renaming variable is not fresh")
    arguments = list(term.arguments)
    arguments[binder.variable_argument] = language.variable(replacement)
    for index in binder.scoped_arguments:
        arguments[index] = _rename_bound(arguments[index], bound.variable, replacement, language)
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
    bound = term.arguments[binder.variable_argument]
    if not isinstance(bound, Var):
        raise AuthoringSemanticError(f"binder variable is not a Var: {term.constructor}")
    scoped_substitutions = {
        variable: replacement
        for variable, replacement in substitutions.items()
        if variable != bound.variable
    }
    relevant = set().union(
        *(
            free_variables(term.arguments[index], language) & scoped_substitutions.keys()
            for index in binder.scoped_arguments
        )
    )
    replacement_free = frozenset().union(
        *(free_variables(scoped_substitutions[variable], language) for variable in relevant)
    )
    current = term
    if bound.variable in replacement_free:
        forbidden = (
            variables(term)
            | frozenset(substitutions)
            | frozenset().union(
                *(variables(replacement) for replacement in substitutions.values())
            )
        )
        current = alpha_rename(
            term,
            _fresh_variable(bound.variable, forbidden),
            language,
        )
        bound = current.arguments[binder.variable_argument]
        assert isinstance(bound, Var)
    arguments = list(current.arguments)
    for index, argument in enumerate(arguments):
        if index == binder.variable_argument:
            continue
        active = scoped_substitutions if index in binder.scoped_arguments else substitutions
        arguments[index] = substitute(argument, active, language)
    return language.apply(current.constructor, arguments)
