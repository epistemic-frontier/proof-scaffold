from __future__ import annotations

from ..context import LinkContext


def run(ctx: LinkContext) -> None:
    """Stage 0.5: Origin sealing.

    Placeholder in M1.2: no strict checks yet to remain backward-compatible with existing tests.
    """
    # Future: validate that required origins exist and raise E_MISSING_ORIGIN via diag helpers.
    return
