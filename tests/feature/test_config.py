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


def test_get_active_commands_skips_missing_executables(tmp_path: Path) -> None:
    cfg = SkfdConfig(
        verifiers={
            "missing": VerifierConfig(command="/no/such/binary", args=[]),
            "mmverify": VerifierConfig(command="/no/such/python", args=["x"]),
        },
        active_verifiers=["missing", "mmverify"],
    )
    save_config(cfg, root=tmp_path)
    loaded = load_config(tmp_path)
    active = loaded.get_active_commands()
    assert active == []


def test_get_active_commands_skips_missing_metamath_bin(tmp_path: Path) -> None:
    cfg = SkfdConfig(
        verifiers={
            "metamath": VerifierConfig(
                command="env",
                args=[
                    "METAMATH_BIN=/no/such/metamath",
                    "/bin/echo",
                    "shim.py",
                ],
            ),
        },
        active_verifiers=["metamath"],
    )
    save_config(cfg, root=tmp_path)
    loaded = load_config(tmp_path)
    assert loaded.get_active_commands() == []
