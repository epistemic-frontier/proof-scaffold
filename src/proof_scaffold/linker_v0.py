# proof_scaffold/linker_v0.py
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .ir import (
    Axiom,
    ConstDecl,
    DisjointDecl,
    EssentialHyp,
    FloatingHyp,
    LIRStmt,
    ProofUnitIR,
    ScopeEnter,
    ScopeExit,
    SymbolRef,
    Theorem,
    VarDecl,
)


class LinkerError(Exception):
    """Linker errors (not frozen; allow traceback attachment)."""
    pass


@dataclass
class _UnitInfo:
    unit_id: str
    stmts: list[LIRStmt]
    # labels: name -> kind ("$f","$e","$a","$p")
    labels: dict[str, str]
    # uses of other units' exported labels ($a/$p) by name
    uses_assertions: set[str]
    # per-unit floating hyp mapping and order
    f_label_of_var: dict[str, str]
    f_order: list[str]
    # per-unit assertion statements (typecode + expr tokens)
    assertion_stmt: dict[str, list[str]]


class LinkerV0:
    """
    Minimal M1.1 baseline linker:
      - Stage 1: symbol resolution (within the provided units) & early lint
      - Stage 4: dependency closure (from proof tokens) & topo sort with cycle detection
      - Stage 5: conservative scope planning (one ScopeFrame per unit)
      - Stage 6: token-level relocation for all labels (deterministic, unit-suffixed)
      - Stage 7: two-phase emission (header: $c/$v; body: frames of $d/$f/$e/$a/$p)

    Notes:
      - `$d` handling is pass-through (Mode A): placed where declared within the unit frame.
      - All `$a/$p` are treated as exported in this v0 baseline.
      - Raw-string tokens are not present in LIR (all tokens are SymbolRef by design).
    """

    def __init__(self) -> None:
        pass

    # --------
    # Public API
    # --------
    def link(self, units: Iterable[ProofUnitIR]) -> str:
        unit_list = [u for u in units]
        if not unit_list:
            raise LinkerError("no units provided to linker")

        # Stage 1: build unit infos, collect global symbols, early lint
        infos, global_consts, global_vars, label_owners, label_kind_by_unit = self._stage1(unit_list)

        # Stage 4: dependency closure & topo sort
        order_units = self._stage4(infos, label_owners, label_kind_by_unit)

        # Stage 6: relocation map (labels only; $c/$v kept verbatim for now)
        relabel = self._build_label_relocation(infos)

        # Stage 7: emit
        return self._emit(
            global_consts,
            global_vars,
            order_units,
            relabel,
            label_owners=label_owners,
            label_kind_by_unit=label_kind_by_unit,
        )

    # --------
    # Stages
    # --------
    def _stage1(
        self, unit_list: list[ProofUnitIR]
    ) -> tuple[list[_UnitInfo], set[str], set[str], dict[str, set[str]], dict[tuple[str, str], str]]:
        infos: list[_UnitInfo] = []
        global_consts: set[str] = set()
        global_vars: set[str] = set()

        # label_name -> set[unit_id]
        label_owners: dict[str, set[str]] = {}
        # (unit_id, label_name) -> kind
        label_kind_by_unit: dict[tuple[str, str], str] = {}

        for u in unit_list:
            labels: dict[str, str] = {}
            uses_assertions: set[str] = set()
            f_label_of_var: dict[str, str] = {}
            f_order: list[str] = []
            assertion_stmt: dict[str, list[str]] = {}

            # Collect and early lint
            for st in u.lir:
                if isinstance(st, ConstDecl):
                    for s in st.symbols:
                        if not isinstance(s, SymbolRef):
                            raise LinkerError("ConstDecl contains non-SymbolRef token")
                        global_consts.add(s.name)
                elif isinstance(st, VarDecl):
                    for s in st.symbols:
                        if not isinstance(s, SymbolRef):
                            raise LinkerError("VarDecl contains non-SymbolRef token")
                        global_vars.add(s.name)
                elif isinstance(st, FloatingHyp):
                    lab = st.label
                    label_owners.setdefault(lab, set()).add(u.unit_id)
                    label_kind_by_unit[(u.unit_id, lab)] = "$f"
                    labels[lab] = "$f"
                    v = st.var.name
                    f_label_of_var[v] = lab
                    if v not in f_order:
                        f_order.append(v)
                elif isinstance(st, EssentialHyp):
                    lab = st.label
                    label_owners.setdefault(lab, set()).add(u.unit_id)
                    label_kind_by_unit[(u.unit_id, lab)] = "$e"
                    labels[lab] = "$e"
                elif isinstance(st, Axiom):
                    lab = st.label
                    label_owners.setdefault(lab, set()).add(u.unit_id)
                    label_kind_by_unit[(u.unit_id, lab)] = "$a"
                    labels[lab] = "$a"
                    assertion_stmt[lab] = [st.typecode.name] + [t.name for t in st.expr]
                elif isinstance(st, Theorem):
                    lab = st.label
                    label_owners.setdefault(lab, set()).add(u.unit_id)
                    label_kind_by_unit[(u.unit_id, lab)] = "$p"
                    labels[lab] = "$p"
                    assertion_stmt[lab] = [st.typecode.name] + [t.name for t in st.expr]
                    # Inspect proof tokens for uses (names only; owners resolved later)
                    for tk in st.proof_tokens:
                        if not isinstance(tk, SymbolRef):
                            raise LinkerError("proof token is not a SymbolRef (raw string token forbidden)")
                        step = tk.name
                        # mark that this theorem uses an assertion name; real edges computed in Stage 4
                        # (not strictly needed but kept for potential diagnostics)
                        if any(label_kind_by_unit.get((own, step)) in ("$a", "$p") for own in label_owners.get(step, set())):
                            uses_assertions.add(step)
                elif isinstance(st, (ScopeEnter, ScopeExit, DisjointDecl)):
                    # Transparent to Stage 1
                    pass
                else:  # pragma: no cover - future-proof
                    raise LinkerError(f"unknown LIR stmt: {type(st)}")

            infos.append(_UnitInfo(
                unit_id=u.unit_id,
                stmts=list(u.lir),
                labels=labels,
                uses_assertions=uses_assertions,
                f_label_of_var=f_label_of_var,
                f_order=f_order,
                assertion_stmt=assertion_stmt,
            ))

        # Early lint: cross-unit $f/$e usage and unresolved symbols
        for info in infos:
            for st in info.stmts:
                if isinstance(st, Theorem):
                    for tk in st.proof_tokens:
                        step = tk.name
                        # local label is always OK
                        if (info.unit_id, step) in label_kind_by_unit:
                            continue
                        owners = label_owners.get(step)
                        if not owners:
                            raise LinkerError(
                                f"unresolved label in proof: '{step}' (in unit {info.unit_id})"
                            )
                        # If any owner defines this name as $f/$e, it's a leakage
                        leak_from = [own for own in owners if label_kind_by_unit.get((own, step)) in ("$f", "$e")]
                        if leak_from:
                            offender = sorted(leak_from)[0]
                            raise LinkerError(
                                f"cross-unit hypothesis leakage: '{step}' from {offender} used in {info.unit_id}"
                            )
        return infos, global_consts, global_vars, label_owners, label_kind_by_unit

    def _stage4(
        self,
        infos: list[_UnitInfo],
        label_owners: dict[str, set[str]],
        label_kind_by_unit: dict[tuple[str, str], str],
    ) -> list[_UnitInfo]:
        # Build unit dependency graph: unit A -> unit B if A uses an $a/$p from B
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
                            raise LinkerError(f"unresolved exported label: {step}")
                        for owner in owners:
                            kind = label_kind_by_unit.get((owner, step))
                            if kind in ("$a", "$p") and owner != i.unit_id:
                                deps[i.unit_id].add(owner)

        # topo sort + cycle detection
        temp_mark: set[str] = set()
        perm_mark: set[str] = set()
        order: list[str] = []
        cycle_stack: list[str] = []

        def visit(n: str) -> None:
            if n in perm_mark:
                return
            if n in temp_mark:
                # cycle detected; reconstruct a small path
                cycle_stack.append(n)
                raise LinkerError("dependency cycle detected: " + " -> ".join(cycle_stack + [n]))
            temp_mark.add(n)
            cycle_stack.append(n)
            for m in sorted(deps[n]):
                visit(m)
            cycle_stack.pop()
            temp_mark.remove(n)
            perm_mark.add(n)
            order.append(n)

        for uid in sorted(deps.keys()):
            if uid not in perm_mark:
                visit(uid)

        # order currently: dependencies first (postorder). Map to infos
        ordered_infos = [info_by_id[u] for u in order]
        return ordered_infos

    def _build_label_relocation(self, infos: list[_UnitInfo]) -> dict[tuple[str, str], str]:
        relabel: dict[tuple[str, str], str] = {}
        for info in infos:
            suffix = self._mangle_suffix(info.unit_id)
            for name, _kind in sorted(info.labels.items()):
                # relocate all label kinds to avoid collisions deterministically per unit
                relabel[(info.unit_id, name)] = f"{name}__{suffix}"
        return relabel

    @staticmethod
    def _mangle_suffix(unit_id: str) -> str:
        # Deterministic, readable: replace dots with underscores
        return unit_id.replace("/", "_").replace(".", "_")

    # --------
    # Emission
    # --------
    def _emit(
        self,
        global_consts: set[str],
        global_vars: set[str],
        ordered_units: list[_UnitInfo],
        relabel: dict[tuple[str, str], str],
        *,
        label_owners: dict[str, set[str]] | None = None,
        label_kind_by_unit: dict[tuple[str, str], str] | None = None,
    ) -> str:
        out: list[str] = []
        # Header: $c / $v (sorted, deterministic)
        if global_consts:
            consts = " ".join(sorted(global_consts))
            out.append(f"$c {consts} $.")
        if global_vars:
            vars_ = " ".join(sorted(global_vars))
            out.append(f"$v {vars_} $.")

        # Body: one ScopeFrame per unit
        for info in ordered_units:
            out.append("${")
            # Emit in original order but ensure $f/$e before $a/$p naturally by relying on input order
            for st in info.stmts:
                if isinstance(st, DisjointDecl):
                    toks = " ".join(s.name for s in st.symbols)
                    out.append(f"$d {toks} $.")
                elif isinstance(st, FloatingHyp):
                    tc = st.typecode.name
                    var = st.var.name
                    lab = relabel[(info.unit_id, st.label)]
                    out.append(f"{lab} $f {tc} {var} $.")
                elif isinstance(st, EssentialHyp):
                    tc = st.typecode.name
                    expr = " ".join(t.name for t in st.expr)
                    lab = relabel[(info.unit_id, st.label)]
                    out.append(f"{lab} $e {tc} {expr} $.")
                elif isinstance(st, Axiom):
                    tc = st.typecode.name
                    expr = " ".join(t.name for t in st.expr)
                    lab = relabel[(info.unit_id, st.label)]
                    out.append(f"{lab} $a {tc} {expr} $.")
                elif isinstance(st, Theorem):
                    tc = st.typecode.name
                    expr = " ".join(t.name for t in st.expr)
                    lab = relabel[(info.unit_id, st.label)]
                    # proof tokens: rewrite with deterministic relocation, preserving order
                    steps: list[str] = []
                    for tk in st.proof_tokens:
                        nm = tk.name
                        # Prefer local mapping if present
                        key_local = (info.unit_id, nm)
                        if key_local in relabel:
                            steps.append(relabel[key_local])
                            continue
                        owners = (label_owners or {}).get(nm, set())
                        if owners:
                            owner = sorted(owners)[0]
                            mapped = relabel.get((owner, nm), nm)
                            steps.append(mapped)
                        else:
                            steps.append(nm)
                    out.append(f"{lab} $p {tc} {expr} $=")
                    out.append("  " + " ".join(steps))
                    out.append("$.")

                elif isinstance(st, (ConstDecl, VarDecl, ScopeEnter, ScopeExit)):
                    # Header hoists $c/$v; ScopeEnter/Exit are replaced by the unit ScopeFrame
                    continue
                else:  # pragma: no cover - future-proof
                    raise LinkerError(f"unknown LIR stmt at emission: {type(st)}")
            out.append("$}")

        return "\n".join(out) + ("\n" if out else "")
