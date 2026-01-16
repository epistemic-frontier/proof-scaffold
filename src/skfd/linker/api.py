# skfd/linker/api.py
from __future__ import annotations

from dataclasses import dataclass

from skfd.core.context import Context
from skfd.core.diag import Diagnostic, LinkerDiagError
from skfd.core.origin import OriginTable
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR

from .emit.emit_mm import emit_mm
from .passes.stage1_resolve import run as stage1_run


from .passes.stage6_relocation import run as stage6_relocate
from .passes.stage4_topo_sort import run as stage4_topo_sort
from .passes.stage5_scope import run as stage5_planning
from .passes.stage2_contracts import run as stage2_extract
from .passes.stage3_disjoint import run as stage3_enrich

@dataclass(frozen=True)
class LinkResult:
    mm_text: str
    ctx: Context


class LinkerV1:
    @staticmethod
    def link(
        *, units: list[ProofUnitIR], origin_table: OriginTable, interner: SymbolInterner
    ) -> LinkResult:
        # Stage1: lint/resolution baseline (bootstrap assumes Stage0 already interned)
        ctx = Context(
            origin_table=origin_table, interner=interner, symtab=interner.symbol_table()
        )
        try:
            units1 = stage1_run(ctx=ctx, units=units)
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

        # Stage 2: Contract Extraction
        contracts = stage2_extract(units1, ctx.symtab)
        
        # Stage 3: $d Processing (Mode A: Enrich)
        contracts = stage3_enrich(units1, ctx.symtab, contracts)

        # Stage 4: Dependency closure and topo sort
        units4 = stage4_topo_sort(units1, contracts)

        # Stage 5: Scope Planning (LinearPlan)
        plan = stage5_planning(units4, ctx.symtab)

        # Stage 6: Relocation
        reloc_table = stage6_relocate(ctx.symtab)

        mm_text = emit_mm(symtab=ctx.symtab, plan=plan, reloc_table=reloc_table)
        return LinkResult(mm_text=mm_text, ctx=ctx)
