# tests/driver/test_runner.py
from pathlib import Path

import pytest
from skfd.driver.runner import DriverRunner


@pytest.fixture
def workspace(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    target = tmp_path / "target"
    return src, target

def create_package(src_root: Path, name: str, deps: list[str], build_code: str):
    pkg_dir = src_root / name
    pkg_dir.mkdir()
    # Note: we need to handle indentation in build_code manually or dedicat
    # Better to just write simple strings.
    
    manifest_code = f"""
from typing import Any
from skfd.builder import MMBuilder

def manifest() -> dict[str, Any]:
    return {{ "deps": {deps} }}
"""
    full_code = manifest_code + "\n" + build_code
    (pkg_dir / "build.py").write_text(full_code, encoding="utf-8")

def test_runner_integration(workspace):
    src, target = workspace
    
    # 1. Create pkg_a (Base)
    create_package(src, "pkg_a", [], """
def build(mm: MMBuilder, **deps: Any) -> Any:
    mm.c("const_a")
    return {"val": "A"}
""")

    # 2. Create pkg_b (Depends on A)
    create_package(src, "pkg_b", ["pkg_a"], """
def build(mm: MMBuilder, **deps: Any) -> Any:
    # Check injection
    if deps.get("pkg_a", {}).get("val") != "A":
        raise ValueError("Deps injection failed")
        
    mm.c("const_b")
    mm.v("var_b")
    return {"val": "B"}
""")

    # 3. Create pkg_c (Depends on B, transitively on A)
    create_package(src, "pkg_c", ["pkg_b"], """
def build(mm: MMBuilder, **deps: Any) -> Any:
    mm.c("const_c")
    return None
""")

    # Run Driver
    runner = DriverRunner(src, target)
    runner.execute_all()
    
    # Assert build success
    assert "pkg_a" in runner.lirs
    assert "pkg_b" in runner.lirs
    assert "pkg_c" in runner.lirs
    
    # Verify pkg_b (Should include A and B)
    runner.verify_package("pkg_b")
    out_b = target / "pkg_b_full.mm"
    assert out_b.exists()
    content_b = out_b.read_text()
    assert "const_a" in content_b
    assert "const_b" in content_b
    assert "var_b" in content_b
    assert "const_c" not in content_b # Downstream
    
    # Verify pkg_c (Should include A, B, and C)
    runner.verify_package("pkg_c")
    out_c = target / "pkg_c_full.mm"
    assert out_c.exists()
    content_c = out_c.read_text()
    assert "const_a" in content_c
    assert "const_b" in content_c
    assert "const_c" in content_c
