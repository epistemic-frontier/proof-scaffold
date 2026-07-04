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
    build_py = root / "src" / "demo_pkg" / "build.py"
    assert build_py.exists()
    assert "def build(ctx" in build_py.read_text(encoding="utf-8")

    verify = _run_cli(tmp_path, "verify", "demo-pkg")
    assert verify.returncode == 0, (verify.stdout, verify.stderr)


def test_init_proof_mode(tmp_path: Path) -> None:
    res = _run_cli(tmp_path, "init-proof", "demo-proof.py")
    assert res.returncode == 0, (res.stdout, res.stderr)

    root = tmp_path
    skfd_text = (root / ".skfd").read_text(encoding="utf-8")
    assert "active = ['mmverify']" in skfd_text
    proof_py = root / "demo-proof.py"
    assert proof_py.exists()
    text = proof_py.read_text(encoding="utf-8")
    assert "SETMM_TO_HILBERT_LEMMAS" in text
    assert "LemmaBuilder" not in text
    assert "LemmaProof" not in text
