from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "skfd.cli", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def test_verify_prints_traceback_on_import_error(tmp_path: Path) -> None:
    # Arrange: create a minimal package that imports a missing module
    root = tmp_path
    src = root / "src" / "badpkg"
    src.mkdir(parents=True)

    (root / "pyproject.toml").write_text(
        """
[project]
name = "badpkg"
version = "0.0.1"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "build.py").write_text(
        """
from __future__ import annotations

import missing_module  # noqa: F401

def build(mm):
    return None
""".strip()
        + "\n",
        encoding="utf-8",
    )

    # Act
    proc = _run_cli(["verify", "badpkg"], cwd=root)

    # Assert
    assert proc.returncode != 0
    combined = proc.stderr + proc.stdout
    assert "Verification failed" in combined
    assert "Traceback" in combined
    assert "No module named" in combined


def test_verify_prints_hint_for_missing_prelude(tmp_path: Path) -> None:
    # Arrange: mimic a prelude import failure (in an isolated temp project)
    root = tmp_path
    src = root / "src" / "_tmp_missing_prelude"
    src.mkdir(parents=True)

    (src / "build.py").write_text(
        """
from __future__ import annotations

from prelude.formula import Builtins  # noqa: F401

def build(mm):
    return None
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (root / "pyproject.toml").write_text(
        """
[project]
name = "_tmp_missing_prelude"
version = "0.0.1"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    # Act
    proc = _run_cli(["verify", "_tmp_missing_prelude"], cwd=root)

    # Assert
    assert proc.returncode != 0
    combined = proc.stderr + proc.stdout
    assert "Hint: 'prelude' not found" in combined
    assert "Traceback" in combined
