# skfd/driver/graph.py
from __future__ import annotations

from graphlib import TopologicalSorter


def sort_packages(packages: dict[str, list[str]]) -> list[str]:
    """
    Topologically sort packages based on dependencies.
    
    Args:
        packages: dict mapping {package_name: [dependency_names]}
        
    Returns:
        List of package names in build order.
    """
    sorter: TopologicalSorter[str] = TopologicalSorter(packages)
    return list(sorter.static_order())
