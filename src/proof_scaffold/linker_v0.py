# proof_scaffold/linker_v0.py
from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from proof_scaffold.ir import ProofUnitIR
from proof_scaffold.linker.context import LinkContext
from proof_scaffold.linker.errors import (  # re-export for tests
    LinkerError,
)
from proof_scaffold.linker.passes import origin_seal as pass_origin_seal
from proof_scaffold.linker.passes import stage1_collect as pass_stage1_collect
from proof_scaffold.linker.passes import stage1_lint as pass_stage1_lint
from proof_scaffold.linker.passes import stage4_deps as pass_stage4_deps
from proof_scaffold.linker.passes import stage6_reloc as pass_stage6_reloc
from proof_scaffold.linker.passes import stage7_emit as pass_stage7_emit


class LinkerV0:
    """
    M1.2 orchestrator-only LinkerV0:
      - Stage 0.5: origin sealing (strict)
      - Stage 1a: collect
      - Stage 1b: lint
      - Stage 4: deps closure + topo order
      - Stage 6: relocation map
      - Stage 7: emission

    All business logic lives in passes/* and shared helpers.
    """

    def __init__(self) -> None:
        pass

    # --------
    # Public API
    # --------
    def link(self, units: Iterable[ProofUnitIR]) -> str:
        unit_list = [u for u in units]  # materialize
        if not unit_list:
            raise LinkerError("no units provided to linker")

        ctx = LinkContext(units=unit_list)

        # Stage 0.5: Origin sealing
        pass_origin_seal.run(ctx)
        # Stage 1: collect + lint
        pass_stage1_collect.run(ctx)
        pass_stage1_lint.run(ctx)
        # Stage 4: deps order
        pass_stage4_deps.run(ctx)
        # Stage 6: relocation
        pass_stage6_reloc.run(ctx)
        # Stage 7: emission
        return pass_stage7_emit.run(ctx)

    def build_symbol_table(self, units: Iterable[ProofUnitIR]) -> list[tuple[str, str, str, int]]:
        """
        Deterministic global symbol table snapshot for tests.
        Returns list of (origin_id, local_name, kind, ordinal_id).
        """
        unit_list = [u for u in units]
        if not unit_list:
            return []
        ctx = LinkContext(units=unit_list)
        pass_stage1_collect.run(ctx)
        rows: list[tuple[str, str, str]] = []
        globals_rows: list[tuple[str, str, str]] = []
        for c in ctx.global_consts:
            globals_rows.append(("<global>", c, "CONST"))
        for v in ctx.global_vars:
            globals_rows.append(("<global>", v, "VAR"))
        globals_rows.sort(key=lambda t: t[1])
        rows.extend(globals_rows)
        for info in sorted(ctx.infos, key=lambda x: x.unit_id):
            for name, kind in sorted(info.labels.items()):
                rows.append((info.unit_id, name, kind))
        return [(o, n, k, idx) for idx, (o, n, k) in enumerate(rows)]


def link_v0(units, *, return_context: bool = False):
    """Convenience wrapper used by tests and debug tooling.

    When return_context=True, returns (LinkContext, mm_text).
    """
    unit_list = [u for u in units]
    if not unit_list:
        raise LinkerError("no units provided to linker")

    # Keep link_v0 permissive for tests/tooling; cast to the canonical type.
    ctx = LinkContext(units=cast(list[ProofUnitIR], unit_list))
    pass_origin_seal.run(ctx)
    pass_stage1_collect.run(ctx)
    pass_stage1_lint.run(ctx)
    pass_stage4_deps.run(ctx)
    pass_stage6_reloc.run(ctx)
    mm = pass_stage7_emit.run(ctx)

    if return_context:
        return ctx, mm
    return mm
