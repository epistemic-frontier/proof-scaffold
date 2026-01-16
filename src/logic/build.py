# src/logic/build.py
from typing import Any
from skfd.builder import MMBuilder

def manifest() -> dict[str, Any]:
    return {"deps": ["prelude"]}

def build(mm: MMBuilder, **deps: Any) -> Any:
    # Verify dependency injection
    prelude_export = deps.get("prelude")
    if prelude_export != {"exported_symbols": "PRELUDE_OK"}:
        raise RuntimeError(f"Dependency injection failed. Got: {prelude_export}")

    mm.c("logic_const")
    return {}
