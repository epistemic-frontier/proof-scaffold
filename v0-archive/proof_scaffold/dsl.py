# scaffold/dsl.py — compatibility re-export layer
from __future__ import annotations

# Keep external import path stable:
# from scaffold.dsl import MMBuilder, expr, MMDSLError
# Now re-exported from the refactored subpackage (see projects/m_1p2_refactor_2.md)
from proof_scaffold.dsl.builder import MMBuilder
from proof_scaffold.dsl.errors import MMDSLError
from proof_scaffold.dsl.types import expr

__all__ = [
    "MMBuilder",
    "MMDSLError",
    "expr",
]
