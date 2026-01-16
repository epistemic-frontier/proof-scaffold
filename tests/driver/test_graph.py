# tests/driver/test_graph.py
import pytest
from skfd.driver.graph import sort_packages
from graphlib import CycleError

def test_sort_simple_chain():
    # A -> B -> C
    deps = {
        "A": [],
        "B": ["A"],
        "C": ["B"]
    }
    order = sort_packages(deps)
    assert order == ["A", "B", "C"]

def test_sort_diamond():
    # A -> B, A -> C, B -> D, C -> D
    deps = {
        "A": [],
        "B": ["A"],
        "C": ["A"],
        "D": ["B", "C"]
    }
    order = sort_packages(deps)
    # A must be first, D must be last. B and C can be in any order between.
    assert order[0] == "A"
    assert order[-1] == "D"
    assert set(order[1:3]) == {"B", "C"}

def test_sort_disjoint():
    # A -> B; C
    deps = {
        "A": [],
        "B": ["A"],
        "C": []
    }
    order = sort_packages(deps)
    assert "A" in order
    assert "B" in order
    assert "C" in order
    assert order.index("A") < order.index("B")

def test_sort_cycle():
    # A -> B -> A
    deps = {
        "A": ["B"],
        "B": ["A"]
    }
    with pytest.raises(CycleError):
        sort_packages(deps)
