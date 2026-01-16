# skfd/builder/scope.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

from skfd.core.errors import MMDSLError

Label: TypeAlias = str
Token: TypeAlias = str  # On the builder side (user facing), we deal with strings


@dataclass
class _Scope:
    # labels declared in this scope (for visibility + leakage prevention)
    local_labels: set[Label] = field(default_factory=set)

    # active floating hypotheses labels (map variable token -> label)
    active_f: dict[Token, Label] = field(default_factory=dict)

    # active essential hypotheses labels (ordered, as in Metamath)
    active_e: list[Label] = field(default_factory=list)

    # strict profile: forbid $e at top-level
    is_top_level: bool = False


class ScopeStack:
    def __init__(self) -> None:
        # initialize with a top-level scope
        self._scopes: list[_Scope] = [_Scope(is_top_level=True)]

    # push/pop ---------------------------------------------------------------
    def push(self) -> None:
        self._scopes.append(_Scope(is_top_level=False))

    def pop(self) -> None:
        if len(self._scopes) <= 1:
            raise MMDSLError("unbalanced scope pop")
        self._scopes.pop()

    # properties -------------------------------------------------------------
    @property
    def current(self) -> _Scope:
        return self._scopes[-1]

    @property
    def is_top_level(self) -> bool:
        return self.current.is_top_level

    @property
    def depth(self) -> int:
        return len(self._scopes)

    # label visibility -------------------------------------------------------
    def register_local_label(self, label: Label) -> None:
        self.current.local_labels.add(label)

    def visible_labels(self) -> set[Label]:
        s: set[Label] = set()
        for sc in self._scopes:
            s |= sc.local_labels
        return s

    # activations ------------------------------------------------------------
    def activate_f(self, var: Token, label: Label) -> None:
        self.current.active_f[var] = label

    def activate_e(self, label: Label) -> None:
        self.current.active_e.append(label)
