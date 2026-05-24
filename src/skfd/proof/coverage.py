from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from skfd.core.symbols import SymbolDef
from skfd.core.unit import ProofUnitIR


@dataclass(frozen=True)
class ProofCoverageDeclaration:
    name: str
    labels: tuple[str, ...]
    require_verified: bool
    source: str


@dataclass(frozen=True)
class ProofCoverageReport:
    unit_id: str
    declarations: tuple[ProofCoverageDeclaration, ...]
    emitted_labels: tuple[str, ...]
    declared_labels: tuple[str, ...]
    declared_but_unemitted: tuple[str, ...]
    missing_required_labels: tuple[str, ...]

    @property
    def has_declarations(self) -> bool:
        return bool(self.declarations)

    @property
    def all_declared_emitted(self) -> bool:
        return not self.declared_but_unemitted

    @property
    def ok(self) -> bool:
        return not self.missing_required_labels

    def render(self) -> str:
        if not self.has_declarations:
            return (
                f"Proof coverage ({self.unit_id}): no declared proof surface; "
                "coverage is limited to the emitted monolith."
            )

        lines = [
            (
                f"Proof coverage ({self.unit_id}): "
                f"{len(self.declared_labels)} declared, "
                f"{len(self.emitted_labels)} emitted, "
                f"{len(self.declared_but_unemitted)} declared-but-unemitted."
            )
        ]
        if self.declared_but_unemitted:
            lines.append(
                "  declared-but-unemitted: "
                + ", ".join(self.declared_but_unemitted)
            )
        if self.missing_required_labels:
            lines.append(
                "  missing required labels: "
                + ", ".join(self.missing_required_labels)
            )
        return "\n".join(lines)


class ProofCoverageError(ValueError):
    def __init__(self, report: ProofCoverageReport) -> None:
        self.report = report
        super().__init__(report.render())


class ProofCoverage:
    def __init__(self) -> None:
        self._declarations: list[ProofCoverageDeclaration] = []
        self._require_all_declared_verified = False

    @property
    def declarations(self) -> tuple[ProofCoverageDeclaration, ...]:
        return tuple(self._declarations)

    def declare_labels(
        self,
        name: str,
        labels: Iterable[str],
        *,
        require_verified: bool = False,
    ) -> None:
        label_tuple = tuple(sorted(set(labels)))
        self._declarations.append(
            ProofCoverageDeclaration(
                name=name,
                labels=label_tuple,
                require_verified=require_verified,
                source="labels",
            )
        )

    def declare_registry(
        self,
        name: str,
        constructors: Mapping[str, object],
        *,
        require_verified: bool = False,
    ) -> None:
        label_tuple = tuple(sorted(constructors))
        self._declarations.append(
            ProofCoverageDeclaration(
                name=name,
                labels=label_tuple,
                require_verified=require_verified,
                source="registry",
            )
        )

    def require_all_declared_verified(self) -> None:
        self._require_all_declared_verified = True

    def required_labels(self) -> set[str]:
        if self._require_all_declared_verified:
            return self.declared_labels()

        labels: set[str] = set()
        for decl in self._declarations:
            if decl.require_verified:
                labels.update(decl.labels)
        return labels

    def declared_labels(self) -> set[str]:
        labels: set[str] = set()
        for decl in self._declarations:
            labels.update(decl.labels)
        return labels


def build_proof_coverage_report(
    *,
    unit: ProofUnitIR,
    symtab: Mapping[int, SymbolDef],
    coverage: ProofCoverage,
) -> ProofCoverageReport:
    emitted = _emitted_label_names(unit=unit, symtab=symtab)
    declared = coverage.declared_labels()
    required = coverage.required_labels()

    declared_but_unemitted = tuple(sorted(declared - emitted))
    missing_required = tuple(sorted(required - emitted))

    return ProofCoverageReport(
        unit_id=unit.unit_id,
        declarations=coverage.declarations,
        emitted_labels=tuple(sorted(emitted)),
        declared_labels=tuple(sorted(declared)),
        declared_but_unemitted=declared_but_unemitted,
        missing_required_labels=missing_required,
    )


def _emitted_label_names(
    *,
    unit: ProofUnitIR,
    symtab: Mapping[int, SymbolDef],
) -> set[str]:
    labels: set[str] = set()
    for stmt in unit.lir_stmts:
        label = getattr(stmt, "label", None)
        if not isinstance(label, int):
            continue
        sym = symtab.get(label)
        if sym is not None:
            labels.add(sym.local_name)
    return labels


__all__ = [
    "ProofCoverage",
    "ProofCoverageDeclaration",
    "ProofCoverageError",
    "ProofCoverageReport",
    "build_proof_coverage_report",
]
