from __future__ import annotations

from ..context import LinkContext, UnitInfo
from ..diag_helpers import raise_link_error
from ..policy import stable_sorted


def _tok_name(info: UnitInfo, tok: object) -> str:
    if isinstance(tok, int):
        if info.symtab and 0 <= tok < len(info.symtab):
            return str(info.symtab[tok])
        return str(tok)
    name = getattr(tok, "name", None)
    if isinstance(name, str):
        return name
    # Explicitly cast unknowns to str for type-checkers
    return str(tok)


def run(ctx: LinkContext) -> None:
    infos = ctx.infos
    label_owners = ctx.label_owners
    label_kind_by_unit = ctx.label_kind_by_unit

    deps: dict[str, set[str]] = {i.unit_id: set() for i in infos}
    info_by_id = {i.unit_id: i for i in infos}
    # NOTE: In current LinkerV0, deps keys are derived from infos, so `owner`
    # is always in `unit_ids` when it comes from label_owners.
    unit_ids = set(info_by_id.keys())

    for i in infos:
        # Stage1 already computed uses_assertions from resolved proof tokens.
        for step in i.uses_assertions:
            owners = label_owners.get(step, set())
            # If uses_assertions contains a label, it must resolve to an $a/$p label.
            # Otherwise Stage1 logic is inconsistent.
            if not owners:
                prov = i.uses_provenance.get(step)
                raise_link_error(
                    "E_UNRESOLVED_LABEL",
                    f"unresolved exported label: {step}",
                    primary=(prov.ref_origin if prov else i.unit_origin),
                    chain=("Stage4", f"unit={i.unit_id}"),
                    details={"label": step},
                )

            # choose an exported $a/$p owner deterministically
            ap_owners: list[str] = []
            for owner in stable_sorted(owners):
                kind = label_kind_by_unit.get((owner, step))
                if kind not in ("$a", "$p"):
                    continue
                ex = info_by_id[owner].exports
                if ex is None or step in ex:
                    ap_owners.append(owner)

            if not ap_owners:
                # Stage1_lint already rejects non-exported label ref and $f/$e leakage,
                # so reaching here indicates inconsistent state.
                prov = i.uses_provenance.get(step)
                raise_link_error(
                    "E_INTERNAL_INVARIANT",
                    f"uses_assertions contains non-exported or non-assertion label: {step}",
                    primary=(prov.ref_origin if prov else i.unit_origin),
                    chain=("Stage4", f"unit={i.unit_id}"),
                    details={"label": step},
                )

            owner = ap_owners[0]
            # Missing-dep-unit is a v3 requirement, but the current v0-archive pipeline
            # does not have an importable "export index" for off-graph units.
            # Missing labels are handled as E_UNRESOLVED_LABEL in Stage1.
            if owner not in unit_ids:  # pragma: no cover
                prov = i.uses_provenance.get(step)
                raise_link_error(
                    "E_MISSING_DEP_UNIT",
                    f"missing dependency unit: {owner} (needed by {i.unit_id} via {step})",
                    primary=(prov.ref_origin if prov else i.unit_origin),
                    chain=("Stage4", f"unit={i.unit_id}"),
                    details={"user_unit": i.unit_id, "dep_unit": owner, "label": step},
                )

            if owner != i.unit_id:
                deps[i.unit_id].add(owner)

        # COMPAT fallback: if a unit has no computed closure (common in
        # interface-only builds), allow a unit-level dependency hint.
        if ctx.compat and not i.uses_assertions:
            hint = next((u.dependencies_hint_unit_ids for u in ctx.units if u.unit_id == i.unit_id), None)
            if hint is None:
                raise_link_error(
                    "E_DEP_HINT_REQUIRED",
                    "dependencies_hint_unit_ids required in COMPAT when no proof closure is available",
                    primary=i.unit_origin,
                    chain=("Stage4", f"unit={i.unit_id}"),
                    details={"unit": i.unit_id},
                )
            for dep_uid in stable_sorted(hint):
                if dep_uid not in unit_ids:
                    raise_link_error(
                        "E_DEP_HINT_INVALID",
                        f"invalid dependency hint unit: {dep_uid}",
                        primary=i.unit_origin,
                        chain=("Stage4", f"unit={i.unit_id}"),
                        details={"unit": i.unit_id, "hint_unit": dep_uid},
                    )
                if dep_uid != i.unit_id:
                    deps[i.unit_id].add(dep_uid)

        # Optional: if both computed deps and hint exist, require exact match
        # in COMPAT mode to avoid ghost dependencies.
        if ctx.compat and i.uses_assertions:
            hint = next((u.dependencies_hint_unit_ids for u in ctx.units if u.unit_id == i.unit_id), None)
            if hint is not None:
                computed = set(deps[i.unit_id])
                hinted = set(hint)
                if computed != hinted:
                    raise_link_error(
                        "E_DEP_HINT_MISMATCH",
                        "dependency hint mismatch with computed closure",
                        primary=i.unit_origin,
                        chain=("Stage4", f"unit={i.unit_id}"),
                        details={
                            "unit": i.unit_id,
                            "computed": stable_sorted(computed),
                            "hint": stable_sorted(hinted),
                        },
                    )

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
