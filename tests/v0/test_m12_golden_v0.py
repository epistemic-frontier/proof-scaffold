from __future__ import annotations

import json

import pytest

from proof_scaffold.ir import (
    Axiom,
    ConstDecl,
    EssentialHyp,
    FloatingHyp,
    Origin,
    ProofUnitIR,
    ScopeEnter,
    ScopeExit,
    VarDecl,
)
from proof_scaffold.ir import (
    Theorem as LIRTheorem,
)
from proof_scaffold.linker.errors import LinkerDiagError
from proof_scaffold.linker_v0 import LinkerV0


def _stable_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


@pytest.mark.golden
def test_golden_m12_diagnostic_stable_snapshot() -> None:
    """
    B1. For a fixed erroneous input, run twice and ensure Diagnostic JSON is byte-identical.
    Use an unresolved label in a single unit to trigger E_UNRESOLVED_LABEL.
    """
    u = ProofUnitIR(
        unit_id="gold.diag",
        lir=[
            ConstDecl((0,), origin=Origin(file="gold.py", line=1)),
            VarDecl((1,), origin=Origin(file="gold.py", line=2)),
            ScopeEnter(origin=Origin(file="gold.py", line=3)),
            FloatingHyp(label="wph", typecode=0, var=1, origin=Origin(file="gold.py", line=4)),
            LIRTheorem(
                label="bad",
                typecode=0,
                expr=(1,),
                proof_tokens=(2,),
                origin=Origin(file="gold.py", line=10),
            ),
            ScopeExit(origin=Origin(file="gold.py", line=20)),
        ],
        origin=Origin(file="gold.py", line=0),
        symtab=("wff", "ph", "missing_label"),
    )

    def run_once() -> dict[str, object]:
        try:
            LinkerV0().link([u])
        except LinkerDiagError as e:
            return e.diag.to_json_obj()
        raise AssertionError("expected LinkerDiagError")

    d1 = run_once()
    d2 = run_once()

    # byte-identical JSON snapshot
    assert _stable_json(d1) == _stable_json(d2)


@pytest.mark.golden
def test_golden_m12_symbol_table_ordering() -> None:
    """
    B2. Symbol table ordering must be stable and deterministic for a fixed input.
    Validate two runs produce identical rows and that ordering follows the policy:
    - $c sorted, then $v sorted, then per unit (sorted by unit_id) labels sorted by name.
    """
    ua = ProofUnitIR(
        unit_id="u.alpha",
        lir=[
            ConstDecl((0, 1), origin=Origin(file="A.py", line=1)),
            VarDecl((2, 3), origin=Origin(file="A.py", line=2)),
            ScopeEnter(origin=Origin(file="A.py", line=3)),
            FloatingHyp(label="wph", typecode=0, var=2, origin=Origin(file="A.py", line=4)),
            EssentialHyp(label="h", typecode=0, expr=(2,), origin=Origin(file="A.py", line=5)),
            Axiom(label="ax", typecode=0, expr=(3,), origin=Origin(file="A.py", line=6)),
            ScopeExit(origin=Origin(file="A.py", line=7)),
        ],
        origin=Origin(file="A.py", line=0),
        symtab=("wff", "|-", "ph", "ps"),
    )

    ub = ProofUnitIR(
        unit_id="u.beta",
        lir=[
            ConstDecl((0, 1), origin=Origin(file="B.py", line=1)),
            VarDecl((2,), origin=Origin(file="B.py", line=2)),
            ScopeEnter(origin=Origin(file="B.py", line=3)),
            Axiom(label="bax", typecode=3, expr=(2,), origin=Origin(file="B.py", line=4)),
            ScopeExit(origin=Origin(file="B.py", line=5)),
        ],
        origin=Origin(file="B.py", line=0),
        # Note: ub references typecode "wff" but doesn't declare it locally; this is OK
        # for build_symbol_table ordering purposes (it only inspects local decl stmts).
        symtab=("(", ")", "ch", "wff"),
    )

    linker = LinkerV0()
    rows1 = linker.build_symbol_table([ua, ub])
    rows2 = linker.build_symbol_table([ub, ua])  # different input order must not change result
    assert rows1 == rows2

    # Basic ordering assertions
    # Header tokens first ($c sorted, then $v sorted)
    head = [(o, n, k) for (o, n, k, _i) in rows1 if o == "<global>"]
    globals_only = [n for (_o, n, _k) in head]
    assert globals_only == sorted(globals_only)

    # Then units in unit_id order; labels within each unit are alphabetically sorted
    body = [(o, n, k) for (o, n, k, _i) in rows1 if o != "<global>"]
    # group by unit_id in contiguous blocks
    units_seen: list[str] = []
    cur_unit = None
    cur_names: list[str] = []
    for o, n, _k in body:
        if cur_unit is None:
            cur_unit = o
            units_seen.append(o)
            cur_names = [n]
        elif o == cur_unit:
            cur_names.append(n)
        else:
            # finish previous block
            assert cur_names == sorted(cur_names)
            # move to next unit block
            units_seen.append(o)
            cur_unit = o
            cur_names = [n]
    if cur_unit is not None:
        assert cur_names == sorted(cur_names)
    assert units_seen == sorted(set(units_seen), key=lambda x: x)
