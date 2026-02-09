from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from skfd.driver import script_runner


def _write(path: Path, text: str) -> None:
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


def test_verify_script_no_proofs(tmp_path: Path) -> None:
    script = tmp_path / "s.py"
    _write(
        script,
        """
        def foo():
            return None
        """,
    )

    assert script_runner.verify_script(script, project_root=tmp_path) == 0


def test_verify_script_exec_error(tmp_path: Path) -> None:
    script = tmp_path / "s.py"
    _write(
        script,
        """
        raise RuntimeError('boom')
        """,
    )

    assert script_runner.verify_script(script, project_root=tmp_path) == 1


def test_verify_script_missing_system(tmp_path: Path) -> None:
    script = tmp_path / "s.py"
    _write(
        script,
        """
        def prove_x():
            return None
        """,
    )

    assert script_runner.verify_script(script, project_root=tmp_path) == 1


def test_verify_script_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = tmp_path / "s.py"
    _write(
        script,
        """
        from types import SimpleNamespace

        class Step:
            def __init__(self, label, wff, op='ref', args=(), ref='wi'):
                self.label = label
                self.wff = wff
                self.op = op
                self.args = args
                self.ref = ref

        class Proof:
            def __init__(self, name, statement, steps):
                self.name = name
                self.statement = statement
                self.steps = steps

        def prove_x(sys):
            # minimal proof object (structure only, contents won't be verified here)
            wff = sys.compile('ph', ctx='t')
            return Proof('P1', wff, [Step('s1', wff)])
        """,
    )

    class DummySystem:
        def __init__(self):
            from skfd.core.symbols import SymbolInterner
            self.interner = SymbolInterner()

        def compile(self, _expr, *, ctx: str):
            # Return a minimal Wff-like object
            ph = self.interner.intern(
                origin_module_id="dummy",
                local_name="ph",
                kind="Var",
                origin_ref=None,
            )
            return type("Wff", (), {"tokens": (ph,), "sort": "wff"})()

        def compile_axioms(self):
            return {}

        @property
        def builtins(self):
            # Provide minimal tokens for emit_lowered_lemmas
            lp = self.interner.intern(
                origin_module_id="dummy",
                local_name="(",
                kind="Const",
                origin_ref=None,
            )
            rp = self.interner.intern(
                origin_module_id="dummy",
                local_name=")",
                kind="Const",
                origin_ref=None,
            )
            imp = self.interner.intern(
                origin_module_id="dummy",
                local_name="->",
                kind="Const",
                origin_ref=None,
            )
            neg = self.interner.intern(
                origin_module_id="dummy",
                local_name="-.",
                kind="Const",
                origin_ref=None,
            )
            and_ = self.interner.intern(
                origin_module_id="dummy",
                local_name="/\\",
                kind="Const",
                origin_ref=None,
            )
            return type("B", (), {"lp": lp, "rp": rp, "imp": imp, "neg": neg, "and_": and_})()

    def _fake_get_system(_module):
        # Monkeypatch parser entry to avoid full parsing
        monkeypatch.setattr(script_runner, "wff", lambda _s: "ph")
        return DummySystem()

    monkeypatch.setattr(script_runner, '_get_or_create_system', _fake_get_system)

    def _fake_run_all(_mm_path, _cmds):
        from skfd.verifier.aggregate import VerifierResult
        return [VerifierResult(name='mmverify', passed=True, returncode=0, output='ok')]

    monkeypatch.setattr(script_runner, 'run_all', _fake_run_all)

    assert script_runner.verify_script(script, project_root=tmp_path) == 0
