from __future__ import annotations

import hashlib

from ...ir import (
    ConstDecl,
    LIRStmt,
    ScopeEnter,
    ScopeExit,
    VarDecl,
)
from ..context import FrameStmt, LinearPlan, LinkContext, ScopeFramePlan
from ..diag_helpers import raise_link_error


def _stable_u64(text: str) -> int:
    """Stable u64 derived from sha256(text).

    DO NOT use Python's built-in hash(), because it is randomized per-process.
    """

    d = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(d[:8], byteorder="big", signed=False)


def _is_decl_local_stmt(st: LIRStmt) -> bool:
    # In this codebase, decls_local are the hypothesis/decl statements.
    # Exports are the $a/$p assertions.
    #
    # We treat these as "local decl" candidates:
    # - $f / $e / $d
    # - structural scope markers (ignored for ordering but counted for balance)
    # - $c/$v are *not* allowed inside frames for M1.4 (dropped)
    from ...ir import DisjointDecl, EssentialHyp, FloatingHyp

    return isinstance(st, (FloatingHyp, EssentialHyp, DisjointDecl))


def _is_export_stmt(st: LIRStmt) -> bool:
    from ...ir import Axiom, Theorem

    return isinstance(st, (Axiom, Theorem))


def run(ctx: LinkContext) -> None:
    """Stage 5: Scope planning (M1.4 conservative ScopeFrames).

    For each unit (in topo order), emit exactly one outer `${ ... $}` frame.

    Hard rules enforced:
    - unit's internal ScopeEnter/Exit must be balanced (already enforced by Stage1);
      additionally, Stage5 ensures no scope imbalance *after dropping* $c/$v.
    - decls_local must appear before exports (E_EXPORT_ORDER_INVALID)
    - drop ConstDecl / VarDecl inside frames (note N_DROPPED_LOCAL_CV_DECL)
    """

    ordered_units = ctx.ordered_infos or ctx.infos
    frames: list[ScopeFramePlan] = []

    for frame_id, info in enumerate(ordered_units):
        # --- Conformance: exports must come after decls_local (fail-fast)
        # We scan original order and ensure no "decl-local" stmt appears after an export.
        seen_export = False
        for st in info.stmts:
            # $c/$v are dropped; they should not participate in decl/export ordering.
            if isinstance(st, (ConstDecl, VarDecl)):
                continue
            # Scope markers are structural; ignore for this ordering rule.
            if isinstance(st, (ScopeEnter, ScopeExit)):
                continue
            if _is_export_stmt(st):
                seen_export = True
            elif _is_decl_local_stmt(st) and seen_export:
                raise_link_error(
                    "E_EXPORT_ORDER_INVALID",
                    "decls_local must appear before exports within a unit",
                    primary=getattr(st, "origin", None),
                    chain=("Stage5", f"unit={info.unit_id}"),
                    details={"unit": info.unit_id},
                )

        # --- Build planned frame body, with filtering + synthetic scope markers
        stmts: list[FrameStmt] = []
        stmts.append(
            FrameStmt(
                stmt=ScopeEnter(origin=info.unit_origin),
                origin=info.unit_origin,
                synthetic_tag="linker:stage5:ScopeEnter",
            )
        )

        depth = 0
        for st in info.stmts:
            # drop $c/$v (hard rule)
            if isinstance(st, (ConstDecl, VarDecl)):
                ctx.lint_notes.append(
                    {
                        "code": "N_DROPPED_LOCAL_CV_DECL",
                        "unit_id": info.unit_id,
                        "origin": getattr(st, "origin", None),
                    }
                )
                continue

            if isinstance(st, ScopeEnter):
                depth += 1
                stmts.append(FrameStmt(stmt=st, origin=st.origin))
                continue
            if isinstance(st, ScopeExit):
                depth -= 1
                if depth < 0:
                    raise_link_error(
                        "E_UNIT_SCOPE_IMBALANCE",
                        "unit contains extra ScopeExit (after filtering)",
                        primary=st.origin,
                        related=(info.unit_origin,),
                        chain=("Stage5", f"unit={info.unit_id}"),
                        details={"unit": info.unit_id},
                    )
                stmts.append(FrameStmt(stmt=st, origin=st.origin))
                continue

            stmts.append(FrameStmt(stmt=st, origin=getattr(st, "origin", None)))

        if depth != 0:
            raise_link_error(
                "E_UNIT_SCOPE_IMBALANCE",
                "unit contains unmatched ScopeEnter/ScopeExit (after filtering)",
                primary=info.unit_origin,
                chain=("Stage5", f"unit={info.unit_id}"),
                details={"unit": info.unit_id, "depth": depth},
            )

        stmts.append(
            FrameStmt(
                stmt=ScopeExit(origin=info.unit_origin),
                origin=info.unit_origin,
                synthetic_tag="linker:stage5:ScopeExit",
            )
        )

        frames.append(
            ScopeFramePlan(
                frame_id=frame_id,
                unit_id=info.unit_id,
                origin_ref=info.unit_origin,
                context_hash=_stable_u64(info.unit_id),
                stmts=tuple(stmts),
            )
        )

    ctx.linear_plan = LinearPlan(frames=tuple(frames))
