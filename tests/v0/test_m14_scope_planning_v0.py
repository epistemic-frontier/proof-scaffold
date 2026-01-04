from __future__ import annotations

import json
from pathlib import Path

import pytest

from proof_scaffold.dsl import MMBuilder
from proof_scaffold.ir import ConstDecl, Origin, ProofUnitIR, VarDecl
from proof_scaffold.linker.errors import LinkerDiagError
from proof_scaffold.linker_v0 import LinkerV0, link_v0
from tests._sanity_utils import verify_expect_ok


def _stable_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _write(tmp_path: Path, mm_src: str) -> Path:
    p = tmp_path / "linked_m14.mm"
    p.write_text(mm_src, encoding="utf-8")
    return p


@pytest.mark.sanity
def test_sanity_m14_two_unit_scoped_emission_verifies(tmp_path: Path) -> None:
    """A0: two units A->B, each wrapped in a fresh ${...$}, verifier accepts."""
    # Unit A exports ax-mp
    a = MMBuilder()
    a.c("wff", "(", ")", "->")
    a.v("ph", "ps")
    a.f("wph", "wff", "ph")
    a.f("wps", "wff", "ps")
    with a.block():
        a.e("h1r", "wff", ("ph",))
        a.e("h2r", "wff", ("(", "ph", "->", "ps", ")"))
        a.a("ax-mp", "wff", ("ps",))
    ua = a.to_proof_unit("m14.modus")

    # Unit B uses ax-mp
    b = MMBuilder()
    b.c("wff", "(", ")", "->")
    b.v("ph", "ps")
    b.f("wph", "wff", "ph")
    b.f("wps", "wff", "ps")
    from proof_scaffold.theorem import Theorem
    ax_mp = Theorem(fqname="m14.modus.ax_mp", module_id="m14.modus", name="ax_mp", label="ax-mp")
    with b.block():
        b.e("h1", "wff", ("ph",))
        b.e("h2", "wff", ("(", "ph", "->", "ps", ")"))
        b.p("th", "wff", ("ps",), proof=["wph", "wps", "h1", "h2", ax_mp])
    ub = b.to_proof_unit("m14.user")

    src = LinkerV0().link([ua, ub])
    verify_expect_ok(_write(tmp_path, src))


def test_sanity_m14_frame_boundaries_present() -> None:
    """A1: each unit => exactly one frame (outer ${/$}) in plan."""
    m = MMBuilder()
    m.c("wff")
    m.v("ph")
    m.f("wph", "wff", "ph")
    with m.block():
        m.a("ax", "wff", ("ph",))
    u1 = m.to_proof_unit("m14.u1")

    m2 = MMBuilder()
    m2.c("wff")
    m2.v("ph")
    m2.f("wph", "wff", "ph")
    with m2.block():
        m2.a("ax", "wff", ("ph",))
    u2 = m2.to_proof_unit("m14.u2")

    ctx, _mm = link_v0([u1, u2], return_context=True)
    assert ctx.linear_plan is not None
    assert [f.unit_id for f in ctx.linear_plan.frames] == [i.unit_id for i in ctx.ordered_infos]
    assert all(any(fs.synthetic_tag == "linker:stage5:ScopeEnter" for fs in f.stmts) for f in ctx.linear_plan.frames)
    assert all(any(fs.synthetic_tag == "linker:stage5:ScopeExit" for fs in f.stmts) for f in ctx.linear_plan.frames)


@pytest.mark.golden
def test_golden_m14_linear_plan_snapshot_byte_identical() -> None:
    """B1: plan snapshot determinism (frame_id/unit_id/context_hash + synthetic tags)."""
    m = MMBuilder()
    m.c("wff")
    m.v("ph")
    m.f("wph", "wff", "ph")
    with m.block():
        m.a("ax", "wff", ("ph",))
    u = m.to_proof_unit("m14.snap")

    ctx1, _mm1 = link_v0([u], return_context=True)
    ctx2, _mm2 = link_v0([u], return_context=True)
    assert ctx1.linear_plan is not None and ctx2.linear_plan is not None

    def snap(ctx) -> dict[str, object]:
        lp = ctx.linear_plan
        assert lp is not None
        return {
            "frames": [
                {
                    "frame_id": f.frame_id,
                    "unit_id": f.unit_id,
                    "context_hash": f.context_hash,
                    "synthetic_tags": [fs.synthetic_tag for fs in f.stmts],
                }
                for f in lp.frames
            ]
        }

    assert _stable_json(snap(ctx1)) == _stable_json(snap(ctx2))


def test_golden_m14_context_hash_stable() -> None:
    """B2: context_hash stable across runs for same unit id."""
    m = MMBuilder()
    m.c("wff")
    m.v("ph")
    m.f("wph", "wff", "ph")
    with m.block():
        m.a("ax", "wff", ("ph",))
    u = m.to_proof_unit("m14.hash")
    ctx1, _ = link_v0([u], return_context=True)
    ctx2, _ = link_v0([u], return_context=True)
    assert ctx1.linear_plan is not None and ctx2.linear_plan is not None
    assert ctx1.linear_plan.frames[0].context_hash == ctx2.linear_plan.frames[0].context_hash


def test_adv_m14_unit_internal_scope_imbalance_rejected() -> None:
    """C1: unit contains unmatched ${/$} after filtering => E_UNIT_SCOPE_IMBALANCE."""
    # Create a unit with an extra ScopeEnter inside.
    u = ProofUnitIR(
        unit_id="m14.bad.scope",
        lir=[],
        origin=Origin(file="m14_bad_scope.py", line=0),
        symtab=("wff", "ph"),
    )
    from proof_scaffold.ir import ScopeEnter

    u.lir.append(ConstDecl((0,), origin=Origin(file="m14_bad_scope.py", line=1)))
    u.lir.append(VarDecl((1,), origin=Origin(file="m14_bad_scope.py", line=2)))
    u.lir.append(ScopeEnter(origin=Origin(file="m14_bad_scope.py", line=3)))
    u.lir.append(ScopeEnter(origin=Origin(file="m14_bad_scope.py", line=4)))

    with pytest.raises(LinkerDiagError) as ei:
        LinkerV0().link([u])
    assert ei.value.diag.error_code in ("E_SCOPE_IMBALANCE", "E_UNIT_SCOPE_IMBALANCE")


def test_adv_m14_export_order_invalid_is_error() -> None:
    """C2: decl ($f) after export ($a/$p) => E_EXPORT_ORDER_INVALID."""
    from proof_scaffold.ir import Axiom, FloatingHyp, ScopeEnter, ScopeExit

    u = ProofUnitIR(
        unit_id="m14.bad.order",
        lir=[],
        origin=Origin(file="m14_bad_order.py", line=0),
        symtab=("wff", "ph"),
    )
    u.lir.extend(
        [
            ConstDecl((0,), origin=Origin(file="m14_bad_order.py", line=1)),
            VarDecl((1,), origin=Origin(file="m14_bad_order.py", line=2)),
            ScopeEnter(origin=Origin(file="m14_bad_order.py", line=3)),
            Axiom(label="ax", typecode=0, expr=(1,), origin=Origin(file="m14_bad_order.py", line=4)),
            FloatingHyp(label="wph", typecode=0, var=1, origin=Origin(file="m14_bad_order.py", line=5)),
            ScopeExit(origin=Origin(file="m14_bad_order.py", line=6)),
        ]
    )
    with pytest.raises(LinkerDiagError) as ei:
        LinkerV0().link([u])

    # Keep this assertion strict (the implementation should not change the code),
    # but avoid mypy "non-overlapping equality" noise when the error_code type is
    # narrowed elsewhere.
    assert str(ei.value.diag.error_code) == "E_EXPORT_ORDER_INVALID"


def test_adv_m14_local_cv_decl_dropped() -> None:
    """C3: ConstDecl/VarDecl inside unit are dropped from frame body."""
    m = MMBuilder()
    m.c("wff")
    m.v("ph")
    m.f("wph", "wff", "ph")
    with m.block():
        m.a("ax", "wff", ("ph",))
    u = m.to_proof_unit("m14.drop")

    ctx, _mm = link_v0([u], return_context=True)
    assert ctx.linear_plan is not None
    frame = ctx.linear_plan.frames[0]
    assert all(not isinstance(fs.stmt, (ConstDecl, VarDecl)) for fs in frame.stmts)
    assert any(n.get("code") == "N_DROPPED_LOCAL_CV_DECL" for n in ctx.lint_notes)


def test_struct_m14_no_cv_inside_frames() -> None:
    """D3: frame bodies contain no $c/$v stmts."""
    m = MMBuilder()
    m.c("wff")
    m.v("ph")
    m.f("wph", "wff", "ph")
    with m.block():
        m.a("ax", "wff", ("ph",))
    u = m.to_proof_unit("m14.no_cv")

    ctx, _mm = link_v0([u], return_context=True)
    assert ctx.linear_plan is not None
    for f in ctx.linear_plan.frames:
        assert all(not isinstance(fs.stmt, (ConstDecl, VarDecl)) for fs in f.stmts)


def test_struct_m14_preserves_valid_internal_nesting() -> None:
    """D4: ScopePlanner preserves valid internal scope blocks.

    Input (unit stmts after $c/$v dropping):
      [ ${, helper, $}, main ]
    Output (frame stmts):
      [ Outer ${ (synthetic), Inner ${, helper, Inner $}, main, Outer $} (synthetic) ]
    """

    from proof_scaffold.ir import Axiom, ScopeEnter, ScopeExit

    u = ProofUnitIR(
        unit_id="m14.nested",
        lir=[],
        origin=Origin(file="m14_nested.py", line=0),
        symtab=("wff", "ph"),
        # NOTE: `exports` is a list in ProofUnitIR; we export only "main".
        exports=["main"],
    )

    # 1. VarDecl (will be dropped from frame body by Stage5)
    u.lir.append(VarDecl((1,), origin=Origin(file="m14_nested.py", line=1)))

    # 2. Internal nested scope
    u.lir.append(ScopeEnter(origin=Origin(file="m14_nested.py", line=2)))
    u.lir.append(Axiom(label="helper", typecode=0, expr=(1,), origin=Origin(file="m14_nested.py", line=3)))
    u.lir.append(ScopeExit(origin=Origin(file="m14_nested.py", line=4)))

    # 3. Export
    u.lir.append(Axiom(label="main", typecode=0, expr=(1,), origin=Origin(file="m14_nested.py", line=5)))

    ctx, _mm = link_v0([u], return_context=True)
    assert ctx.linear_plan is not None
    frame = ctx.linear_plan.frames[0]

    stmts = [fs.stmt for fs in frame.stmts]
    assert isinstance(stmts[0], ScopeEnter)  # outer synthetic
    assert isinstance(stmts[1], ScopeEnter)  # inner original
    assert isinstance(stmts[2], Axiom) and stmts[2].label == "helper"
    assert isinstance(stmts[3], ScopeExit)   # inner original
    assert isinstance(stmts[4], Axiom) and stmts[4].label == "main"
    assert isinstance(stmts[5], ScopeExit)   # outer synthetic
