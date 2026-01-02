# proof_scaffold/linker_v0.py
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .diag import Diagnostic
from .ir import (
    Axiom,
    ConstDecl,
    DisjointDecl,
    EssentialHyp,
    FloatingHyp,
    LIRStmt,
    Origin,
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


class LinkerDiagError(LinkerError):
    def __init__(self, diag: Diagnostic) -> None:
        super().__init__(f"{diag.error_code}: {diag.message}")
        self.diag = diag

    def __str__(self) -> str:  # include origin hints to satisfy existing tests
        def fmt(o: Origin | None) -> str:
            if o is None:
                return "<unknown origin>"
            parts: list[str] = []
            if o.file:
                parts.append(str(o.file))
            if o.line is not None:
                parts.append(str(o.line))
            return ":".join(parts) if parts else "<unknown origin>"

        base = f"{self.diag.error_code}: {self.diag.message}"
        segs: list[str] = []
        if self.diag.primary_origin is not None:
            segs.append(fmt(self.diag.primary_origin))
        for ro in self.diag.related_origins:
            if ro is not None:
                segs.append(fmt(ro))
        if segs:
            return base + " [" + ", ".join(segs) + "]"
        return base


@dataclass
class _UnitInfo:
    unit_id: str
    stmts: list[LIRStmt]
    # labels: name -> kind ("$f","$e","$a","$p")
    labels: dict[str, str]
    # label origins for diagnostics: name -> origin
    label_origin: dict[str, Origin | None]
    # uses of other units' exported labels ($a/$p) by name
    uses_assertions: set[str]
    # per-unit floating hyp mapping and order
    f_label_of_var: dict[str, str]
    f_order: list[str]
    # per-unit assertion statements (typecode + expr tokens)
    assertion_stmt: dict[str, list[str]]
    # exported labels for this unit (only $a/$p). None means "all $a/$p exported" (compat)
    exports: set[str] | None
    # unit origin for diagnostics
    unit_origin: Origin | None


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

    def build_symbol_table(self, units: Iterable[ProofUnitIR]) -> list[tuple[str, str, str, int]]:
        """
        Build a deterministic global symbol table snapshot for tests.
        Returns a list of tuples: (origin_id, local_name, kind, ordinal_id)
        origin_id := unit_id for labels; '<global>' for $c/$v
        Ordering policy:
        - All global tokens ($c and $v) are combined and sorted by name (stable), not grouped by kind.
        - Then per-unit blocks ordered by unit_id; inside each unit, labels sorted by name.
        """
        unit_list = [u for u in units]
        infos, global_consts, global_vars, label_owners, label_kind_by_unit = self._stage1(unit_list)
        rows: list[tuple[str, str, str]] = []
        globals_rows: list[tuple[str, str, str]] = []
        for c in global_consts:
            globals_rows.append(("<global>", c, "CONST"))
        for v in global_vars:
            globals_rows.append(("<global>", v, "VAR"))
        # sort all globals by token name deterministically
        globals_rows.sort(key=lambda t: t[1])
        rows.extend(globals_rows)
        # then units in unit_id order, and names within unit sorted
        for info in sorted(infos, key=lambda x: x.unit_id):
            for name, kind in sorted(info.labels.items()):
                rows.append((info.unit_id, name, kind))
        return [(o, n, k, idx) for idx, (o, n, k) in enumerate(rows)]

    # --------
    # Stages
    # --------
    def _stage1(
        self, unit_list: list[ProofUnitIR]
    ) -> tuple[list[_UnitInfo], set[str], set[str], dict[str, set[str]], dict[tuple[str, str], str]]:
        infos: list[_UnitInfo] = []
        global_consts: set[str] = set()
        global_vars: set[str] = set()

        # helper to pretty-print origin
        def fmt_origin(o: Origin | None) -> str:
            if o is None:
                return "<unknown origin>"
            parts: list[str] = []
            if o.module:
                parts.append(str(o.module))
            if o.file:
                parts.append(str(o.file))
            if o.line is not None:
                parts.append(str(o.line))
            return ":".join(parts) if parts else "<unknown origin>"

        # label_name -> set[unit_id]
        label_owners: dict[str, set[str]] = {}
        # (unit_id, label_name) -> kind
        label_kind_by_unit: dict[tuple[str, str], str] = {}

        for u in unit_list:
            labels: dict[str, str] = {}
            label_origin: dict[str, Origin | None] = {}
            uses_assertions: set[str] = set()
            f_label_of_var: dict[str, str] = {}
            f_order: list[str] = []
            assertion_stmt: dict[str, list[str]] = {}

            # Scope balance check (Stage 5/7 early guard): ensure unit-local scopes are balanced
            depth = 0
            for st in u.lir:
                if isinstance(st, ScopeEnter):
                    depth += 1
                elif isinstance(st, ScopeExit):
                    depth -= 1
                    if depth < 0:
                        raise LinkerDiagError(Diagnostic(
                            error_code="E_SCOPE_IMBALANCE",
                            message=f"scope imbalance detected in unit {u.unit_id}: extra ScopeExit",
                            primary_origin=u.origin,
                            origin_chain=("Stage1", f"unit={u.unit_id}"),
                        ))
            if depth != 0:
                raise LinkerDiagError(Diagnostic(
                    error_code="E_SCOPE_IMBALANCE",
                    message=f"scope imbalance detected in unit {u.unit_id}: unmatched ScopeEnter/ScopeExit",
                    primary_origin=u.origin,
                    origin_chain=("Stage1", f"unit={u.unit_id}"),
                ))

            # Collect and early lint
            for st in u.lir:
                if isinstance(st, ConstDecl):
                    for s in st.symbols:
                        if not isinstance(s, SymbolRef):
                            raise LinkerDiagError(Diagnostic(
                                error_code="E_RAW_TOKEN_FORBIDDEN",
                                message="ConstDecl contains non-SymbolRef token",
                                primary_origin=st.origin,
                                origin_chain=("Stage1", f"unit={u.unit_id}"),
                            ))
                        global_consts.add(s.name)
                elif isinstance(st, VarDecl):
                    for s in st.symbols:
                        if not isinstance(s, SymbolRef):
                            raise LinkerDiagError(Diagnostic(
                                error_code="E_RAW_TOKEN_FORBIDDEN",
                                message="VarDecl contains non-SymbolRef token",
                                primary_origin=st.origin,
                                origin_chain=("Stage1", f"unit={u.unit_id}"),
                            ))
                        global_vars.add(s.name)
                elif isinstance(st, FloatingHyp):
                    lab = st.label
                    label_owners.setdefault(lab, set()).add(u.unit_id)
                    label_kind_by_unit[(u.unit_id, lab)] = "$f"
                    labels[lab] = "$f"
                    label_origin[lab] = st.origin
                    v = st.var.name
                    f_label_of_var[v] = lab
                    if v not in f_order:
                        f_order.append(v)
                elif isinstance(st, EssentialHyp):
                    lab = st.label
                    label_owners.setdefault(lab, set()).add(u.unit_id)
                    label_kind_by_unit[(u.unit_id, lab)] = "$e"
                    labels[lab] = "$e"
                    label_origin[lab] = st.origin
                elif isinstance(st, Axiom):
                    lab = st.label
                    label_owners.setdefault(lab, set()).add(u.unit_id)
                    label_kind_by_unit[(u.unit_id, lab)] = "$a"
                    labels[lab] = "$a"
                    label_origin[lab] = st.origin
                    assertion_stmt[lab] = [st.typecode.name] + [t.name for t in st.expr]
                elif isinstance(st, Theorem):
                    lab = st.label
                    label_owners.setdefault(lab, set()).add(u.unit_id)
                    label_kind_by_unit[(u.unit_id, lab)] = "$p"
                    labels[lab] = "$p"
                    label_origin[lab] = st.origin
                    assertion_stmt[lab] = [st.typecode.name] + [t.name for t in st.expr]
                    # Inspect proof tokens for uses (names only; owners resolved later)
                    for tk in st.proof_tokens:
                        if not isinstance(tk, SymbolRef):
                            raise LinkerDiagError(Diagnostic(
                                error_code="E_RAW_TOKEN_FORBIDDEN",
                                message="proof token is not a SymbolRef (raw string token forbidden)",
                                primary_origin=st.origin,
                                origin_chain=("Stage1", f"unit={u.unit_id}", f"stmt={lab}"),
                            ))
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

            # compute exports set for this unit (only $a/$p)
            if u.exports is None:
                exports_set: set[str] | None = None  # compat: all $a/$p exported
            else:
                exports_set = set(u.exports)

            infos.append(_UnitInfo(
                unit_id=u.unit_id,
                stmts=list(u.lir),
                labels=labels,
                label_origin=label_origin,
                uses_assertions=uses_assertions,
                f_label_of_var=f_label_of_var,
                f_order=f_order,
                assertion_stmt=assertion_stmt,
                exports=exports_set,
                unit_origin=u.origin,
            ))

        # Early lint: cross-unit $f/$e usage, non-export references, unresolved symbols
        # fmt_origin already defined above in this method

        exports_by_unit: dict[str, set[str] | None] = {i.unit_id: i.exports for i in infos}

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
                            raise LinkerDiagError(Diagnostic(
                                error_code="E_UNRESOLVED_LABEL",
                                message=f"unresolved label in proof: '{step}' (in unit {info.unit_id})",
                                primary_origin=st.origin,
                                origin_chain=("Stage1", f"unit={info.unit_id}", f"stmt={st.label}"),
                                details={"label": step},
                            ))
                        # leakage via $f/$e
                        leak_from = [own for own in owners if label_kind_by_unit.get((own, step)) in ("$f", "$e")]
                        if leak_from:
                            offender = sorted(leak_from)[0]
                            off_o = next((i for i in infos if i.unit_id == offender), None)
                            off_origin = off_o.label_origin.get(step) if off_o else None
                            raise LinkerDiagError(Diagnostic(
                                error_code="E_CROSS_UNIT_HYP_LEAKAGE",
                                message=f"cross-unit hypothesis leakage: '{step}'",
                                primary_origin=st.origin,
                                related_origins=(off_origin,),
                                origin_chain=("Stage1", f"unit={info.unit_id}", f"stmt={st.label}"),
                                details={"offender_unit": offender, "label": step},
                            ))
                        # non-exported $a/$p usage
                        ap_owners = [own for own in owners if label_kind_by_unit.get((own, step)) in ("$a", "$p")]
                        if ap_owners:
                            exported_ok = False
                            for own in ap_owners:
                                ex = exports_by_unit.get(own)
                                if ex is None or step in ex:
                                    exported_ok = True
                                    break
                            if not exported_ok:
                                owner = sorted(ap_owners)[0]
                                own_info = next((i for i in infos if i.unit_id == owner), None)
                                def_origin = own_info.label_origin.get(step) if own_info else None
                                raise LinkerDiagError(Diagnostic(
                                    error_code="E_NON_EXPORTED_LABEL_REF",
                                    message=f"non-exported label reference: '{step}'",
                                    primary_origin=st.origin,
                                    related_origins=(def_origin,),
                                    origin_chain=("Stage1", f"unit={info.unit_id}", f"stmt={st.label}"),
                                    details={"owner_unit": owner, "label": step},
                                ))
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

        def fmt_origin(o: Origin | None) -> str:
            if o is None:
                return "<unknown origin>"
            parts: list[str] = []
            if getattr(o, "module", None):
                parts.append(str(o.module))
            if getattr(o, "file", None):
                parts.append(str(o.file))
            if getattr(o, "line", None) is not None:
                parts.append(str(o.line))
            return ":".join(parts) if parts else "<unknown origin>"
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
                                # respect exports (None -> all exported; else must be listed)
                                own_info = next((ii for ii in infos if ii.unit_id == owner), None)
                                if own_info is None:
                                    continue
                                if own_info.exports is None or step in own_info.exports:
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
                path = cycle_stack + [n]
                # include origins for all units in the detected cycle for better diagnostics
                related = tuple(info_by_id[uid].unit_origin for uid in path if uid != n)
                raise LinkerDiagError(Diagnostic(
                    error_code="E_DEP_CYCLE",
                    message="dependency cycle detected",
                    primary_origin=info_by_id[n].unit_origin,
                    related_origins=related,
                    origin_chain=("Stage4", f"unit={n}"),
                    details={"cycle": path},
                ))
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
