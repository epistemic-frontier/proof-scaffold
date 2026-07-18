"""Compatibility helpers from semantic Metamath bindings to legacy formulas."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from skfd.authoring.formula import ClassSort, Formula, SetVarSort, Sort, WffSort
from skfd.core.symbols import SymbolId

from .errors import AuthoringSemanticError
from .ids import ConstructorId, SortId
from .metamath_language import ArgumentPart, LiteralPart, ResolvedMetamathLanguageBinding, TokenRef
from .notation import CallForm, InfixForm, NotationInterface, PrefixForm

LegacyFormula = Formula[WffSort] | Formula[ClassSort] | Formula[SetVarSort]


@dataclass(frozen=True, slots=True)
class LegacySymbolSpec:
    name: str
    arity: int
    in_sorts: tuple[Sort, ...]
    out_sort: Sort
    precedence: int
    associativity: Literal["left", "right", "none"]
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LegacyPrefixFormation:
    prefix: TokenRef


@dataclass(frozen=True, slots=True)
class LegacyBinaryFormation:
    left_delimiter: TokenRef
    operator: TokenRef
    right_delimiter: TokenRef


def legacy_prefix_formation(
    binding: ResolvedMetamathLanguageBinding,
    constructor: ConstructorId,
) -> LegacyPrefixFormation:
    """Require and project a legacy prefix formation template."""
    formation = binding.formations.get(constructor)
    if formation is None:
        raise AuthoringSemanticError(f"no legacy Metamath formation for: {constructor}")
    parts = formation.template
    if (
        len(parts) != 2
        or not isinstance(parts[0], LiteralPart)
        or not isinstance(parts[1], ArgumentPart)
        or parts[1].index != 0
    ):
        raise AuthoringSemanticError(f"formation is not legacy prefix shape: {constructor}")
    return LegacyPrefixFormation(prefix=parts[0].token)


def legacy_binary_formation(
    binding: ResolvedMetamathLanguageBinding,
    constructor: ConstructorId,
) -> LegacyBinaryFormation:
    """Require and project a parenthesized legacy binary formation template."""
    formation = binding.formations.get(constructor)
    if formation is None:
        raise AuthoringSemanticError(f"no legacy Metamath formation for: {constructor}")
    parts = formation.template
    if (
        len(parts) != 5
        or not isinstance(parts[0], LiteralPart)
        or not isinstance(parts[1], ArgumentPart)
        or parts[1].index != 0
        or not isinstance(parts[2], LiteralPart)
        or not isinstance(parts[3], ArgumentPart)
        or parts[3].index != 1
        or not isinstance(parts[4], LiteralPart)
    ):
        raise AuthoringSemanticError(f"formation is not legacy binary shape: {constructor}")
    return LegacyBinaryFormation(
        left_delimiter=parts[0].token,
        operator=parts[2].token,
        right_delimiter=parts[4].token,
    )


def legacy_symbol_spec(
    binding: ResolvedMetamathLanguageBinding,
    notation: NotationInterface,
    constructor: ConstructorId,
    *,
    legacy_sorts: Mapping[SortId, Sort],
    call_precedence: int | None = None,
) -> LegacySymbolSpec:
    """Project semantic declarations into the old name-keyed symbol registry shape."""
    declaration = binding.language.constructors.get(constructor)
    formation = binding.formations.get(constructor)
    notation_decl = next(
        (item for item in notation.declarations if item.constructor == constructor),
        None,
    )
    if declaration is None or formation is None or notation_decl is None:
        raise AuthoringSemanticError(f"incomplete legacy symbol declaration: {constructor}")
    if notation.language.constructors.get(constructor) != declaration:
        raise AuthoringSemanticError(f"legacy notation language mismatch: {constructor}")
    try:
        in_sorts = tuple(legacy_sorts[item] for item in declaration.inputs)
        out_sort = legacy_sorts[declaration.output]
    except KeyError as error:
        raise AuthoringSemanticError(f"no legacy sort binding for: {error.args[0]}") from error

    form = notation_decl.form
    if isinstance(form, CallForm):
        if call_precedence is None:
            raise AuthoringSemanticError(
                f"call notation requires a legacy precedence: {constructor}"
            )
    spellings = (form.token, *notation_decl.aliases)
    backend_tokens = {
        part.token.local_name
        for part in formation.template
        if isinstance(part, LiteralPart)
    }
    backend_spellings = tuple(item for item in spellings if item in backend_tokens)
    if len(backend_spellings) != 1:
        raise AuthoringSemanticError(f"legacy operator spelling is ambiguous: {constructor}")
    name = backend_spellings[0]
    aliases = tuple(item for item in spellings if item != name)
    associativity: Literal["left", "right", "none"]
    if isinstance(form, PrefixForm):
        precedence = form.precedence
        associativity = "right"
    elif isinstance(form, InfixForm):
        precedence = form.precedence
        associativity = form.associativity
    elif isinstance(form, CallForm):
        assert call_precedence is not None
        precedence = call_precedence
        associativity = "none"
    else:
        raise AssertionError("unreachable notation form")
    return LegacySymbolSpec(
        name=name,
        arity=len(declaration.inputs),
        in_sorts=in_sorts,
        out_sort=out_sort,
        precedence=precedence,
        associativity=associativity,
        aliases=aliases,
    )


def build_legacy_formula(
    binding: ResolvedMetamathLanguageBinding,
    constructor: ConstructorId,
    arguments: Sequence[LegacyFormula],
    *,
    token_symbols: Mapping[TokenRef, SymbolId],
    legacy_sorts: Mapping[SortId, Sort],
) -> Formula[Sort]:
    """Apply a finite formation template to build a legacy token-level formula."""
    declaration = binding.language.constructors.get(constructor)
    formation = binding.formations.get(constructor)
    if declaration is None or formation is None:
        raise AuthoringSemanticError(f"no legacy Metamath formation for: {constructor}")
    if len(arguments) != len(declaration.inputs):
        raise AuthoringSemanticError(
            f"legacy constructor {constructor} expects {len(declaration.inputs)} arguments, "
            f"got {len(arguments)}"
        )
    for index, (argument, expected_sort) in enumerate(zip(arguments, declaration.inputs, strict=True)):
        legacy_sort = legacy_sorts.get(expected_sort)
        if legacy_sort is None:
            raise AuthoringSemanticError(f"no legacy sort binding for: {expected_sort}")
        if argument.sort != legacy_sort:
            raise AuthoringSemanticError(
                f"legacy constructor {constructor} argument {index} expects {legacy_sort}, "
                f"got {argument.sort}"
            )
    output_sort = legacy_sorts.get(declaration.output)
    if output_sort is None:
        raise AuthoringSemanticError(f"no legacy sort binding for: {declaration.output}")

    tokens: list[SymbolId] = []
    for part in formation.template:
        if isinstance(part, ArgumentPart):
            tokens.extend(arguments[part.index].tokens)
            continue
        symbol = token_symbols.get(part.token)
        if symbol is None:
            raise AuthoringSemanticError(
                f"no legacy symbol binding for token: {part.token.owner}/{part.token.local_name}"
            )
        tokens.append(symbol)
    return Formula(output_sort, tuple(tokens))


__all__ = [
    "LegacyBinaryFormation",
    "LegacyPrefixFormation",
    "LegacySymbolSpec",
    "build_legacy_formula",
    "legacy_binary_formation",
    "legacy_prefix_formation",
    "legacy_symbol_spec",
]
