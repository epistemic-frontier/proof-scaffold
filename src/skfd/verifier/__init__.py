# skfd/verifier/__init__.py
# src/skfd/verify.py
from __future__ import annotations

import subprocess
from pathlib import Path


def _explain_output(output: str) -> str:
    text = output.lower()
    messages: list[str] = []
    if "stack underflow" in text:
        messages.append(
            "检测到 stack underflow：当前语句需要的强制假设多于 proof 实际提供的栈条目。"
            "请检查 proof token 的数量和顺序，以及是否遗漏了某些必需的 `$f`/`$e`。"
        )
    if "stack entry" in text and "doesn't match hypothesis" in text:
        messages.append(
            "检测到栈条目与假设不匹配：某一步的栈顶公式与对应的 mandatory/essential hypothesis 不同。"
            "通常意味着 proof 中标签顺序错误，或使用了错误的中间结论。"
        )
    if "cannot be unified" in text and "hypothesis" in text:
        messages.append(
            "检测到假设无法统一：verifier 无法将 proof 中给出的公式与公理/定理的假设模式对齐。"
            "这通常是 proof 步骤顺序或子公式结构不正确导致的。"
        )
    if "$e" in text and "top level" in text:
        messages.append(
            "检测到 $e 作用域错误：$e 只能出现在 `${ ... $}` 作用域块内，不能在顶层声明。"
            "建议将相关规则 skeleton 包裹在作用域块中。"
        )
    if not messages:
        return ""
    lines = ["", "Explanation:"]
    for m in messages:
        lines.append(f"- {m}")
    return "\n".join(lines)


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
        explanation = _explain_output(proc.stdout or "")
        error_msg = "Metamath verification failed\n"
        error_msg += f"cmd:      {full_cmd}\n"
        error_msg += f"return:   {proc.returncode}\n"
        error_msg += "output:\n"
        error_msg += proc.stdout or ""
        if explanation:
            error_msg += f"\n{explanation}"

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
