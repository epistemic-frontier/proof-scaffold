# tests/test_sanity.py

import subprocess
import sys
from pathlib import Path


def verify_with_mmverify(test_script: Path) -> subprocess.CompletedProcess:
    root = Path(__file__).resolve().parents[1]
    mmverify = root / "verifier" / "metamath-knife"
    # mmverify =  root / "verifier" / "mmverify.py"
    proc = subprocess.run(
        [sys.executable, str(test_script), "--mmverify", str(mmverify)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout


def test_00_env():
    root = Path(__file__).resolve().parents[1]
    verify_with_mmverify(root / "tools" / "sanity" / "check_00_env.py")


def test_01_minimal_db():
    root = Path(__file__).resolve().parents[1]
    verify_with_mmverify(root / "tools" / "sanity" / "check_01_minimal_db.py")


def test_02_stack_machine():
    root = Path(__file__).resolve().parents[1]
    verify_with_mmverify(root / "tools" / "sanity" / "check_02_stack_machine.py")


def test_03_mandatory_f():
    root = Path(__file__).resolve().parents[1]
    verify_with_mmverify(root / "tools" / "sanity" / "check_03_mandatory_f.py")


def test_04_essential_e():
    root = Path(__file__).resolve().parents[1]
    verify_with_mmverify(root / "tools" / "sanity" / "check_04_essential_e.py")
