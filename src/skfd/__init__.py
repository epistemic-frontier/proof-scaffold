# skfd/__init__.py
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("proof-scaffold")
except PackageNotFoundError:
    __version__ = "0.0.1"

__all__ = ["__version__"]
