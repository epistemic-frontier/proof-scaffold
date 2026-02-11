# skfd/driver/discover.py
from __future__ import annotations

import importlib
import importlib.util
import importlib.metadata
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import tomllib

from .types import PackageModule


def load_build_module(path: Path) -> PackageModule:
    """Load a build.py file as a Python module."""
    # 1. Try to import as a standard module (supports relative imports)
    try:
        pkg_name = path.parent.name
        target_mod = f"{pkg_name}.build"
        mod = importlib.import_module(target_mod)
        # Verify it loaded the correct file
        if mod.__file__ and Path(mod.__file__).resolve() == path.resolve():
            return cast(PackageModule, mod)
        else:
             print(f"DEBUG: Path mismatch for {target_mod}: loaded {mod.__file__}, expected {path.resolve()}")
    except ImportError as e:
        # If the error is strictly about finding the module itself, fall back.
        # Otherwise (e.g. syntax error or import error INSIDE the module), re-raise.
        if e.name in {pkg_name, target_mod}:
            pass
        else:
            raise
    except (ValueError, AttributeError) as e:
        print(f"DEBUG: Loading error: {e}")
        pass

    # 2. Fallback: Load as standalone file (no relative imports support)
    module_name = f"skfd_build_{path.parent.name}"
    
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load build module from {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return cast(PackageModule, module)


def load_external_build_module(package_name: str) -> PackageModule | None:
    """Attempt to load a build module from an installed package."""
    candidates: list[str] = []

    def _add(name: str) -> None:
        name = name.strip()
        if not name:
            return
        if name not in candidates:
            candidates.append(name)

    _add(package_name)
    _add(package_name.replace("-", "_"))

    if package_name.startswith("metamath-"):
        suffix = package_name.removeprefix("metamath-")
        _add(suffix)
        _add(suffix.replace("-", "_"))

    def _norm_dist(name: str) -> str:
        return re.sub(r"[-_.]+", "-", name).lower()

    try:
        dist = importlib.metadata.distribution(package_name)
        top_level = dist.read_text("top_level.txt")
        if top_level:
            for line in top_level.splitlines():
                _add(line)
    except importlib.metadata.PackageNotFoundError:
        dist = None

    if dist is None:
        for cand in list(candidates):
            if _norm_dist(cand) == _norm_dist(package_name):
                continue
            try:
                dist = importlib.metadata.distribution(cand)
                top_level = dist.read_text("top_level.txt")
                if top_level:
                    for line in top_level.splitlines():
                        _add(line)
                break
            except importlib.metadata.PackageNotFoundError:
                continue

    for base in candidates:
        try:
            module = importlib.import_module(f"{base}.build")
            return cast(PackageModule, module)
        except ImportError:
            continue

    return None


def get_package_deps(build_path: Path) -> list[str]:
    """
    Determine dependencies for a package.
    Priority:
    1. pyproject.toml [project.dependencies] (Safe & Preferred)
    """
    package_dir = build_path.parent
    
    # 1. Try pyproject.toml
    curr = package_dir
    for _ in range(3):
        p = curr / "pyproject.toml"
        if p.exists():
            try:
                with open(p, "rb") as f:
                    data = tomllib.load(f)
                deps = data.get("project", {}).get("dependencies", [])
                clean_deps = []
                for d in deps:
                    name = d.split(">", 1)[0].split("<", 1)[0].split("=", 1)[0].split(";", 1)[0].strip()
                    if name != "proof-scaffold" and name:
                        clean_deps.append(name)
                return clean_deps
            except Exception as e:
                print(f"Warning: Failed to parse pyproject.toml at {p}: {e}")
        curr = curr.parent

    return []


def get_package_name(build_path: Path) -> str | None:
    """Extract package name from pyproject.toml."""
    curr = build_path.parent
    for _ in range(3):
        p = curr / "pyproject.toml"
        if p.exists():
            try:
                with open(p, "rb") as f:
                    data = tomllib.load(f)
                name = data.get("project", {}).get("name")
                return name if isinstance(name, str) else None
            except Exception:
                pass
        curr = curr.parent
    return None


def find_packages(root: Path) -> Iterator[tuple[str, Path, Path]]:
    """
    Scan root directory for subdirectories containing build.py.
    
    Yields:
        (package_name, package_dir, build_path)
    """
    if not root.is_dir():
        return

    # Recursive scan for build.py
    for build_file in root.glob("**/build.py"):
        if build_file.parent == root:
            continue
        
        # Resolve canonical package name
        real_name = get_package_name(build_file)
        pkg_name = real_name if real_name else build_file.parent.name
        
        yield pkg_name, build_file.parent, build_file
