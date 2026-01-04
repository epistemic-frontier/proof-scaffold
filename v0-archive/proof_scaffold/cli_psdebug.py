"""psdebug CLI (SPEC-0001 Debug Slice MVP).

This is intentionally minimal and LIR-only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .debug_slice import slice_from_link_context
from proof_scaffold.linker import LinkContext


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="psdebug")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("slice", help="Print a debug slice around a verifier error step")
    s.add_argument("--mm-error-step", type=int, required=True, help="verifier reported step index (1-based)")
    s.add_argument("--unit", dest="unit_id", type=str, required=True)
    s.add_argument("--theorem", dest="theorem_label", type=str, default=None)
    s.add_argument("--format", choices=("text", "json"), default="text")
    s.add_argument("--window", type=int, default=8)
    # For now: a python module that yields a list[ProofUnitIR] via get_units()
    s.add_argument("--units-py", type=Path, required=True, help="python file exporting get_units()")
    return p


def _load_units_from_py(path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ps_units", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import units from: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    get_units = getattr(mod, "get_units", None)
    if get_units is None:
        raise RuntimeError("units module must define get_units()")
    return get_units()


def _link_with_debug(units) -> LinkContext:
    # Use the existing link() API to get mm text, but we need LinkContext.
    # The current public API returns only mm text, so we call the internal
    # linker_v0-style function.
    from .linker_v0 import link_v0

    ctx, _mm = link_v0(units, return_context=True)
    return ctx  # type: ignore[no-any-return]


def main(argv: list[str] | None = None) -> int:
    p = _build_arg_parser()
    ns = p.parse_args(argv)

    if ns.cmd == "slice":
        units = _load_units_from_py(ns.units_py)
        ctx = _link_with_debug(units)
        res = slice_from_link_context(
            ctx,
            mm_error_step=ns.mm_error_step,
            unit_id=ns.unit_id,
            theorem_label=ns.theorem_label,
            window=ns.window,
        )
        if ns.format == "json":
            payload = {
                "unit_id": res.unit_id,
                "theorem_label": res.theorem_label,
                "mm_error_step": res.mm_error_step,
                "span": list(res.span),
                "window": [res.window_start, res.window_end],
                "tokens": list(res.window_tokens),
            }
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(f"unit_id: {res.unit_id}")
            print(f"theorem:  {res.theorem_label}")
            print(f"mm_step:  {res.mm_error_step}")
            print(f"span:     [{res.span[0]},{res.span[1]})")
            print(f"window:   [{res.window_start},{res.window_end})")
            print("tokens:")
            for i, t in enumerate(res.window_tokens, start=res.window_start):
                mark = "<-" if i == (res.mm_error_step - 1) else "  "
                print(f"  {i:6d} {t} {mark}")
        return 0

    raise AssertionError("unreachable")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
