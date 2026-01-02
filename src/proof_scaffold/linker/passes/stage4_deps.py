from __future__ import annotations

from ...ir import Theorem
from ..context import LinkContext
from ..diag_helpers import raise_link_error
from ..policy import stable_sorted


def run(ctx: LinkContext) -> None:
    infos = ctx.infos
    label_owners = ctx.label_owners
    label_kind_by_unit = ctx.label_kind_by_unit

    deps: dict[str, set[str]] = {i.unit_id: set() for i in infos}
    info_by_id = {i.unit_id: i for i in infos}

    for i in infos:
        for st in i.stmts:
            if isinstance(st, Theorem):
                for tk in st.proof_tokens:
                    step = tk.name
                    # skip local labels
                    if (i.unit_id, step) in label_kind_by_unit:
                        continue
                    owners = label_owners.get(step, set())
                    if not owners:
                        # unresolved should have been caught in Stage1_lint; keep defensive LinkerError?
                        # We use a generic error code via raise_link_error for consistency.
                        raise_link_error(
                            "E_UNRESOLVED_LABEL",
                            f"unresolved exported label: {step}",
                            primary=st.origin,
                            chain=("Stage4", f"unit={i.unit_id}"),
                            details={"label": step},
                        )
                    for owner in owners:
                        kind = label_kind_by_unit.get((owner, step))
                        if kind in ("$a", "$p") and owner != i.unit_id:
                            own_info = info_by_id.get(owner)
                            if own_info is None:
                                continue
                            ex = own_info.exports
                            if ex is None or step in ex:
                                deps[i.unit_id].add(owner)

    temp_mark: set[str] = set()
    perm_mark: set[str] = set()
    order: list[str] = []
    cycle_stack: list[str] = []

    def visit(n: str) -> None:
        if n in perm_mark:
            return
        if n in temp_mark:
            cycle_stack.append(n)
            path = cycle_stack + [n]
            related = tuple(info_by_id[uid].unit_origin for uid in path if uid != n)
            raise_link_error(
                "E_DEP_CYCLE",
                "dependency cycle detected",
                primary=info_by_id[n].unit_origin,
                related=related,
                chain=("Stage4", f"unit={n}"),
                details={"cycle": path},
            )
        temp_mark.add(n)
        cycle_stack.append(n)
        for m in stable_sorted(deps[n]):
            visit(m)
        cycle_stack.pop()
        temp_mark.remove(n)
        perm_mark.add(n)
        order.append(n)

    for uid in stable_sorted(deps.keys()):
        if uid not in perm_mark:
            visit(uid)

    ctx.ordered_infos = [info_by_id[u] for u in order]
