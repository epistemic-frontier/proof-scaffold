# verify_driver_full.py
import os
import shutil
import sys
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, os.path.abspath("src"))

from skfd.driver.runner import DriverRunner


def main() -> None:
    root = Path("src")
    target = Path("target_verify")
    
    # Clean target
    if target.exists():
        shutil.rmtree(target)
        
    print(f"Initializing DriverRunner(root={root}, target={target})...")
    runner = DriverRunner(root, target)
    
    print("\n--- Spec 1: Execute All (Build) ---")
    runner.execute_all()
    
    print("\n--- Spec 2: Verify Logic (Monolith) ---")
    runner.verify_package("logic")
    
    outfile = target / "logic_full.mm"
    if not outfile.exists():
        print("FAILURE: logic_full.mm not found")
        sys.exit(1)
        
    content = outfile.read_text()
    print(f"\nGenerered Monolith Content ({outfile}):")
    print("-" * 40)
    print(content)
    print("-" * 40)
    
    # Check for both constants tokens
    if "prelude_const" in content and "logic_const" in content:
        print("\nSUCCESS: Both prelude and logic constants found in monolith.")
    else:
        print("\nFAILURE: Missing constants in monolith.")
        sys.exit(1)

if __name__ == "__main__":
    main()
