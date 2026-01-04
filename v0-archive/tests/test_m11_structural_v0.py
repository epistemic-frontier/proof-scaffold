from __future__ import annotations

import re
from pathlib import Path

from proof_scaffold.dsl import MMBuilder
from proof_scaffold.linker_v0 import LinkerV0

from tests._sanity_utils import verify_expect_ok


def _body_segments(mm_src: str) -> list[list[str]]:
    segs: list[list[str]] = []
    cur: list[str] = []
    in_frame = False
    for ln in mm_src.splitlines():
        if ln.strip() == "${":
            in_frame = True
            cur = []
            continue
        if ln.strip() == "$}":
            if in_frame:
                segs.append(cur)
            in_frame = False
            cur = []
            continue
        if in_frame:
            cur.append(ln)
    return segs


def _contains_token(mm_src: str, token: str) -> bool:
    # match metamath token boundaries
    pat = re.compile(rf"(^|\s){re.escape(token)}(\s|$)")
    return any(pat.search(ln) for ln in mm_src.splitlines())


# D1. Header hoist only: $c/$v only in header, never in any ${ ... $}


def test_struct_m11_header_hoist_only(tmp_path: Path) -> None:
    mm = MMBuilder()
    mm.c("wff", "(", ")", "->", "|-")
    mm.v("ph", "ps")
    mm.f("wph", "wff", "ph")
    with mm.block():
        mm.a("ax", "|-", ("(", "ph", "->", "ph", ")"))
    u = mm.to_proof_unit("d.u1")

    src = LinkerV0().link([u])

    # Header lines start with $c/$v if present
    assert src.splitlines()[0].startswith("$c ")
    assert "$v " in src.splitlines()[1]

    # Ensure body segments contain no $c/$v lines
    for seg in _body_segments(src):
        for ln in seg:
            assert not ln.strip().startswith("$c ")
            assert not ln.strip().startswith("$v ")

    # sanity: verifier should accept
    p = tmp_path / "linked.mm"
    p.write_text(src, encoding="utf-8")
    verify_expect_ok(p)


# D2. One unit -> one scope frame


def test_struct_m11_one_unit_one_scopeframe() -> None:
    uids = ["d.uA", "d.uB", "d.uC"]
    units = []
    for uid in uids:
        m = MMBuilder()
        m.c("wff")
        m.v("ph")
        m.f("wph", "wff", "ph")
        with m.block():
            m.a("ax", "wff", ("ph",))
        units.append(m.to_proof_unit(uid))

    src = LinkerV0().link(units)

    # number of frames equals number of units
    assert src.count("${") == len(units)
    assert src.count("$}") == len(units)

    # Each unit's relocated suffix should be confined to exactly one frame
    frames = _body_segments(src)
    for uid in uids:
        suffix = uid.replace("/", "_").replace(".", "_")
        hits = [any(f"__{suffix}" in ln for ln in frame) for frame in frames]
        assert sum(1 for h in hits if h) == 1


# D3. Token-level relocation total: no bare local label names remain in output


def test_struct_m11_token_level_relocation_total() -> None:
    # Two units deliberately sharing the same local label names
    a = MMBuilder()
    a.c("wff", "(", ")", "->")
    a.v("ph", "ps")
    a.f("L_f", "wff", "ph")
    with a.block():
        a.e("L_e", "wff", ("ph",))
        a.a("L_a", "wff", ("ps",))
    ua = a.to_proof_unit("d.A")

    b = MMBuilder()
    b.c("wff", "(", ")", "->")
    b.v("ph", "ps")
    b.f("L_f", "wff", "ph")
    with b.block():
        b.e("L_e", "wff", ("ph",))
        # Proof references L_a from A; ensure proof tokens relocation
        from proof_scaffold.theorem import Theorem as Th

        ax_handle = Th(fqname="d.A.ax", module_id="d.A", name="ax", label="L_a")
        b.p("L_p", "wff", ("ps",), proof=["L_f", "L_e", ax_handle])
    ub = b.to_proof_unit("d.B")

    src = LinkerV0().link([ua, ub])

    # None of the bare local label names should appear as standalone tokens
    for tok in ["L_f", "L_e", "L_a", "L_p"]:
        assert not _contains_token(
            src, tok
        ), f"found unrelocated token {tok} in output\n{src}"

    # But their relocated forms must exist
    assert _contains_token(src, "L_f__d_A")
    assert _contains_token(src, "L_e__d_A")
    assert _contains_token(src, "L_a__d_A")
    assert _contains_token(src, "L_f__d_B")
    assert _contains_token(src, "L_e__d_B")
    assert _contains_token(src, "L_p__d_B")

    # And the proof line of L_p__d_B must reference relocated L_a__d_A
    assert _contains_token(src, "L_a__d_A")
