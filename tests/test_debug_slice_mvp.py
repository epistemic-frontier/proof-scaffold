from __future__ import annotations

import pytest

from proof_scaffold.debug_slice import slice_from_link_context
from proof_scaffold.dsl import MMBuilder
from proof_scaffold.linker_v0 import link_v0


def test_debug_slice_span_and_window() -> None:
    mm = MMBuilder(strict=True)
    mm.c("|-", "wff")
    mm.v("ph")

    with mm.block():
        mm.f("wph", "wff", "ph")
        mm.a("ax1", "|-", "ph")
        # Trivial proof uses ax1 exactly once.
        mm.p("th1", "|-", "ph", "ax1")

    u = mm.to_proof_unit("U")
    ctx, _mm_text = link_v0([u], return_context=True)

    # The only proof token is 'ax1__<suffix>' in relocated form.
    assert len(ctx.proof_tokens) == 1
    (s, e) = ctx.theorem_to_span[("U", "th1")]
    assert (s, e) == (0, 1)

    # Path A sidecar map should exist and map verifier step 1 -> step_id 1.
    assert ctx.emitted_step_to_step_id[1] == 1

    res = slice_from_link_context(ctx, mm_error_step=1, unit_id="U", theorem_label="th1", window=8)
    assert res.span == (0, 1)
    assert res.window_tokens == tuple(ctx.proof_tokens)


def test_debug_slice_rejects_out_of_range() -> None:
    mm = MMBuilder(strict=True)
    mm.c("|-", "wff")
    mm.v("ph")
    with mm.block():
        mm.f("wph", "wff", "ph")
        mm.a("ax1", "|-", "ph")
        mm.p("th1", "|-", "ph", "ax1")
    u = mm.to_proof_unit("U")
    ctx, _mm_text = link_v0([u], return_context=True)
    with pytest.raises(ValueError):
        slice_from_link_context(ctx, mm_error_step=2, unit_id="U", theorem_label="th1")


def test_debug_slice_step_id_is_stable_within_builder() -> None:
    mm = MMBuilder(strict=True)
    mm.c("|-", "wff")
    mm.v("ph")

    with mm.block():
        mm.f("wph", "wff", "ph")
        mm.a("ax1", "|-", "ph")
        mm.a("ax2", "|-", "ph")
        # two proof tokens => step ids should be [1,2] in order
        mm.p("th1", "|-", "ph", "ax1 ax2")

    u = mm.to_proof_unit("U")
    ctx, _mm_text = link_v0([u], return_context=True)
    assert ctx.emitted_step_to_step_id[1] == 1
    assert ctx.emitted_step_to_step_id[2] == 2
