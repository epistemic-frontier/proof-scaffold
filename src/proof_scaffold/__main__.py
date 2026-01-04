from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .linker_v1.diag import LinkerDiagError
from .linker_v1.sanity.check_sanity import run_sanity
from proof_scaffold.verifier import verify


def _build_dir(*parts: str) -> Path:
    # Repo convention: all runtime artifacts live under ./build
    return Path("build").joinpath(*parts)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_example_minimal_ok(*, write_mm: bool = True) -> None:
    from examples.minimal_ok import run as run_example

    mm_text = run_example()
    if write_mm:
        _write_text(_build_dir("examples", "minimal_ok", "out.mm"), mm_text)

    # Verify from a temp file (verifier reads from disk).
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as td:
        mm_path = Path(td) / "minimal_ok.mm"
        mm_path.write_text(mm_text, encoding="utf-8")
        verify(Path("verifier/mmverify.py"), mm_path)


def _run_example_minimal_diag(*, write_mm: bool = False) -> None:
    from examples.minimal_diag import run as run_example

    run_example()
    # minimal_diag is expected to fail before emission; keep side effects minimal.
    if write_mm:
        raise AssertionError("minimal_diag should not emit")


def _cmd_sanity(_args: argparse.Namespace) -> int:
    run_sanity()
    print("accepted")
    return 0


def _cmd_example(args: argparse.Namespace) -> int:
    name = args.name
    if name == "minimal_ok":
        _run_example_minimal_ok(write_mm=not args.no_write)
        print("accepted")
        return 0
    if name == "minimal_diag":
        _run_example_minimal_diag(write_mm=not args.no_write)
        # If it didn't raise, it's unexpected.
        print("unexpected: minimal_diag did not fail")
        return 2

    print(f"unknown example: {name}", file=sys.stderr)
    return 2


def _cmd_smoke(args: argparse.Namespace) -> int:
    run_sanity()
    _run_example_minimal_ok(write_mm=not args.no_write)
    print("accepted")
    return 0


def _cmd_diag_to_json(_args: argparse.Namespace) -> int:
    # Utility subcommand for debugging: run minimal_diag and dump diag JSON.
    try:
        _run_example_minimal_diag()
    except LinkerDiagError as e:
        print(e.diag.to_json(indent=2))
        return 1
    return 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m proof_scaffold")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_smoke = sub.add_parser("smoke", help="run sanity + minimal_ok")
    p_smoke.add_argument("--no-write", action="store_true", help="do not write build/* artifacts")
    p_smoke.set_defaults(func=_cmd_smoke)

    p_sanity = sub.add_parser("sanity", help="run M0.1 sanity only")
    p_sanity.set_defaults(func=_cmd_sanity)

    p_example = sub.add_parser("example", help="run a named example")
    p_example.add_argument("name", choices=["minimal_ok", "minimal_diag"])
    p_example.add_argument("--no-write", action="store_true", help="do not write build/* artifacts")
    p_example.set_defaults(func=_cmd_example)

    p_diag = sub.add_parser("diag-json", help="run minimal_diag and print diagnostic JSON")
    p_diag.set_defaults(func=_cmd_diag_to_json)

    args = p.parse_args(argv)

    try:
        return int(args.func(args))
    except LinkerDiagError as e:
        # Stable, deterministic rendering.
        print(str(e), file=sys.stderr)
        # Also write JSON sidecar if possible.
        try:
            _write_text(_build_dir("diag.json"), e.diag.to_json(indent=2) + "\n")
        except Exception:
            # Do not allow sidecar errors to mask primary error.
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
