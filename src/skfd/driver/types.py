# skfd/driver/types.py
from __future__ import annotations

from typing import Any, Protocol, TypedDict

from skfd.builder import MMBuilder


class ModuleInterface(Protocol):
    """
    Interface for a built module artifact.
    
    This is what is returned by a package's build process and potentially
    injected into downstream packages.
    
    Currently, it's a placeholder for whatever the package exports (e.g. SymbolTable).
    """
    pass


class Manifest(TypedDict):
    """
    Return type for the manifest() hook in build.py.
    """
    deps: list[str]  # List of package names this package depends on


class PackageModule(Protocol):
    """Protocol for the loaded build.py module."""
    
    def manifest(self) -> Manifest:
        ...

    def build(self, mm: MMBuilder, **deps: ModuleInterface) -> ModuleInterface | None:
        ...
