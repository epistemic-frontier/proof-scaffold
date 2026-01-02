from __future__ import annotations

from ...ir import Theorem
from ..context import LinkContext
from ..diag_helpers import raise_link_error


def run(ctx: LinkContext) -> None:
    infos = ctx.infos
    label_owners = ctx.label_owners
    label_kind_by_unit = ctx.label_kind_by_unit
    exports_by_unit = ctx.exports_by_unit

    for info in infos:
        for st in info.stmts:
            if isinstance(st, Theorem):
                for tk in st.proof_tokens:
                    step = tk.name
                    # local label is always OK
                    if (info.unit_id, step) in label_kind_by_unit:
                        continue
                    owners = label_owners.get(step)
                    if not owners:
                        raise_link_error(
                            "E_UNRESOLVED_LABEL",
                            f"unresolved label in proof: '{step}' (in unit {info.unit_id})",
                            primary=st.origin,
                            chain=("Stage1", f"unit={info.unit_id}", f"stmt={st.label}"),
                            details={"label": step},
                        )
                    # leakage via $f/$e
                    leak_from = [own for own in owners if label_kind_by_unit.get((own, step)) in ("$f", "$e")]
                    if leak_from:
                        # pick deterministic offender
                        offender = sorted(leak_from)[0]
                        off_o = next((i for i in infos if i.unit_id == offender), None)
                        off_origin = off_o.label_origin.get(step) if off_o else None
                        raise_link_error(
                            "E_CROSS_UNIT_HYP_LEAKAGE",
                            f"cross-unit hypothesis leakage: '{step}'",
                            primary=st.origin,
                            related=(off_origin,),
                            chain=("Stage1", f"unit={info.unit_id}", f"stmt={st.label}"),
                            details={"offender_unit": offender, "label": step},
                        )
                    # non-exported $a/$p usage
                    ap_owners = [own for own in owners if label_kind_by_unit.get((own, step)) in ("$a", "$p")]
                    if ap_owners:
                        exported_ok = False
                        for own in ap_owners:
                            ex = exports_by_unit.get(own)
                            if ex is None or step in (ex or set()):
                                exported_ok = True
                                break
                        if not exported_ok:
                            owner = sorted(ap_owners)[0]
                            own_info = next((i for i in infos if i.unit_id == owner), None)
                            def_origin = own_info.label_origin.get(step) if own_info else None
                            raise_link_error(
                                "E_NON_EXPORTED_LABEL_REF",
                                f"non-exported label reference: '{step}'",
                                primary=st.origin,
                                related=(def_origin,),
                                chain=("Stage1", f"unit={info.unit_id}", f"stmt={st.label}"),
                                details={"owner_unit": owner, "label": step},
                            )
