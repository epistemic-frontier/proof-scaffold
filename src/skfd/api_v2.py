from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from skfd.builder_v2 import BuildConfig, MMBuilderV2
from skfd.core.symbols import SymbolId
from skfd.names import NameResolver
from skfd.proof.coverage import ProofCoverage


@dataclass(frozen=True)
class UnitMeta:
    dist_name: str
    module_name: str
    build_path: Path | None


class ExportsView(Mapping[str, SymbolId]):
    def __init__(self, mapping: Mapping[str, SymbolId]) -> None:
        self._m = dict(mapping)

    def __getitem__(self, key: str) -> SymbolId:
        return self._m[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._m)

    def __len__(self) -> int:
        return len(self._m)

    def as_dict(self) -> dict[str, SymbolId]:
        return dict(self._m)


class DepsView:
    def __init__(self, *, deps: Mapping[str, ExportsView], metas: Mapping[str, UnitMeta]) -> None:
        self._by_dist = dict(deps)
        self._alias_to_dist: dict[str, str] = {}
        for dist, meta in metas.items():
            self._alias_to_dist[dist] = dist
            self._alias_to_dist[dist.replace("-", "_")] = dist
            self._alias_to_dist[meta.module_name] = dist
            self._alias_to_dist[meta.module_name.replace("-", "_")] = dist

    def __getitem__(self, key: str) -> ExportsView:
        dist = self._alias_to_dist.get(key)
        if dist is None:
            raise KeyError(key)
        return self._by_dist[dist]

    def __getattr__(self, key: str) -> ExportsView:
        try:
            return self[key]
        except KeyError as e:
            raise AttributeError(key) from e


@dataclass(frozen=True)
class BuildContextV2:
    mm: MMBuilderV2
    deps: DepsView
    unit: UnitMeta
    names: NameResolver
    cfg: BuildConfig
    log: logging.Logger
    coverage: ProofCoverage


__all__ = [
    "BuildConfig",
    "BuildContextV2",
    "DepsView",
    "ExportsView",
    "ProofCoverage",
    "UnitMeta",
]
