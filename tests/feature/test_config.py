from __future__ import annotations

from pathlib import Path

from skfd.config import SkfdConfig, VerifierConfig, load_config, save_config


def test_save_and_load_config(tmp_path: Path) -> None:
    cfg = SkfdConfig(
        verifiers={"v1": VerifierConfig(command="/bin/echo", args=["ok"])},
        active_verifiers=["v1"],
    )
    save_config(cfg, root=tmp_path)

    loaded = load_config(tmp_path)
    assert "v1" in loaded.verifiers
    assert "v1" in loaded.active_verifiers
