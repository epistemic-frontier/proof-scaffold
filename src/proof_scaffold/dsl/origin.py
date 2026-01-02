# proof_scaffold/dsl/origin.py
from __future__ import annotations

import inspect
from dataclasses import dataclass

from ..ir import Origin


class OriginProvider:
    def here(self, *, depth: int = 2) -> Origin:
        raise NotImplementedError


class InspectOriginProvider(OriginProvider):
    def here(self, *, depth: int = 2) -> Origin:
        try:
            frame = inspect.stack()[depth]
        except Exception:
            frame = inspect.stack()[1]
        mod = frame.frame.f_globals.get("__name__")
        file = frame.filename
        line = frame.lineno
        return Origin(module=mod, file=file, line=line)


class NullOriginProvider(OriginProvider):
    def here(self, *, depth: int = 2) -> Origin:
        return Origin(module=None, file=None, line=None)


@dataclass(frozen=True)
class ExplicitOriginProvider(OriginProvider):
    origin: Origin

    def here(self, *, depth: int = 2) -> Origin:  # depth ignored
        return self.origin
