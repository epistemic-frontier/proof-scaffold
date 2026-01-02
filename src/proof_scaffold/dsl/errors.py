# proof_scaffold/dsl/errors.py
from __future__ import annotations


class MMDSLError(ValueError):
    """Raised when the DSL detects an invalid Metamath construction."""
