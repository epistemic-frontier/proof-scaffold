# skfd/config.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
from typing import Any

import tomllib


@dataclass
class VerifierConfig:
    command: str
    args: list[str] = field(default_factory=list)


@dataclass
class SkfdConfig:
    verifiers: dict[str, VerifierConfig] = field(default_factory=dict)
    active_verifiers: list[str] = field(default_factory=list)

    def get_verifier_command(self, name: str) -> list[str]:
        """Resolve the command for a specific named verifier."""
        if name not in self.verifiers:
            # Fallback/Error case
            return []
        vc = self.verifiers[name]
        return [vc.command, *vc.args]

    def get_active_commands(self) -> list[tuple[str, list[str]]]:
        """Get list of (name, command) for all active verifiers."""
        def _command_exists(cmd: str) -> bool:
            p = Path(cmd)
            if p.is_absolute():
                return p.exists()
            return shutil.which(cmd) is not None

        def _should_skip(name: str, cmd: list[str]) -> bool:
            if not cmd:
                return True
            if not _command_exists(cmd[0]):
                return True

            if name == "metamath":
                for a in cmd[1:]:
                    if a.startswith("METAMATH_BIN="):
                        bin_path = a.split("=", 1)[1]
                        if bin_path and not Path(bin_path).exists():
                            return True
            return False

        res = []
        # If no active verifiers, fallback to mmverify if available, or just mmverify default
        candidates = self.active_verifiers
        if not candidates:
            candidates = ["mmverify"]

        for name in candidates:
            # Ensure we have the config for it
            if name not in self.verifiers:
                # If it's the builtin/default fallback
                if name == "mmverify":
                    import sys

                    import skfd.verifier

                    mmverify_path = Path(skfd.verifier.__file__).parent / "mmverify.py"
                    cmd = [sys.executable, str(mmverify_path)]
                    if not _should_skip(name, cmd):
                        res.append((name, cmd))
                continue

            cmd = self.get_verifier_command(name)
            if _should_skip(name, cmd):
                continue
            res.append((name, cmd))

        return res


def load_config(root: Path | None = None) -> SkfdConfig:
    """Load configuration from .skfd files."""
    if root is None:
        root = Path.cwd()

    candidates = [
        Path.home() / ".skfd",
        root / ".skfd",
    ]

    config_data: dict[str, Any] = {}

    for path in candidates:
        if path.exists():
            try:
                with open(path, "rb") as f:
                    data = tomllib.load(f)
                    if "verifiers" in data:
                        config_data.setdefault("verifiers", {}).update(
                            data["verifiers"]
                        )
                    # Support new 'active' list
                    if "active" in data:
                        config_data["active"] = data["active"]
                    # Backward compat for 'default'
                    elif "default" in data:
                        config_data["active"] = [data["default"]]
            except Exception as e:
                print(f"Warning: Failed to parse {path}: {e}")

    verifiers = {}
    raw_verifiers = config_data.get("verifiers", {})
    if isinstance(raw_verifiers, dict):
        for name, v_data in raw_verifiers.items():
            if isinstance(v_data, dict) and "command" in v_data:
                verifiers[name] = VerifierConfig(
                    command=v_data["command"], args=v_data.get("args", [])
                )

    # Ensure mmverify is always available in definitions if not active
    if "mmverify" not in verifiers:
        import sys

        # Resolve absolute path to mmverify.py inside the package
        import skfd.verifier

        mmverify_path = Path(skfd.verifier.__file__).parent / "mmverify.py"

        verifiers["mmverify"] = VerifierConfig(
            command=sys.executable, args=[str(mmverify_path)]
        )

    active = config_data.get("active")
    if not active:
        # Default to mmverify if nothing specified
        active = ["mmverify"]

    return SkfdConfig(
        verifiers=verifiers,
        active_verifiers=active,
    )


def save_config(config: SkfdConfig, root: Path | None = None) -> None:
    """Save configuration to project .skfd."""
    if root is None:
        root = Path.cwd()

    path = root / ".skfd"

    lines = []

    # Save active list
    # Use repr to get ['a', 'b'] format which is valid TOML for strings
    lines.append(f"active = {repr(config.active_verifiers)}")

    lines.append("")
    lines.append("[verifiers]")

    for name, v in config.verifiers.items():
        if name == "mmverify":
            # Implementation detail: don't verify built-in unless overridden
            pass

        lines.append(f"\n[verifiers.{name}]")
        lines.append(f"command = {repr(v.command)}")
        if v.args:
            args_str = ", ".join(repr(a) for a in v.args)
            lines.append(f"args = [{args_str}]")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
