from __future__ import annotations

import textwrap
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

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
            def __init__(self, label, wff, op='hyp', args=(), ref=None):
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
            return Proof('P1', wff, [Step('s1', wff, op='hyp')])
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


def test_discover_proof_functions_returns_definition_order() -> None:
    module = ModuleType("m")
    exec(
        textwrap.dedent(
            """
            def prove_b():
                return "b"

            def helper():
                return None

            def prove_a():
                return "a"
            """
        ),
        module.__dict__,
    )

    assert [name for name, _ in script_runner._discover_proof_functions(module)] == [
        "prove_b",
        "prove_a",
    ]


def test_get_or_create_system_prefers_module_hooks() -> None:
    module = ModuleType("m")
    module.system = object()
    assert script_runner._get_or_create_system(module) is module.system

    module2 = ModuleType("m2")
    module2.sys = SimpleNamespace(name="system")
    assert script_runner._get_or_create_system(module2) is module2.sys

    module3 = ModuleType("m3")
    module3.sys = script_runner.sys
    module3.build = lambda: "built"
    assert script_runner._get_or_create_system(module3) == "built"

    module4 = ModuleType("m4")
    module4.get_system = lambda: "got"
    assert script_runner._get_or_create_system(module4) == "got"


def test_verify_script_handles_loader_creation_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(script_runner.importlib.util, "spec_from_file_location", lambda *_a, **_k: None)
    assert script_runner.verify_script(tmp_path / "no_suffix", project_root=tmp_path) == 1


def test_verify_script_reports_proof_function_failures(tmp_path: Path) -> None:
    script = tmp_path / "s.py"
    _write(
        script,
        """
        system = object()

        def prove_x():
            raise RuntimeError("proof exploded")
        """,
    )

    assert script_runner.verify_script(script, project_root=tmp_path) == 1


def test_verify_script_requires_returned_proof_objects(tmp_path: Path) -> None:
    script = tmp_path / "s.py"
    _write(
        script,
        """
        system = object()

        def prove_x():
            return None
        """,
    )

    assert script_runner.verify_script(script, project_root=tmp_path) == 1


def test_verify_script_returns_failure_when_verifier_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script = tmp_path / "s.py"
    _write(
        script,
        """
        from types import SimpleNamespace

        system = SimpleNamespace(
            interner=None,
            compile_axioms=lambda: {"mp": object()},
        )

        def prove_x():
            return SimpleNamespace(name="th1", statement=None, steps=())
        """,
    )

    from skfd.core.symbols import SymbolInterner

    class DummySystem:
        def __init__(self) -> None:
            self.interner = SymbolInterner()

        def compile_axioms(self) -> dict[str, object]:
            return {"mp": object()}

    monkeypatch.setattr(script_runner, "_get_or_create_system", lambda _module: DummySystem())
    monkeypatch.setattr(script_runner, "emit_axioms", lambda *_a, **_k: None)
    monkeypatch.setattr(script_runner, "emit_lowered_lemmas", lambda *_a, **_k: None)
    monkeypatch.setattr(
        script_runner.LinkerV1,
        "link",
        lambda **_kwargs: SimpleNamespace(mm_text="$c wff $."),
    )
    monkeypatch.setattr(
        script_runner,
        "load_config",
        lambda _root: SimpleNamespace(get_active_commands=lambda: ["false"]),
    )

    def failed_run_all(_mm_path: Path, _cmds: list[str]) -> list[Any]:
        from skfd.verifier.aggregate import VerifierResult

        return [VerifierResult(name="dummy", passed=False, returncode=1, output="no")]

    monkeypatch.setattr(script_runner, "run_all", failed_run_all)

    assert script_runner.verify_script(script, project_root=tmp_path) == 1
