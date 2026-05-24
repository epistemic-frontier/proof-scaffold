from __future__ import annotations

import pytest

from skfd.authoring.formula import Wff, wff_atom
from skfd.core.symbols import SymbolInterner
from skfd.proof import (
    Proof,
    ProofRegistryValidationError,
    Step,
    assert_valid_proof_registry,
    validate_proof_registry,
)


def _wff() -> Wff:
    interner = SymbolInterner()
    tok = interner.intern(
        origin_module_id="test",
        local_name="ph",
        kind="Var",
        origin_ref=-1,
    )
    return wff_atom(tok)


WFF = _wff()


def _proof(name: str, *refs: str) -> Proof:
    steps = tuple(
        Step(label=f"s{i}", wff=WFF, note="", op="ref", ref=ref)
        for i, ref in enumerate(refs)
    )
    return Proof(name=name, statement=WFF, steps=steps)


def test_validate_proof_registry_accepts_known_refs() -> None:
    result = validate_proof_registry(
        system=object(),
        constructors={"th1": lambda _sys: _proof("th1", "A1", "syntax")},
        axioms={"A1": WFF},
        reserved={"syntax"},
    )

    assert result.ok
    assert set(result.proofs) == {"th1"}


def test_validate_proof_registry_reports_unknown_refs() -> None:
    result = validate_proof_registry(
        system=object(),
        constructors={"th1": lambda _sys: _proof("th1", "missing")},
        axioms={"A1": WFF},
    )

    assert not result.ok
    assert [(i.kind, i.lemma, i.step, i.ref) for i in result.issues] == [
        ("unknown_ref", "th1", "s0", "missing")
    ]


def test_validate_proof_registry_reports_constructor_errors() -> None:
    def bad_ctor(_sys: object) -> Proof:
        raise RuntimeError("boom")

    result = validate_proof_registry(
        system=object(),
        constructors={"bad": bad_ctor},
    )

    assert not result.ok
    assert result.issues[0].kind == "constructor_error"
    assert result.issues[0].lemma == "bad"
    assert "RuntimeError: boom" in result.issues[0].message


def test_validate_proof_registry_reports_dependency_cycles() -> None:
    result = validate_proof_registry(
        system=object(),
        constructors={
            "a": lambda _sys: _proof("a", "b"),
            "b": lambda _sys: _proof("b", "a"),
        },
    )

    assert not result.ok
    assert any(issue.kind == "cycle" for issue in result.issues)


def test_assert_valid_proof_registry_raises_formatted_error() -> None:
    with pytest.raises(ProofRegistryValidationError) as exc_info:
        assert_valid_proof_registry(
            system=object(),
            constructors={"th1": lambda _sys: _proof("th1", "missing")},
        )

    assert "proof registry validation failed" in str(exc_info.value)
    assert "unknown_ref" in str(exc_info.value)
    assert "missing" in str(exc_info.value)
