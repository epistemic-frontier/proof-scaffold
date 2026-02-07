from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "skfd.cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_init_package_mode(tmp_path: Path) -> None:
    res = _run_cli(tmp_path, "init", "demo-pkg")
    assert res.returncode == 0, (res.stdout, res.stderr)

    root = tmp_path / "demo-pkg"
    assert (root / ".skfd").read_text(encoding="utf-8").strip() == "active = ['mmverify']"
    assert ".skfd" in (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert (root / "pyproject.toml").exists()
    assert (root / "src" / "demo_pkg" / "__init__.py").exists()


def test_init_proof_mode(tmp_path: Path) -> None:
    res = _run_cli(tmp_path, "init", "demo-proof", "--mode", "proof")
    assert res.returncode == 0, (res.stdout, res.stderr)

    root = tmp_path / "demo-proof"
    assert (root / ".skfd").read_text(encoding="utf-8").strip() == "active = ['mmverify']"
    assert ".skfd" in (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert not (root / "pyproject.toml").exists()
    assert (root / "proof.py").exists()
