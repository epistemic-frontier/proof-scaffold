# verify_driver_infra.py
import os
import sys
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, os.path.abspath("src"))

from skfd.driver.discover import find_packages
from skfd.driver.graph import sort_packages


def main() -> None:
    root = Path("src")
    print(f"Scanning {root.absolute()}...")

    packages = {}
    modules = {}

    # 1. Discovery
    for pkg_name, pkg_path, module in find_packages(root):
        print(f"Found package: {pkg_name} at {pkg_path}")
        try:
            m = module.manifest()
            packages[pkg_name] = m["deps"]
            modules[pkg_name] = module
        except Exception as e:
            print(f"Error reading manifest for {pkg_name}: {e}")

    print(f"\nDependency Map: {packages}")

    # 2. Sort
    try:
        order = sort_packages(packages)
        print(f"\nBuild Order: {order}")

        expected = ["prelude", "logic"]
        # Filter order to only include expected (there might be other folders)
        filtered_order = [p for p in order if p in expected]

        if filtered_order == expected:
            print("SUCCESS: Order matches expected [prelude -> logic]")
        else:
            print(f"FAILURE: Order mismatch. Expected {expected}, got {filtered_order}")
            sys.exit(1)

    except Exception as e:
        print(f"Sort failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
