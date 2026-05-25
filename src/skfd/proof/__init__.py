from .core import HasTactics, SystemCore, Tactic, TacticRegistry
from .coverage import (
    ProofCoverage,
    ProofCoverageDeclaration,
    ProofCoverageError,
    ProofCoverageReport,
    build_proof_coverage_report,
)
from .ir import Proof, ProofBuilder, Step
from .signature import LemmaSignature, SignatureCache, extract_signature
from .validate import (
    ProofConstructor,
    ProofLike,
    ProofRegistryIssue,
    ProofRegistryValidationError,
    ProofRegistryValidationResult,
    StepLike,
    assert_valid_proof_registry,
    format_proof_registry_issues,
    validate_proof_registry,
)

__all__ = [
    "HasTactics",
    "LemmaSignature",
    "Proof",
    "ProofCoverage",
    "ProofCoverageDeclaration",
    "ProofCoverageError",
    "ProofCoverageReport",
    "ProofBuilder",
    "ProofConstructor",
    "ProofLike",
    "ProofRegistryIssue",
    "ProofRegistryValidationError",
    "ProofRegistryValidationResult",
    "SignatureCache",
    "Step",
    "StepLike",
    "SystemCore",
    "Tactic",
    "TacticRegistry",
    "assert_valid_proof_registry",
    "build_proof_coverage_report",
    "extract_signature",
    "format_proof_registry_issues",
    "validate_proof_registry",
]
