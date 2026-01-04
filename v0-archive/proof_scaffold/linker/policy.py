from __future__ import annotations

from collections.abc import Callable, Iterable
from collections.abc import Iterable as TypingIterable
from typing import Any, Protocol, TypeVar, overload

T = TypeVar("T")


class _SupportsRichComparison(Protocol):
    def __lt__(self, other: Any, /) -> bool: ...


_T_ord = TypeVar("_T_ord", bound=_SupportsRichComparison)


@overload
def stable_sorted(
    iterable: Iterable[_T_ord], *, reverse: bool = False
) -> list[_T_ord]: ...


@overload
def stable_sorted(
    iterable: Iterable[T], *, key: Callable[[T], Any], reverse: bool = False
) -> list[T]: ...


def stable_sorted(
    iterable: Iterable[Any],
    *,
    key: Callable[[Any], Any] | None = None,
    reverse: bool = False,
) -> list[Any]:
    """Deterministic sort wrapper to centralize ordering policy."""
    return sorted(iterable, key=key, reverse=reverse)


def pick_owner(owners: set[str]) -> str:
    """Pick a canonical owner deterministically.

    Current policy: lexical minimum.
    """
    if not owners:
        raise ValueError("pick_owner requires non-empty owners")
    return stable_sorted(owners)[0]


def mangle_suffix(unit_id: str) -> str:
    """Deterministic, readable mangling for unit suffixes."""
    return unit_id.replace("/", "_").replace(".", "_")


def stable_unit_order(units: TypingIterable[str]) -> list[str]:
    return stable_sorted(units)
