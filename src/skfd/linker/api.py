from __future__ import annotations

from dataclasses import dataclass

from skfd.core.context import Context
from skfd.core.diag import Diagnostic, LinkerDiagError
from .emit.emit_mm import emit_mm
from skfd.core.origin import OriginTable
from .passes.stage1_resolve import run as stage1_run
from skfd.core.symbols import SymbolInterner
from skfd.core.unit import ProofUnitIR


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

        mm_text = emit_mm(symtab=ctx.symtab, units=units1)
        return LinkResult(mm_text=mm_text, ctx=ctx)
