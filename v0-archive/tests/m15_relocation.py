from __future__ import annotations

import re

import pytest

from proof_scaffold.dsl import MMBuilder
from proof_scaffold.linker.context import LinkContext
from proof_scaffold.linker.passes import stage5_scope, stage7_emit, stage1_collect, stage4_deps, stage6_reloc


def _link_mm(*units) -> tuple[LinkContext, str]:
    ctx = LinkContext(units=list(units))
    stage1_collect.run(ctx)
    stage4_deps.run(ctx)
    stage5_scope.run(ctx)
    stage6_reloc.run(ctx)
    mm = stage7_emit.run(ctx)
    return ctx, mm


def test_sanity_m15_emitted_stream_is_deterministic() -> None:
    a = MMBuilder()
    a.c("|-", "wff")
    a.v("ph")
    a.f("wph", "wff", "ph")
    with a.block():
        a.a("ax1", "|-", ("ph",))
        a.p("th1", "|-", ("ph",), "ax1")

    u = a.to_proof_unit("u.A")
    ctx1, mm1 = _link_mm(u)
    ctx2, mm2 = _link_mm(u)
    assert mm1 == mm2
    # NOTE: LinkContext is dynamically extended; use type: ignore for tests.
    assert ctx1.relocation is not None and ctx2.relocation is not None  # type: ignore[attr-defined]
    assert ctx1.relocation.plan_hash == ctx2.relocation.plan_hash  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "bad",
    ["$c", "$v", "$d", "$f", "$e", "$a", "$p", "$=", "$.", "$(", "$)", "$[", "$]", "${", "$}"],
)
def test_adv_m15_reloc_rejects_reserved_or_invalid_tokens(bad: str) -> None:
    # Put a reserved token into symtab as a symbol name; relocation must reject.
    a = MMBuilder()
    a.c(bad)
    u = a.to_proof_unit("u.A")
    ctx = LinkContext(units=[u])
    stage1_collect.run(ctx)
    stage4_deps.run(ctx)
    stage5_scope.run(ctx)
    with pytest.raises(Exception) as ei:
        stage6_reloc.run(ctx)
    assert "E_RELOC_INVALID_TOKEN_FORM" in str(ei.value)


def test_adv_m15_unmapped_symbol_is_error_with_original_token_hint() -> None:
    a = MMBuilder()
    a.c("|-", "wff")
    a.v("ph")
    a.f("wph", "wff", "ph")
    with a.block():
        a.a("ax1", "|-", ("ph",))
        a.p("th1", "|-", ("ph",), "ax1")

    u = a.to_proof_unit("u.A")
    ctx = LinkContext(units=[u])
    stage1_collect.run(ctx)
    stage4_deps.run(ctx)
    stage5_scope.run(ctx)
    stage6_reloc.run(ctx)
    assert ctx.relocation is not None  # type: ignore[attr-defined]

    # Simulate a bug: delete a mapping.
    # Note: under Route B the relocation map is global, but this unit may not
    # reference every tok_id in the symtab. If we delete an unused mapping,
    # Stage7 won't notice. So we choose a tok_id that we know is referenced.
    info = (ctx.ordered_infos or ctx.infos)[0]
    used_ids: set[int] = set()
    for st in info.stmts:
        if hasattr(st, "symbols"):
            used_ids.update(st.symbols)
        if hasattr(st, "typecode"):
            used_ids.add(st.typecode)
        if hasattr(st, "expr"):
            used_ids.update(st.expr)
        if hasattr(st, "var"):
            used_ids.add(st.var)

    some_id = next(iter(sorted(used_ids)))
    hint = info.symtab[some_id]
    ctx.relocation_name_of.pop(some_id)  # type: ignore[attr-defined]

    with pytest.raises(Exception) as ei:
        stage7_emit.run(ctx)
    s = str(ei.value)
    assert "E_RELOC_UNMAPPED_SYMBOL" in s
    assert hint in s or "hint_original_token" in s


def test_adv_m15_duplicate_stable_key_does_not_loop() -> None:
    # Force two different ids to have identical local_name and be in same unit.
    # We do this by directly mutating symtab to duplicate a name.
    a = MMBuilder()
    a.c("|-", "wff")
    a.v("ph")
    a.f("wph", "wff", "ph")
    pu = a.to_proof_unit("u.A")
    # Duplicate: set symtab[0] and symtab[1] to same string.
    if len(pu.symtab) < 2:
        pytest.skip("symtab too small")
    pu.symtab = (pu.symtab[0], pu.symtab[0]) + pu.symtab[2:]

    ctx = LinkContext(units=[pu])
    stage1_collect.run(ctx)
    stage4_deps.run(ctx)
    stage5_scope.run(ctx)
    stage6_reloc.run(ctx)
    assert ctx.relocation is not None  # type: ignore[attr-defined]
    # The first two ids must map to distinct emitted names (injective)
    assert ctx.relocation_name_of[0] != ctx.relocation_name_of[1]  # type: ignore[attr-defined]
    # And collision records should include at least one entry
    assert ctx.relocation.collisions  # type: ignore[attr-defined]


def test_struct_m15_all_token_positions_go_through_name_of() -> None:
    a = MMBuilder()
    a.c("|-", "wff")
    a.v("ph")
    a.f("wph", "wff", "ph")
    with a.block():
        a.a("ax1", "|-", ("ph",))
        a.p("th1", "|-", ("ph",), "ax1")

    ctx, mm = _link_mm(a.to_proof_unit("u.A"))
    assert ctx.relocation is not None  # type: ignore[attr-defined]
    # Ensure no raw local tokens appear as whole tokens in output.
    for raw in ["|-", "wff", "ph", "wph", "ax1", "th1"]:
        assert not re.search(rf"(^|\s){re.escape(raw)}(\s|$)", mm)
