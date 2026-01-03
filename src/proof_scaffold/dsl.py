# proof_scaffold/dsl.py — compatibility re-export layer
from __future__ import annotations

# Keep external import path stable:
# from proof_scaffold.dsl import MMBuilder, expr, MMDSLError
# Now re-exported from the refactored subpackage (see projects/m_1p2_refactor_2.md)
from .dsl.builder import MMBuilder
from .dsl.errors import MMDSLError
from .dsl.types import expr

__all__ = [
    "MMBuilder",
    "MMDSLError",
    "expr",
]
