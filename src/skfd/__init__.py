# skfd/__init__.py
from __future__ import annotations

from typing import Any

from .globals import DepsProxy, MMProxy

# Public API for build scripts
mm: Any = MMProxy()
deps: Any = DepsProxy()

__all__ = ["mm", "deps"]
