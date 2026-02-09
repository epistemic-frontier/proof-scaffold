from __future__ import annotations

import pytest

from skfd.globals import DepsProxy, MMProxy, reset_context, set_context


class DummyMM:
    def __init__(self) -> None:
        self.value = 42


def test_mmproxy_context() -> None:
    mm = DummyMM()
    tokens = set_context(mm, {})
    try:
        proxy = MMProxy()
        assert proxy.value == 42
    finally:
        reset_context(tokens)

    with pytest.raises(RuntimeError):
        _ = MMProxy().value


def test_depsproxy_context() -> None:
    tokens = set_context(DummyMM(), {"x": 1})
    try:
        proxy = DepsProxy()
        assert proxy.x == 1
    finally:
        reset_context(tokens)

    with pytest.raises(RuntimeError):
        _ = DepsProxy().x

    tokens = set_context(DummyMM(), {"x": 1})
    try:
        proxy = DepsProxy()
        with pytest.raises(AttributeError):
            _ = proxy.y
    finally:
        reset_context(tokens)

    class Obj:
        z = 3

    tokens = set_context(DummyMM(), Obj())
    try:
        proxy = DepsProxy()
        assert proxy.z == 3
    finally:
        reset_context(tokens)
