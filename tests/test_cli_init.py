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
    res = _run_cli(tmp_path, "init-pkg", "demo-pkg")
    assert res.returncode == 0, (res.stdout, res.stderr)

    root = tmp_path
    skfd_text = (root / ".skfd").read_text(encoding="utf-8")
    assert "active = ['mmverify']" in skfd_text
    assert (root / "pyproject.toml").exists()
    assert (root / "src" / "demo_pkg" / "__init__.py").exists()
    assert (root / "src" / "demo_pkg" / "build.py").exists()


def test_init_proof_mode(tmp_path: Path) -> None:
    res = _run_cli(tmp_path, "init-proof", "demo-proof.py")
    assert res.returncode == 0, (res.stdout, res.stderr)

    root = tmp_path
    skfd_text = (root / ".skfd").read_text(encoding="utf-8")
    assert "active = ['mmverify']" in skfd_text
    assert (root / "demo-proof.py").exists()
