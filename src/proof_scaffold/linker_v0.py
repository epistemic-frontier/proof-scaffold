# proof_scaffold/linker_v0.py
from __future__ import annotations

from collections.abc import Iterable

from .linker.context import LinkContext
from .linker.errors import LinkerError  # re-export for tests
from .linker.passes import origin_seal as pass_origin_seal
from .linker.passes import stage1_collect as pass_stage1_collect
from .linker.passes import stage1_lint as pass_stage1_lint
from .linker.passes import stage4_deps as pass_stage4_deps
from .linker.passes import stage6_reloc as pass_stage6_reloc
from .linker.passes import stage7_emit as pass_stage7_emit


class LinkerV0:
    """
    M1.2 orchestrator-only LinkerV0:
      - Stage 0.5: origin sealing (placeholder)
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
    def link(self, units: Iterable[object]) -> str:
        unit_list = [u for u in units]  # materialize
        if not unit_list:
            raise LinkerError("no units provided to linker")

        ctx = LinkContext(units=unit_list)  # type: ignore[arg-type]

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

    def build_symbol_table(self, units: Iterable[object]) -> list[tuple[str, str, str, int]]:
        """
        Deterministic global symbol table snapshot for tests.
        Returns list of (origin_id, local_name, kind, ordinal_id).
        """
        unit_list = [u for u in units]
        if not unit_list:
            return []
        ctx = LinkContext(units=unit_list)  # type: ignore[arg-type]
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
