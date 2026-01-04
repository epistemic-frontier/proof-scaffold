from __future__ import annotations

from ..ir_lir import ConstDecl, FloatingHyp, Theorem, VarDecl
from ..origin import OriginRecord, OriginTable
from ..symbols import SymbolInterner
from ..unit import ProofUnitIR


def build_sanity_ir() -> tuple[OriginTable, SymbolInterner, list[ProofUnitIR]]:
    ot = OriginTable()
    origin_ref = ot.intern(OriginRecord(module_id="sanity", file="<sanity>", line=1))
    interner = SymbolInterner()

    c_turnstile = interner.intern(
        origin_module_id="sanity",
        local_name="|-",
        kind="Const",
        origin_ref=origin_ref,
    )
    v_ph = interner.intern(
        origin_module_id="sanity",
        local_name="ph",
        kind="Var",
        origin_ref=origin_ref,
    )
    l_wph = interner.intern(
        origin_module_id="sanity",
        local_name="wph",
        kind="Label",
        origin_ref=origin_ref,
    )
    l_th1 = interner.intern(
        origin_module_id="sanity",
        local_name="th1",
        kind="Label",
        origin_ref=origin_ref,
    )

    stmts: list[object] = [
        ConstDecl(stmt_id=0, origin_ref=origin_ref, tokens=[c_turnstile]),
        VarDecl(stmt_id=1, origin_ref=origin_ref, tokens=[v_ph]),
        FloatingHyp(
            stmt_id=2,
            origin_ref=origin_ref,
            label=l_wph,
            typecode=c_turnstile,
            var=v_ph,
        ),
        # Theorem: |- ph, proof is just wph
        Theorem(
            stmt_id=3,
            origin_ref=origin_ref,
            label=l_th1,
            expr=[c_turnstile, v_ph],
            proof=[l_wph],
        ),
    ]
    unit = ProofUnitIR(
        unit_id="sanity:unit0",
        origin_ref=origin_ref,
        origin_module_id="sanity",
        lir_stmts=stmts,  # type: ignore[arg-type]
        exports=[l_th1],
    )
    return ot, interner, [unit]
