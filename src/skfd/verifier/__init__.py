# skfd/verifier/__init__.py
# src/skfd/verify.py
from __future__ import annotations

import subprocess
from pathlib import Path


def verify(command: list[str], mm_file: Path, timeout_sec: int = 60) -> None:
    """
    Run a verifier command against a .mm file.

    Args:
        command: The command line to execute (e.g. ["python3", "verifier/mmverify.py"]).
                 The `.mm` file path will be appended to this command.
        mm_file: Path to the .mm file to verify.
        timeout_sec: Timeout in seconds.
    """
    mm_file = Path(mm_file)

    if not mm_file.exists():
        raise FileNotFoundError(f".mm file not found: {mm_file}")

    # command is trusted to be correct from config/caller
    full_cmd = command + [str(mm_file)]

    proc = subprocess.run(
        full_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_sec,
    )

    # Always print output so pytest captures it (helps debugging).
    if proc.stdout:
        print(proc.stdout)

    if proc.returncode != 0:
        error_msg = (
            "Metamath verification failed\n"
            f"cmd:      {full_cmd}\n"
            f"return:   {proc.returncode}\n"
            f"output:\n{proc.stdout}"
        )

        map_file = mm_file.with_suffix(".mm.map")
        if map_file.exists():
            import json
            import re

            match = re.search(r"\?Error at line (\d+):", proc.stdout)
            if match:
                line_failed = int(match.group(1))
                try:
                    mm_context = ""
                    try:
                        with open(mm_file, encoding="utf-8") as f_mm:
                            all_lines = f_mm.read().splitlines()
                        idx = line_failed - 1
                        radius = 4
                        start = max(0, idx - radius)
                        end = min(len(all_lines), idx + radius + 1)
                        numbered = []
                        for i in range(start, end):
                            prefix = ">" if i == idx else " "
                            numbered.append(f"{prefix} {i+1:6d}: {all_lines[i]}")
                        mm_context = "\n".join(numbered)
                    except Exception as mm_exc:
                        mm_context = f"(failed to read .mm context: {mm_exc})"

                    with open(map_file, encoding="utf-8") as f:
                        map_data = json.load(f)

                    origin_ref = None
                    for entry in map_data.get("mappings", []):
                        if entry.get("line") == line_failed:
                            origin_ref = entry.get("origin_ref")
                            break

                    if origin_ref is not None:
                        origins = map_data.get("origins", [])
                        if 0 <= origin_ref < len(origins):
                            orig = origins[origin_ref]
                            f_path = orig.get("file", "??")
                            f_line = orig.get("line", "??")
                            error_msg += f"\n\n--> Source Origin: {f_path}:{f_line}\n"

                    if mm_context:
                        error_msg += (
                            f"\n\n--> MM context around line {line_failed} in {mm_file}:\n"
                            f"{mm_context}\n"
                        )
                except Exception as e:
                    error_msg += f"\n(Failed to apply source map: {e})"

        raise RuntimeError(error_msg)
