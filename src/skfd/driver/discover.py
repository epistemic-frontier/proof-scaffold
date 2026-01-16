# skfd/driver/discover.py
from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from .types import PackageModule


def load_build_module(path: Path) -> PackageModule:
    """Load a build.py file as a Python module."""
    module_name = f"skfd_build_{path.parent.name}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load build module from {path}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    return cast(PackageModule, module)


def find_packages(root: Path) -> Iterator[tuple[str, Path, PackageModule]]:
    """
    Scan root directory for subdirectories containing build.py.
    
    Yields:
        (package_name, package_dir, build_module)
    """
    if not root.is_dir():
        return

    for item in root.iterdir():
        if item.is_dir():
            build_file = item / "build.py"
            if build_file.exists():
                try:
                    module = load_build_module(build_file)
                    yield item.name, item, module
                except Exception as e:
                    print(f"Warning: Failed to load build module for {item.name}: {e}")
