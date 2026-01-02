from __future__ import annotations

from pathlib import Path

from proof_scaffold.dsl import MMBuilder
from proof_scaffold.ir import (
    Axiom,
    ConstDecl,
    EssentialHyp,
    FloatingHyp,
    Origin,
    ProofUnitIR,
    ScopeEnter,
    ScopeExit,
    SymbolRef,
    VarDecl,
)
from proof_scaffold.ir import (
    Theorem as LIRTheorem,
)
from proof_scaffold.linker_v0 import LinkerV0
from proof_scaffold.theorem import Theorem
from tests._sanity_utils import verify_expect_ok

# Helpers for golden snapshot checks

def _scan_emitted_names(mm_src: str) -> set[str]:
    names: set[str] = set()
    for line in mm_src.splitlines():
        line = line.strip()
        if not line or line.startswith("$("):
            continue
        if line.startswith("$"):
            continue
        # labeled stmts start with the label
        parts = line.split()
        if parts and parts[0] not in {"$.", "${", "$}"}:
            # First token is label for $f/$e/$a/$p
            names.add(parts[0])
    return names


def _proof_body_lines(mm_src: str) -> list[str]:
    lines: list[str] = []
    in_proof = False
    for ln in mm_src.splitlines():
        if "$=" in ln:
            in_proof = True
            continue
        if in_proof:
            if ln.strip() == "$.":
                in_proof = False
            else:
                lines.append(ln.strip())
    return lines


def _write(tmp_path: Path, mm_src: str) -> Path:
    p = tmp_path / "linked.mm"
    p.write_text(mm_src, encoding="utf-8")
    return p


def test_sanity_m11_single_unit_links(tmp_path: Path) -> None:
    # Build a single ProofUnit via DSL
    mm = MMBuilder()
    mm.c("wff", "(", ")", "->", "|-")
    mm.v("ph")
    mm.f("wph", "wff", "ph")
    mm.a("ax-id", "|-", ("(", "ph", "->", "ph", ")"))
    with mm.block():
        mm.p("t", "|-", ("(", "ph", "->", "ph", ")"), proof=["wph", "ax-id"])

    u = mm.to_proof_unit("sanity.u1")

    # Link and emit
    linker = LinkerV0()
    mm_src = linker.link([u])

    # Determinism: linking the same input twice yields identical output
    mm_src_2 = linker.link([u])
    assert mm_src == mm_src_2

    # Verify with metamath
    verify_expect_ok(_write(tmp_path, mm_src))


def test_sanity_m11_two_units_cross_module_links(tmp_path: Path) -> None:
    # Unit A: provides ax-mp
    a = MMBuilder()
    a.c("wff", "(", ")", "->")
    a.v("ph", "ps")
    a.f("wph", "wff", "ph")
    a.f("wps", "wff", "ps")
    # axiom modus ponens shape: |- ps given ph and (ph -> ps)
    with a.block():
        a.e("h1r", "wff", ("ph",))
        a.e("h2r", "wff", ("(", "ph", "->", "ps", ")"))
        a.a("ax-mp", "wff", ("ps",))
    ua = a.to_proof_unit("m.modus")

    # Unit B: uses ax-mp from A to prove thm
    b = MMBuilder()
    b.c("wff", "(", ")", "->")
    b.v("ph", "ps")
    b.f("wph", "wff", "ph")
    b.f("wps", "wff", "ps")
    # Cross-unit reference via Theorem handle (label = "ax-mp")
    ax_mp_handle = Theorem(
        fqname="m.modus.ax_mp_export", module_id="m.modus", name="ax_mp_export", label="ax-mp"
    )
    with b.block():
        b.e("h1", "wff", ("ph",))
        b.e("h2", "wff", ("(", "ph", "->", "ps", ")"))
        b.p("th", "wff", ("ps",), proof=["wph", "wps", "h1", "h2", ax_mp_handle])
    ub = b.to_proof_unit("m.user")

    linker = LinkerV0()
    mm_src = linker.link([ua, ub])

    # Structure checks: header first, then exactly two scope frames
    assert mm_src.splitlines()[0].startswith("$c ")  # header hoists constants
    assert "${" in mm_src and "$}" in mm_src
    assert mm_src.count("${") == 2 and mm_src.count("$}") == 2

    # Determinism snapshot
    assert mm_src == linker.link([ua, ub])

    verify_expect_ok(_write(tmp_path, mm_src))


# -----------------
# B. Golden Tests
# -----------------

def test_golden_m11_deterministic_emission() -> None:
    # Build two units with cross dependency
    a = MMBuilder()
    a.c("wff", "(", ")", "->")
    a.v("ph", "ps")
    a.f("wph", "wff", "ph")
    a.f("wps", "wff", "ps")
    with a.block():
        a.e("h1r", "wff", ("ph",))
        a.e("h2r", "wff", ("(", "ph", "->", "ps", ")"))
        a.a("ax-mp", "wff", ("ps",))
    ua = a.to_proof_unit("m.modus")

    b = MMBuilder()
    b.c("wff", "(", ")", "->")
    b.v("ph", "ps")
    b.f("wph", "wff", "ph")
    b.f("wps", "wff", "ps")
    ax_mp_handle = Theorem(
        fqname="m.modus.ax_mp_export", module_id="m.modus", name="ax_mp_export", label="ax-mp"
    )
    with b.block():
        b.e("h1", "wff", ("ph",))
        b.e("h2", "wff", ("(", "ph", "->", "ps", ")"))
        b.p("th", "wff", ("ps",), proof=["wph", "wps", "h1", "h2", ax_mp_handle])
    ub = b.to_proof_unit("m.user")

    # Determinism across runs and input order
    l1 = LinkerV0().link([ua, ub])
    l2 = LinkerV0().link([ub, ua])  # reversed input order should not affect output
    l3 = LinkerV0().link([ua, ub])  # new instance, same order

    assert l1 == l2 == l3


def test_golden_m11_relocation_snapshot() -> None:
    # Same setup as above to assert relocation names are stable
    a = MMBuilder()
    a.c("wff", "(", ")", "->")
    a.v("ph", "ps")
    a.f("wph", "wff", "ph")
    a.f("wps", "wff", "ps")
    with a.block():
        a.e("h1r", "wff", ("ph",))
        a.e("h2r", "wff", ("(", "ph", "->", "ps", ")"))
        a.a("ax-mp", "wff", ("ps",))
    ua = a.to_proof_unit("m.modus")

    b = MMBuilder()
    b.c("wff", "(", ")", "->")
    b.v("ph", "ps")
    b.f("wph", "wff", "ph")
    b.f("wps", "wff", "ps")
    ax_mp_handle = Theorem(
        fqname="m.modus.ax_mp_export", module_id="m.modus", name="ax_mp_export", label="ax-mp"
    )
    with b.block():
        b.e("h1", "wff", ("ph",))
        b.e("h2", "wff", ("(", "ph", "->", "ps", ")"))
        b.p("th", "wff", ("ps",), proof=["wph", "wps", "h1", "h2", ax_mp_handle])
    ub = b.to_proof_unit("m.user")

    mm_src = LinkerV0().link([ua, ub])

    # Expected relocated label names
    expected_names = {
        # unit A labels relocated with suffix from unit id m.modus -> m_modus
        "wph__m_modus",
        "wps__m_modus",
        "h1r__m_modus",
        "h2r__m_modus",
        "ax-mp__m_modus",
        # unit B labels relocated with suffix from unit id m.user -> m_user
        "wph__m_user",
        "wps__m_user",
        "h1__m_user",
        "h2__m_user",
        "th__m_user",
    }

    emitted_names = _scan_emitted_names(mm_src)
    # All expected names must be present
    assert expected_names.issubset(emitted_names)

    # The proof tokens of th__m_user must be fully relocated and reference the relocated ax-mp
    # Expect a single proof line with all steps relocated deterministically
    proof_lines = _proof_body_lines(mm_src)
    assert any(
        ln == "wph__m_user wps__m_user h1__m_user h2__m_user ax-mp__m_modus" for ln in proof_lines
    )


# -----------------
# C. Adversarial Tests
# -----------------

def test_adv_m11_forbid_raw_string_tokens_default_off() -> None:
    # Construct LIR with a raw string in proof_tokens to simulate COMPAT-off violation
    lir = [
        ConstDecl((SymbolRef("wff"), SymbolRef("|-"), SymbolRef("("), SymbolRef(")"), SymbolRef("->")), origin=Origin(module="mod", file="x.py", line=1)),
        VarDecl((SymbolRef("ph"),), origin=Origin(module="mod", file="x.py", line=2)),
        FloatingHyp(label="wph", typecode=SymbolRef("wff"), var=SymbolRef("ph"), origin=Origin(module="mod", file="x.py", line=3)),
        Axiom(label="ax-id", typecode=SymbolRef("|-"), expr=(SymbolRef("("), SymbolRef("ph"), SymbolRef("->"), SymbolRef("ph"), SymbolRef(")")), origin=Origin(module="mod", file="x.py", line=4)),
        # Raw string token "ax-id" below should be rejected at Stage 1
        LIRTheorem(
            label="t",
            typecode=SymbolRef("|-"),
            expr=(SymbolRef("("), SymbolRef("ph"), SymbolRef("->"), SymbolRef("ph"), SymbolRef(")")),
            proof_tokens=(SymbolRef("wph"), "ax-id"),  # type: ignore[arg-type]
            origin=Origin(module="mod", file="x.py", line=5),
        ),
    ]
    u = ProofUnitIR(unit_id="adv.raw", lir=lir, origin=Origin(module="mod", file="x.py", line=0))
    try:
        LinkerV0().link([u])
        raise AssertionError("expected LinkerError for raw string proof token")
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        assert isinstance(e, Exception)
        assert "raw string token" in msg or "SymbolRef" in msg
        assert "x.py" in msg


def test_adv_m11_forbid_cross_unit_hyp_leakage() -> None:
    # Unit A defines essential hypotheses h1r/h2r and an axiom
    ua = ProofUnitIR(
        unit_id="m.modus",
        lir=[
            ConstDecl((SymbolRef("wff"), SymbolRef("("), SymbolRef(")"), SymbolRef("->")), origin=Origin(file="a.py", line=1)),
            VarDecl((SymbolRef("ph"), SymbolRef("ps")), origin=Origin(file="a.py", line=2)),
            FloatingHyp(label="wph", typecode=SymbolRef("wff"), var=SymbolRef("ph"), origin=Origin(file="a.py", line=3)),
            FloatingHyp(label="wps", typecode=SymbolRef("wff"), var=SymbolRef("ps"), origin=Origin(file="a.py", line=4)),
            ScopeEnter(origin=Origin(file="a.py", line=5)),
            EssentialHyp(label="h1r", typecode=SymbolRef("wff"), expr=(SymbolRef("ph"),), origin=Origin(file="a.py", line=6)),
            EssentialHyp(label="h2r", typecode=SymbolRef("wff"), expr=(SymbolRef("("), SymbolRef("ph"), SymbolRef("->"), SymbolRef("ps"), SymbolRef(")")), origin=Origin(file="a.py", line=7)),
            Axiom(label="ax-mp", typecode=SymbolRef("wff"), expr=(SymbolRef("ps"),), origin=Origin(file="a.py", line=8)),
            ScopeExit(origin=Origin(file="a.py", line=9)),
        ],
        origin=Origin(file="a.py", line=0),
    )
    # Unit B illegally references A's essential hypothesis h1r in its proof tokens
    ub = ProofUnitIR(
        unit_id="m.user",
        lir=[
            ConstDecl((SymbolRef("wff"), SymbolRef("("), SymbolRef(")"), SymbolRef("->")), origin=Origin(file="b.py", line=1)),
            VarDecl((SymbolRef("ph"), SymbolRef("ps")), origin=Origin(file="b.py", line=2)),
            FloatingHyp(label="wph", typecode=SymbolRef("wff"), var=SymbolRef("ph"), origin=Origin(file="b.py", line=3)),
            FloatingHyp(label="wps", typecode=SymbolRef("wff"), var=SymbolRef("ps"), origin=Origin(file="b.py", line=4)),
            ScopeEnter(origin=Origin(file="b.py", line=5)),
            EssentialHyp(label="h1", typecode=SymbolRef("wff"), expr=(SymbolRef("ph"),), origin=Origin(file="b.py", line=6)),
            EssentialHyp(label="h2", typecode=SymbolRef("wff"), expr=(SymbolRef("("), SymbolRef("ph"), SymbolRef("->"), SymbolRef("ps"), SymbolRef(")")), origin=Origin(file="b.py", line=7)),
            LIRTheorem(
                label="th",
                typecode=SymbolRef("wff"),
                expr=(SymbolRef("ps"),),
                proof_tokens=(
                    SymbolRef("wph"), SymbolRef("wps"), SymbolRef("h1"), SymbolRef("h2"), SymbolRef("h1r"),
                ),
                origin=Origin(file="b.py", line=8),
            ),
            ScopeExit(origin=Origin(file="b.py", line=9)),
        ],
        origin=Origin(file="b.py", line=0),
    )
    try:
        LinkerV0().link([ua, ub])
        raise AssertionError("expected LinkerError for cross-unit hypothesis leakage")
    except Exception as e:  # noqa: BLE001
        s = str(e)
        assert "hypothesis leakage" in s or "$f" in s or "$e" in s
        assert "b.py" in s


def test_adv_m11_forbid_non_export_label_reference() -> None:
    # Unit A defines a local theorem but does NOT export it; Unit B tries to use it.
    ua = ProofUnitIR(
        unit_id="u.A",
        lir=[
            ConstDecl((SymbolRef("wff"),), origin=Origin(file="A.py", line=1)),
            VarDecl((SymbolRef("ph"),), origin=Origin(file="A.py", line=2)),
            ScopeEnter(origin=Origin(file="A.py", line=3)),
            LIRTheorem(
                label="secret_thm",
                typecode=SymbolRef("wff"),
                expr=(SymbolRef("ph"),),
                proof_tokens=(SymbolRef("secret_thm"),),  # self-ref bogus, we only care about visibility
                origin=Origin(file="A.py", line=4),
            ),
            ScopeExit(origin=Origin(file="A.py", line=5)),
        ],
        origin=Origin(file="A.py", line=0),
        exports=[],  # explicitly export nothing
    )
    ub = ProofUnitIR(
        unit_id="u.B",
        lir=[
            ConstDecl((SymbolRef("wff"),), origin=Origin(file="B.py", line=1)),
            VarDecl((SymbolRef("ph"),), origin=Origin(file="B.py", line=2)),
            ScopeEnter(origin=Origin(file="B.py", line=3)),
            LIRTheorem(
                label="use_secret",
                typecode=SymbolRef("wff"),
                expr=(SymbolRef("ph"),),
                proof_tokens=(SymbolRef("secret_thm"),),  # attempt to use A's non-exported label
                origin=Origin(file="B.py", line=4),
            ),
            ScopeExit(origin=Origin(file="B.py", line=5)),
        ],
        origin=Origin(file="B.py", line=0),
    )
    try:
        LinkerV0().link([ua, ub])
        raise AssertionError("expected LinkerError for non-export label reference")
    except Exception as e:  # noqa: BLE001
        s = str(e)
        assert "non-exported label" in s or "unresolved" in s
        assert "A.py" in s and "B.py" in s  # origins included


def test_adv_m11_dependency_cycle_detected() -> None:
    # Unit A theorem uses B's axiom; Unit B theorem uses A's axiom -> cycle
    ua = ProofUnitIR(
        unit_id="u.A",
        lir=[
            ConstDecl((SymbolRef("wff"),), origin=Origin(file="A.py", line=1)),
            VarDecl((SymbolRef("ph"),), origin=Origin(file="A.py", line=2)),
            ScopeEnter(origin=Origin(file="A.py", line=3)),
            Axiom(label="a_in_A", typecode=SymbolRef("wff"), expr=(SymbolRef("ph"),), origin=Origin(file="A.py", line=4)),
            LIRTheorem(
                label="tA",
                typecode=SymbolRef("wff"),
                expr=(SymbolRef("ph"),),
                proof_tokens=(SymbolRef("a_in_B"),),
                origin=Origin(file="A.py", line=5),
            ),
            ScopeExit(origin=Origin(file="A.py", line=6)),
        ],
        origin=Origin(file="A.py", line=0),
    )
    ub = ProofUnitIR(
        unit_id="u.B",
        lir=[
            ConstDecl((SymbolRef("wff"),), origin=Origin(file="B.py", line=1)),
            VarDecl((SymbolRef("ph"),), origin=Origin(file="B.py", line=2)),
            ScopeEnter(origin=Origin(file="B.py", line=3)),
            Axiom(label="a_in_B", typecode=SymbolRef("wff"), expr=(SymbolRef("ph"),), origin=Origin(file="B.py", line=4)),
            LIRTheorem(
                label="tB",
                typecode=SymbolRef("wff"),
                expr=(SymbolRef("ph"),),
                proof_tokens=(SymbolRef("a_in_A"),),
                origin=Origin(file="B.py", line=5),
            ),
            ScopeExit(origin=Origin(file="B.py", line=6)),
        ],
        origin=Origin(file="B.py", line=0),
    )
    try:
        LinkerV0().link([ua, ub])
        raise AssertionError("expected LinkerError for dependency cycle")
    except Exception as e:  # noqa: BLE001
        s = str(e)
        assert "cycle" in s
        assert "A.py" in s and "B.py" in s


def test_adv_m11_scope_unbalanced_rejected() -> None:
    # A unit with an extra ScopeEnter without matching ScopeExit
    u = ProofUnitIR(
        unit_id="u.badscope",
        lir=[
            ConstDecl((SymbolRef("wff"),), origin=Origin(file="bad.py", line=1)),
            VarDecl((SymbolRef("ph"),), origin=Origin(file="bad.py", line=2)),
            ScopeEnter(origin=Origin(file="bad.py", line=3)),
            FloatingHyp(label="wph", typecode=SymbolRef("wff"), var=SymbolRef("ph"), origin=Origin(file="bad.py", line=4)),
            # Missing ScopeExit here -> imbalance
        ],
        origin=Origin(file="bad.py", line=0),
    )
    try:
        LinkerV0().link([u])
        raise AssertionError("expected LinkerError for scope imbalance")
    except Exception as e:  # noqa: BLE001
        s = str(e)
        assert "scope" in s or "balance" in s
        assert "bad.py" in s
