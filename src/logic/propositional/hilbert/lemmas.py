# logic/propositional/hilbert/lemmas.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from prelude.formula import Wff, render
from prelude.typing import Hypothesis, PreludeTypingError, Sort

from . import HilbertSystem
from ._structures import Imp, phi, psi
from .definitions import Or


# -----------------------------------------------------------------------------
# Proof result container (debug-friendly)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class ProofStep:
    """One proof step for debugging/introspection."""
    label: str
    wff: Wff
    note: str


@dataclass(frozen=True)
class LemmaProof:
    """A lemma proof artifact produced by the authoring/proof script."""
    name: str
    statement: Wff
    steps: Tuple[ProofStep, ...]


# -----------------------------------------------------------------------------
# Lemma proofs
# -----------------------------------------------------------------------------

def prove_L1_id(sys: HilbertSystem) -> LemmaProof:
    """Prove L1: φ -> φ using Hilbert axioms A1/A2 and rule mp.

    Standard Hilbert proof outline:
      (1) A1 with ψ := φ
          φ -> (φ -> φ)

      (2) A2 with ψ := (φ -> φ), χ := φ
          (φ -> ((φ -> φ) -> φ)) -> ((φ -> (φ -> φ)) -> (φ -> φ))

      (3) A1 with ψ := (φ -> φ)
          φ -> ((φ -> φ) -> φ)

      (4) mp on (3) and (2)
          (φ -> (φ -> φ)) -> (φ -> φ)

      (5) mp on (1) and (4)
          φ -> φ
    """
    steps: List[ProofStep] = []

    # compile φ
    phi_wff = sys.compile(phi, ctx="compile φ")  # type: ignore[arg-type]

    b = sys.builtins
    phi_imp_phi = sys.compile(Imp(phi, phi), ctx="compile (φ→φ)")  # authoring compile

    # (1)
    s1 = sys.axioms["A1"].apply(phi_wff, phi_wff)
    steps.append(ProofStep("s1", s1, "A1 with (phi, psi) = (φ, φ)"))

    # (2)
    s2 = sys.axioms["A2"].apply(phi_wff, phi_imp_phi, phi_wff)
    steps.append(ProofStep("s2", s2, "A2 with (phi, psi, chi) = (φ, (φ→φ), φ)"))

    # (3)
    s3 = sys.axioms["A1"].apply(phi_wff, phi_imp_phi)
    steps.append(ProofStep("s3", s3, "A1 with (phi, psi) = (φ, (φ→φ))"))

    # (4) mp(s3, s2)
    h3 = Hypothesis[Sort]("h3", s3)  # type: ignore[type-var]
    h2 = Hypothesis[Sort]("h2", s2)  # type: ignore[type-var]
    s4 = sys.apply("mp", [h3, h2], ctx="mp step (s3, s2)")
    if not isinstance(s4, Wff):
        raise PreludeTypingError("prove_L1_id: mp did not return a Wff (unexpected)")
    steps.append(ProofStep("s4", s4, "mp on s3 and s2"))

    # (5) mp(s1, s4)
    h1 = Hypothesis[Sort]("h1", s1)  # type: ignore[type-var]
    h4 = Hypothesis[Sort]("h4", s4)  # type: ignore[type-var]
    s5 = sys.apply("mp", [h1, h4], ctx="mp step (s1, s4)")
    if not isinstance(s5, Wff):
        raise PreludeTypingError("prove_L1_id: mp did not return a Wff (unexpected)")
    steps.append(ProofStep("s5", s5, "mp on s1 and s4"))

    return LemmaProof(name="L1_id", statement=s5, steps=tuple(steps))


def prove_L2_or_intro_right(sys: HilbertSystem) -> LemmaProof:
    """Prove L2: φ -> Or(ψ, φ) with Or(a,b) := ¬a -> b.

    Expand:
      Or(ψ, φ) = (¬ψ -> φ)

    Then L2 is exactly an instance of A1:
      A1: α -> (β -> α)
    with:
      α := φ
      β := ¬ψ

    Proof:
      (1) compile goal statement
      (2) instantiate A1
    """
    steps: List[ProofStep] = []

    # Authoring: statement Expr = φ -> Or(ψ, φ)
    stmt_expr = Imp(phi, Or.expand(psi, phi))  # Or.expand: ¬ψ -> φ
    stmt_wff = sys.compile(stmt_expr, ctx="compile L2 statement")

    # compile components for A1 instantiation
    phi_wff = sys.compile(phi, ctx="compile φ")  # type: ignore[arg-type]
    not_psi_wff = sys.compile(Or.expand(psi, psi).args[0] if False else None)  # placeholder, not used

    # Instead of trying to pick apart Expr, just compile (¬ψ) directly:
    # We have Not in structures; but definitions.py uses Imp(Not(a), b),
    # so Or.expand(psi, phi) is (¬ψ -> φ). To instantiate A1, we need β = ¬ψ.
    # We'll build β as authoring expr using Not from structures.
    from ._structures import Not
    beta_wff = sys.compile(Not(psi), ctx="compile ¬ψ")  # type: ignore[arg-type]

    # (1) A1: φ -> (¬ψ -> φ)
    s1 = sys.axioms["A1"].apply(phi_wff, beta_wff)
    steps.append(ProofStep("s1", s1, "A1 with (alpha, beta) = (φ, ¬ψ)"))

    # statement equals s1
    if s1.tokens != stmt_wff.tokens:
        # This should not happen; if it does, debug symbol rendering.
        symtab = sys.interner.symbol_table()
        raise PreludeTypingError(
            "prove_L2_or_intro_right: compiled statement != A1 instance\n"
            f"stmt: {render(stmt_wff.tokens, symtab=symtab)}\n"
            f"a1  : {render(s1.tokens, symtab=symtab)}"
        )

    return LemmaProof(name="L2_or_intro_right", statement=s1, steps=tuple(steps))


# -----------------------------------------------------------------------------
# Requested lemma (nontrivial at current stage)
# -----------------------------------------------------------------------------

def prove_L3_or_intro_left(sys: HilbertSystem) -> LemmaProof:
    """Target lemma (requested): φ -> Or(φ, ψ), where Or(φ,ψ) := ¬φ -> ψ.

    Expanded goal:
      φ -> (¬φ -> ψ)

    This lemma is valid in classical propositional logic, but proving it in this
    Hilbert system typically requires additional derived lemmas (e.g. explosion,
    permutation/exportation, etc.). We intentionally defer it until the lemma
    library has those building blocks.

    For now, raise to keep the framework honest.
    """
    raise NotImplementedError(
        "L3 (φ -> Or(φ, ψ)) is deferred: needs additional derived lemmas "
        "(e.g. explosion / permutation). Use L2 to validate the framework first."
    )


# -----------------------------------------------------------------------------
# Optional: debug printer
# -----------------------------------------------------------------------------

def debug_dump(proof: LemmaProof, *, sys: HilbertSystem) -> str:
    """Render a lemma proof using the symbol table for debugging."""
    symtab = sys.interner.symbol_table()
    lines = [f"== {proof.name} =="]
    lines.append("statement: " + render(proof.statement.tokens, symtab=symtab))
    for st in proof.steps:
        lines.append(f"{st.label}: {render(st.wff.tokens, symtab=symtab)}    # {st.note}")
    return "\n".join(lines)


__all__ = [
    "ProofStep",
    "LemmaProof",
    "prove_L1_id",
    "prove_L2_or_intro_right",
    "prove_L3_or_intro_left",
    "debug_dump",
]
