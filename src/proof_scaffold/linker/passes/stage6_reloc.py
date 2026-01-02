from __future__ import annotations

from ..context import LinkContext
from ..policy import mangle_suffix, stable_sorted


def run(ctx: LinkContext) -> None:
    relabel: dict[tuple[str, str], str] = {}
    for info in ctx.ordered_infos or ctx.infos:
        suffix = mangle_suffix(info.unit_id)
        for name, _kind in stable_sorted(info.labels.items(), key=lambda kv: kv[0]):
            relabel[(info.unit_id, name)] = f"{name}__{suffix}"
    ctx.relabel = relabel
