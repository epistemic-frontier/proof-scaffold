from __future__ import annotations

from skfd.core.contracts import AssertionContract
from skfd.core.lir import (
    Axiom,
    DisjointVar,
    FloatingHyp,
    LIRStmt,
    ScopeEnter,
    ScopeExit,
    Theorem,
)
from skfd.core.symbols import SymbolDef, SymbolId
from skfd.core.unit import ProofUnitIR
from skfd.linker.passes.stage2_contracts import ContractIndex
from skfd.linker.passes.stage2_contracts import run as stage2_run
from skfd.linker.passes.stage3_disjoint import run as stage3_run
from skfd.linker.passes.stage4_topo_sort import run as stage4_run


def _unit(stmts: list[LIRStmt], export: SymbolId) -> ProofUnitIR:
    return ProofUnitIR(
        unit_id="test_unit",
        origin_ref=0,
        origin_module_id="mod",
        lir_stmts=stmts,
        exports=[export],
    )


def _var_symtab(names: dict[SymbolId, str]) -> dict[SymbolId, SymbolDef]:
    return {
        sid: SymbolDef(
            id=sid,
            kind="Var",
            origin_ref=0,
            local_name=name,
            origin_module_id="mod",
        )
        for sid, name in names.items()
    }


def test_assertion_contract_keeps_legacy_distinct_vars_position() -> None:
    contract = AssertionContract(1, [], [], [(2, 3)])

    assert contract.distinct_vars == [(2, 3)]
    assert contract.mandatory_var_ids == []


def test_stage3_expands_group_to_canonical_mandatory_pairs() -> None:
    # SymbolId order deliberately differs from semantic name order.
    s_z, s_x, s_y = 1, 2, 3
    symtab = _var_symtab({s_x: "x", s_y: "y", s_z: "z"})
    f_x, f_y, f_z = 4, 5, 6
    l_ax = 10
    contracts = ContractIndex(
        contracts={
            l_ax: AssertionContract(
                l_ax,
                [],
                [f_x, f_y, f_z],
                mandatory_var_ids=[s_x, s_y, s_z],
            )
        },
        details={},
    )
    unit = _unit(
        [
            FloatingHyp(1, 0, f_x, 0, s_x),
            FloatingHyp(2, 0, f_y, 0, s_y),
            FloatingHyp(3, 0, f_z, 0, s_z),
            ScopeEnter(4, 0),
            DisjointVar(5, 0, [s_z, s_x, s_y]),
            Axiom(6, 0, l_ax, 0, []),
            ScopeExit(7, 0),
        ],
        l_ax,
    )

    result = stage3_run([unit], symtab, contracts)

    assert result.contracts[l_ax].distinct_vars == [
        (s_x, s_y),
        (s_x, s_z),
        (s_y, s_z),
    ]


def test_stage3_excludes_proof_only_active_dv() -> None:
    s_x, s_y = 1, 2
    symtab = _var_symtab({s_x: "x", s_y: "y"})
    f_x, f_y = 3, 4
    l_th = 10
    contracts = ContractIndex(
        contracts={l_th: AssertionContract(l_th, [], [f_x], mandatory_var_ids=[s_x])},
        details={},
    )
    unit = _unit(
        [
            FloatingHyp(1, 0, f_x, 0, s_x),
            FloatingHyp(2, 0, f_y, 0, s_y),
            ScopeEnter(3, 0),
            DisjointVar(4, 0, [s_x, s_y]),
            Theorem(5, 0, l_th, 0, [], []),
            ScopeExit(6, 0),
        ],
        l_th,
    )

    result = stage3_run([unit], symtab, contracts)

    assert result.contracts[l_th].distinct_vars == []


def test_stage3_does_not_merge_pair_groups_into_clique() -> None:
    s_x, s_y, s_z = 1, 2, 3
    symtab = _var_symtab({s_x: "x", s_y: "y", s_z: "z"})
    f_x, f_y, f_z = 4, 5, 6
    l_ax = 10
    contracts = ContractIndex(
        contracts={
            l_ax: AssertionContract(
                l_ax,
                [],
                [f_x, f_y, f_z],
                mandatory_var_ids=[s_x, s_y, s_z],
            )
        },
        details={},
    )
    unit = _unit(
        [
            FloatingHyp(1, 0, f_x, 0, s_x),
            FloatingHyp(2, 0, f_y, 0, s_y),
            FloatingHyp(3, 0, f_z, 0, s_z),
            ScopeEnter(4, 0),
            DisjointVar(5, 0, [s_y, s_x]),
            DisjointVar(6, 0, [s_z, s_y]),
            Axiom(7, 0, l_ax, 0, []),
            ScopeExit(8, 0),
        ],
        l_ax,
    )

    result = stage3_run([unit], symtab, contracts)

    assert result.contracts[l_ax].distinct_vars == [(s_x, s_y), (s_y, s_z)]


def test_stage2_and_stage3_inherit_foundation_floating_hypotheses() -> None:
    s_x, s_y = 1, 2
    f_x, f_y = 3, 4
    l_ax = 10
    symtab = _var_symtab({s_x: "x", s_y: "y"})
    foundation = ProofUnitIR(
        unit_id="foundation",
        origin_ref=0,
        origin_module_id="foundation",
        lir_stmts=[
            FloatingHyp(1, 0, f_x, 0, s_x),
            FloatingHyp(2, 0, f_y, 0, s_y),
        ],
        exports=[f_x, f_y],
        kind="foundation",
    )
    library = _unit(
        [
            ScopeEnter(3, 0),
            DisjointVar(4, 0, [s_y, s_x]),
            Axiom(5, 0, l_ax, 0, [s_x, s_y]),
            ScopeExit(6, 0),
        ],
        l_ax,
    )

    input_units = [library, foundation]
    dependency_index = stage2_run(input_units, symtab)
    ordered = stage4_run(input_units, dependency_index)
    contracts = stage2_run(ordered, symtab)
    result = stage3_run(ordered, symtab, contracts)

    assert [unit.unit_id for unit in ordered] == ["foundation", "test_unit"]
    assert result.contracts[l_ax].mandatory_vars == [f_x, f_y]
    assert result.contracts[l_ax].mandatory_var_ids == [s_x, s_y]
    assert result.contracts[l_ax].distinct_vars == [(s_x, s_y)]


def test_stage3_inherits_top_level_foundation_dv() -> None:
    s_x, s_y = 1, 2
    f_x, f_y = 3, 4
    l_ax = 10
    symtab = _var_symtab({s_x: "x", s_y: "y"})
    foundation = ProofUnitIR(
        unit_id="foundation",
        origin_ref=0,
        origin_module_id="foundation",
        lir_stmts=[
            FloatingHyp(1, 0, f_x, 0, s_x),
            FloatingHyp(2, 0, f_y, 0, s_y),
            DisjointVar(3, 0, [s_x, s_y]),
        ],
        exports=[f_x, f_y],
        kind="foundation",
    )
    library = _unit([Axiom(4, 0, l_ax, 0, [s_x, s_y])], l_ax)

    contracts = stage2_run([foundation, library], symtab)
    result = stage3_run([foundation, library], symtab, contracts)

    assert result.contracts[l_ax].distinct_vars == [(s_x, s_y)]
