from __future__ import annotations

from ..context import LinkContext
from ..diag_helpers import raise_link_error


def _check_origin(obj_name: str, origin, *, unit_id: str | None, chain_prefix: tuple[str, ...]) -> None:
    if origin is None:
        # In Stage 0.5 we fail fast on missing origin
        raise_link_error(
            "E_MISSING_ORIGIN",
            f"missing origin on {obj_name}",
            primary=None,
            chain=chain_prefix + ((f"unit={unit_id}",) if unit_id else ()),
            details={"object": obj_name, "unit": unit_id},
        )


def run(ctx: LinkContext) -> None:
    """Stage 0.5: Origin sealing.

    Enforce that ProofUnitIR and every LIR statement carry a non-null origin.
    Any violation fails fast with a deterministic diagnostic.
    """
    for u in ctx.units:
        _check_origin("ProofUnitIR", getattr(u, "origin", None), unit_id=getattr(u, "unit_id", None), chain_prefix=("Stage0.5",))
        for st in getattr(u, "lir", []) or []:
            # Use class name in message for clarity
            obj_name = type(st).__name__
            _check_origin(obj_name, getattr(st, "origin", None), unit_id=getattr(u, "unit_id", None), chain_prefix=("Stage0.5",))
    return
