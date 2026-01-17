# skfd/__init__.py
from __future__ import annotations

from typing import TYPE_CHECKING

from .globals import DepsProxy, MMProxy

if TYPE_CHECKING:
    from skfd.builder import MMBuilder

# Public API for build scripts
mm: MMBuilder = MMProxy()  # type: ignore
deps: DepsProxy = DepsProxy()  # type: ignore

__all__ = ["mm", "deps"]
