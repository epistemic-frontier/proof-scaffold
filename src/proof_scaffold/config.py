from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
                     import proof_scaffold.verifier
                     mmverify_path = Path(proof_scaffold.verifier.__file__).parent / "mmverify.py"
                     res.append((name, [sys.executable, str(mmverify_path)]))
                continue
            
            res.append((name, self.get_verifier_command(name)))
            
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
                        config_data.setdefault("verifiers", {}).update(data["verifiers"])
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
                    command=v_data["command"],
                    args=v_data.get("args", [])
                )

    # Ensure mmverify is always available in definitions if not active
    if "mmverify" not in verifiers:
        import sys
        # Resolve absolute path to mmverify.py inside the package
        import proof_scaffold.verifier
        mmverify_path = Path(proof_scaffold.verifier.__file__).parent / "mmverify.py"
        
        verifiers["mmverify"] = VerifierConfig(
            command=sys.executable,
            args=[str(mmverify_path)]
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
        lines.append(f'command = {repr(v.command)}')
        if v.args:
            args_str = ", ".join(repr(a) for a in v.args)
            lines.append(f"args = [{args_str}]")
            
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

