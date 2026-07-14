# skfd/linker/api.py
from __future__ import annotations

from dataclasses import dataclass

from skfd.core.context import Context
from skfd.core.diag import Diagnostic, LinkerDiagError
from skfd.core.origin import OriginTable
from skfd.core.source_map import SourceMap
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR

from .emit.emit_mm import emit_mm
from .passes.stage1_resolve import run as stage1_run
from .passes.stage2_contracts import run as stage2_extract
from .passes.stage3_disjoint import run as stage3_enrich
from .passes.stage4_topo_sort import run as stage4_topo_sort
from .passes.stage5_scope import run as stage5_planning
from .passes.stage6_relocation import run as stage6_relocate


@dataclass(frozen=True)
class LinkResult:
    mm_text: str
    source_map: SourceMap
    ctx: Context


class LinkerV1:
    @staticmethod
    def link(
        *,
        units: list[ProofUnitIR],
        origin_table: OriginTable,
        interner: SymbolInterner,
        conformance_level: int = 0,
    ) -> LinkResult:
        # Stage1: lint/resolution baseline (bootstrap assumes Stage0 already interned)
        ctx = Context(
            origin_table=origin_table, interner=interner, symtab=interner.symbol_table()
        )
        try:
            units1 = stage1_run(
                ctx=ctx, units=units, conformance_level=conformance_level
            )
        except LinkerDiagError:
            raise
        except Exception as e:  # wrap as diagnostic
            raise LinkerDiagError(
                Diagnostic(
                    error_code="E_INTERNAL_INVARIANT",
                    message="unexpected internal error",
                    primary_origin_ref=0,
                    details={"exc": repr(e)},
                )
            ) from e

        # Extract theorem references first so units can be put in their final
        # order. Contract extraction is then repeated over that order because
        # foundation-owned `$f/$e` hypotheses are ambient for downstream units.
        dependency_index = stage2_extract(units1, ctx.symtab)
        units4 = stage4_topo_sort(units1, dependency_index)

        # Stage 2: final contract extraction in emitted scope order.
        contracts = stage2_extract(units4, ctx.symtab)

        # Stage 3: mandatory distinct-variable contracts.
        contracts = stage3_enrich(units4, ctx.symtab, contracts)

        # Stage 5: Scope Planning (LinearPlan)
        plan = stage5_planning(units4, ctx.symtab)

        # Stage 6: Relocation
        reloc_table = stage6_relocate(ctx.symtab)

        mm_text, source_map = emit_mm(
            symtab=ctx.symtab, plan=plan, reloc_table=reloc_table
        )
        return LinkResult(mm_text=mm_text, source_map=source_map, ctx=ctx)
