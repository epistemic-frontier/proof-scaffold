from __future__ import annotations

import subprocess


def test_cli_smoke_one_command() -> None:
    """M0.2 acceptance: one command runs sanity + minimal_ok."""

    res = subprocess.run(
        ["skfd", "smoke", "--no-write"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, (res.stdout, res.stderr)
