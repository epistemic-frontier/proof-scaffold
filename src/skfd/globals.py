# skfd/globals.py
from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from skfd.builder import MMBuilder

# Context variables for thread-safe build execution
_current_mm = contextvars.ContextVar["MMBuilder | None"]("current_mm", default=None)
_current_deps = contextvars.ContextVar["Any | None"]("current_deps", default=None)


def set_context(mm: MMBuilder, deps: Any) -> Any:
    """Set the current build context. Returns tokens to reset."""
    t1 = _current_mm.set(mm)
    t2 = _current_deps.set(deps)
    return (t1, t2)


def reset_context(tokens: Any) -> None:
    """Reset the build context using tokens from set_context."""
    t1, t2 = tokens
    _current_mm.reset(t1)
    _current_deps.reset(t2)


class MMProxy:
    """Proxy for the thread-local MMBuilder."""

    def __getattr__(self, name: str) -> Any:
        mm = _current_mm.get()
        if mm is None:
            raise RuntimeError(
                "No active MMBuilder context. "
                "Are you running this script via 'skfd'?"
            )
        return getattr(mm, name)


class DepsProxy:
    """Proxy for the thread-local dependencies object."""

    def __getattr__(self, name: str) -> Any:
        deps = _current_deps.get()
        if deps is None:
            raise RuntimeError(
                "No active dependencies context. "
                "Are you running this script via 'skfd'?"
            )
        # deps is expected to be a dict or object
        if isinstance(deps, dict):
            try:
                return deps[name]
            except KeyError as err:
                raise AttributeError(f"Dependency '{name}' not found in context") from err
        return getattr(deps, name)
