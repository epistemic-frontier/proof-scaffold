# src/prelude/build.py
from typing import Any

from skfd.builder import MMBuilder


def manifest() -> dict[str, Any]:
    return {"deps": []}

def build(mm: MMBuilder, **deps: Any) -> Any:
    # Declare a constant so we can see it in LIR
    mm.c("prelude_const")
    return {"exported_symbols": "PRELUDE_OK"}
