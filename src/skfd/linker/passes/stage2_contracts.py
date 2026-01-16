# skfd/linker/passes/stage2_contracts.py
from __future__ import annotations

from dataclasses import dataclass, field

from skfd.core.contracts import AssertionContract, TheoremDetails
from skfd.core.lir import (
    Axiom,
    EssentialHyp,
    FloatingHyp,
    ScopeEnter,
    ScopeExit,
    Theorem,
)
from skfd.core.symbols import SymbolDef, SymbolId
from skfd.core.unit import ProofUnitIR


@dataclass(frozen=True)
class ContractIndex:
    """Results of contract extraction."""

    # usage: contracts[label_id] -> Contract
    contracts: dict[SymbolId, AssertionContract] = field(default_factory=dict)
    # usage: details[label_id] -> Details
    details: dict[SymbolId, TheoremDetails] = field(default_factory=dict)


def run(units: list[ProofUnitIR], symtab: dict[SymbolId, SymbolDef]) -> ContractIndex:
    """
    Stage 2: Contract Extraction.

    Analyses units to determine:
    1. Interface definition of every $a/$p (Contract)
    2. Dependency usage of every $p (Details)
    """
    contracts: dict[SymbolId, AssertionContract] = {}
    details: dict[SymbolId, TheoremDetails] = {}

    for u in units:
        # Per unit, we need to track state to determine mandatory hyps.
        # However, LIR units are flat lists of statements.
        # But wait, $e and $f scope is technically frame-based or unit-based.
        # For 'Mandatory Hyps', we look at what is active *at the projected open scope*.
        #
        # In Metamath, constraints are:
        # A $p statement uses hyps that are "active" in the scope.
        # But 'AssertionContract' defines what a *user* of this assertion sees.
        # A user sees the frame: {$e... $f... $a/$p ...}.
        #
        # Simplified for Bootstrap:
        # In a generic "LIR Unit", we usually define hyps, then assertion.
        # We assume strict compliance: the local hyps ($e/$f) preceding an assertion
        # ARE its mandatory hypotheses.
        #
        # Algorithm:
        # 1. Track current open floating_hyps ($f) and essential_hyps ($e).
        # 2. When hitting $a/$p:
        #    - Collect all current $e.
        #    - Collect all $f necessary for variables in $e and the assertion expr.
        #    - *Actually*, standard Metamath tools often compute this from the logic.
        #    - BUT, in our scaffold, typically units might be minimal (one assertion per unit).
        #    - Let's assuming "Greedy Collection" of all preceding local hyps in the unit?
        #    - Or does LIR carry this info?
        #    - Inspect LIR: `Axiom(expr, ...)` doesn't list mandatory hyps.
        #    - BUT, `emit_mm` just emits what it sees.
        #
        # CAUTION:
        # Computing "Mandatory Variables" ($f) strictly requires parsing the expression
        # and finding the active $f for each variable.
        # `mandatory_vars` order is usually "order of appearance in assertion expr + hyps".
        #
        # Let's verify what `Link Model v4` expects.
        # Usually Stage 2 extracts this.
        # If we want to stay simple for now (since we don't have an expression parser in linker yet):
        # We can scan the Unit's LIR for FloatingHyp and EssentialHyp statements *preceding* the assertion.
        #
        # Optimization for "One Assertion Per Unit" (Common in this scaffold):
        # Just scan the whole unit's LIR for $e and $f.
        #
        # Correctness check:
        # If a unit has multiple assertions, are scoping rules respected?
        # LIR has `ScopeEnter/Exit`.
        # Correct scope logic: maintain a stack of active hyps.

        # We do need rudimentary scope tracking to be correct for multi-assertion units.
        scope_stack_f: list[list[FloatingHyp]] = []
        scope_stack_e: list[list[EssentialHyp]] = []

        # Current frame accumulation
        current_frame_f: list[FloatingHyp] = []
        current_frame_e: list[EssentialHyp] = []

        for st in u.lir_stmts:
            if isinstance(st, ScopeEnter):
                # Push current frame to stack
                scope_stack_f.append(list(current_frame_f))
                scope_stack_e.append(list(current_frame_e))
                # New frame starts with copy (scopes inherit?) or empty?
                # Metamath scopes nest. Inner scope sees outer symbols.
                # New declarations in inner scope are local.
                # So we usually copy or link. Python list copy is safe.
                pass
                # Wait, usually Metamath scope starts empty? No, it inherits.
                # "${ ... $}"
                # Definitions outside are visible. Definitions inside are discarded on exit.
                # So: push state.
                pass

            elif isinstance(st, ScopeExit):
                if scope_stack_f:
                    current_frame_f = scope_stack_f.pop()
                    current_frame_e = scope_stack_e.pop()
                else:
                    # Unbalanced, but Stage 1 should have caught or meaningful error
                    current_frame_f = []
                    current_frame_e = []

            elif isinstance(st, FloatingHyp):
                current_frame_f.append(st)

            elif isinstance(st, EssentialHyp):
                current_frame_e.append(st)

            elif isinstance(st, Axiom | Theorem):
                # Found an assertion attempt!
                # Compute contract.

                # 1. Mandatory Hyps ($e)
                # All active $e are mandatory for this assertion in this local scope block.
                # (Unless we do logic minimalization, but here we trust the authoring frame).
                m_hyps = [h.label for h in current_frame_e]

                # 2. Mandatory Vars ($f)
                # Need to find variables in expr and hyps.
                # Helper to collect Vars from an expr tokens

                required_vars: set[SymbolId] = set()

                def scan_vars(
                    expr: tuple[SymbolId, ...], target_vars: set[SymbolId]
                ) -> None:
                    for t in expr:
                        kind = symtab[t].kind
                        if kind == "Var":
                            target_vars.add(t)

                # Scan assertion expr
                scan_vars(tuple(st.expr), required_vars)
                # Scan mandatory hyps (essential hyps)
                for h_stmt in current_frame_e:
                    # Expr is list[int], scan_vars expects Sequence[int] or specific?
                    # MyPy complained "expected tuple". Let's update Helper scan_vars or cast.
                    # Helper definition: def scan_vars(tokens: tuple[int, ...], ...)
                    # But LIR tokens are list[int].
                    # We should convert to tuple before calling.
                    scan_vars(tuple(h_stmt.expr), required_vars)

                # Now filter active $f to find those matching required vars.
                # Order matters? Standard Metamath is "order of appearance".
                # But here we just need *a* set for the contract.
                # Let's keep them in frame order for stability.
                m_vars = []
                for f in current_frame_f:
                    if f.var in required_vars:
                        # Dedupe? Active frame shouldn't have dupe vars usually.
                        m_vars.append(f.label)

                contracts[st.label] = AssertionContract(
                    label=st.label,
                    mandatory_hyps=m_hyps,
                    mandatory_vars=m_vars,
                )

                if isinstance(st, Theorem):
                    # Compute dependencies
                    deps = set()
                    for t in st.proof:
                        # Proof tokens are labels.
                        # We only care if it's an assertion/hyp?
                        # TheoremDetails.direct_dependencies usually refers to OTHER assertions (Axioms/Theorems).
                        # Using a local hypothesis ($e/$f) is valid but not a "dependency" on another unit.
                        # How to distinguish? Kind?
                        # Symtab entry says "Label".
                        # Effectively, everything in proof is a dependency if it's not local.
                        # But filtering by "Is it an export of another unit" happens in Stage 4.
                        # Here we just collect all labels.
                        # Or strictly: only collecting labels that are NOT local hyps?
                        # Contract extraction usually focuses on "External References".
                        # Let's collect ALL labels for now, verify in Stage 4.
                        deps.add(t)

                    details[st.label] = TheoremDetails(
                        label=st.label,
                        direct_dependencies=deps,
                    )

    return ContractIndex(contracts, details)
