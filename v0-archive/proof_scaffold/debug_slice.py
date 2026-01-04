"""Debug slice utilities (SPEC-0001: Debug Slice MVP).

This module is the user-facing implementation of the *debug slice* concept.

Current implementation focuses on the smallest reliable chain:

* verifier step index -> locate a proof token index
* proof token index -> find the enclosing theorem span within a unit
* print a small window of proof tokens around the span

We support both mapping paths described in the spec:

* Path A (preferred): emitted proof-step index -> step_id sidecar map
* Path B (fallback): treat verifier step index as a token index

NOTE: HIR Apply + subst digests are a future extension; the current project
milestone keeps this module LIR-focused.
"""

from __future__ import annotations

from dataclasses import dataclass

from proof_scaffold.linker.context import LinkContext


@dataclass(frozen=True)
class SliceResult:
    unit_id: str
    theorem_label: str
    mm_error_step: int
    span: tuple[int, int]
    window_start: int
    window_end: int
    window_tokens: tuple[str, ...]


def slice_from_link_context(
    ctx: LinkContext,
    *,
    mm_error_step: int,
    unit_id: str,
    theorem_label: str | None = None,
    window: int = 8,
) -> SliceResult:
    """Compute a debug slice for a verifier error step.

    Assumptions (MVP):
    - mm_error_step is 1-based and corresponds to the verifier's proof-step index.
    - Path A (preferred): ctx.emitted_step_to_step_id is present.
    - Path B (fallback): treat mm_error_step as a token index into ctx.proof_tokens.
    """

    if mm_error_step <= 0:
        raise ValueError("mm_error_step must be 1-based positive")
    if not ctx.proof_tokens or not ctx.theorem_to_span:
        raise ValueError("debug metadata missing: run linker emission first")

    # Preferred (Path A): emitted proof-step index -> step_id.
    step_id = ctx.emitted_step_to_step_id.get(mm_error_step)
    if step_id is not None:
        # Find the token index by scanning (acceptable for MVP sizes).
        # In the future we can store inverse map step_id->token_idx.
        idx = None
        for ti, sid in ctx.emitted_step_to_step_id.items():
            if sid == step_id:
                idx = ti - 1
                break
        if idx is None:
            raise ValueError(
                "internal error: step_id present but cannot locate token index"
            )
    else:
        # Fallback (Path B): treat as token index.
        idx = mm_error_step - 1

    if idx >= len(ctx.proof_tokens):
        raise ValueError(
            f"mm_error_step out of range: step={mm_error_step}, "
            f"proof_tokens={len(ctx.proof_tokens)}"
        )

    # Find candidate theorem spans for this unit.
    candidates: list[tuple[str, tuple[int, int]]] = []
    for (u, th), span in ctx.theorem_to_span.items():
        if u != unit_id:
            continue
        candidates.append((th, span))
    if not candidates:
        raise ValueError(f"no theorem spans found for unit_id={unit_id}")

    if theorem_label is not None:
        span_opt = ctx.theorem_to_span.get((unit_id, theorem_label))
        if span_opt is None:
            raise ValueError(f"unknown theorem_label in unit: {theorem_label}")
        span = span_opt
        chosen_label = theorem_label
    else:
        # If not specified, try to infer by locating the global token index.
        match = [(th, sp) for (th, sp) in candidates if sp[0] <= idx < sp[1]]
        if len(match) == 1:
            chosen_label, span = match[0]
        elif len(match) == 0:
            raise ValueError(
                "cannot infer theorem from mm_error_step; "
                "step is not inside any theorem span for this unit"
            )
        else:
            # Shouldn't happen in v0-archive since spans don't overlap, but keep safe.
            raise ValueError(
                "ambiguous theorem inference; please specify --theorem explicitly"
            )

    s, e = span
    ws = max(0, s - window)
    we = min(len(ctx.proof_tokens), e + window)
    window_tokens = tuple(ctx.proof_tokens[ws:we])

    return SliceResult(
        unit_id=unit_id,
        theorem_label=chosen_label,
        mm_error_step=mm_error_step,
        span=(s, e),
        window_start=ws,
        window_end=we,
        window_tokens=window_tokens,
    )
