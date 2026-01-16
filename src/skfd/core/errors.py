# skfd/core/errors.py
# src/skfd/builder/errors.py
from __future__ import annotations


class MMError(Exception):
    """Base exception for Metamath DSL errors."""


class MMDSLError(MMError):
    """Raised when the DSL usage is invalid (e.g. unknown token)."""
