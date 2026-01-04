from __future__ import annotations

from proof_scaffold.diag import Diagnostic


class LinkerError(Exception):
    """Linker errors (not frozen; allow traceback attachment)."""

    pass


class LinkerDiagError(LinkerError):
    def __init__(self, diag: Diagnostic) -> None:
        # message kept minimal; __str__ provides rich formatting
        super().__init__(f"{diag.error_code}: {diag.message}")
        self.diag = diag

    def __str__(self) -> str:  # include origin hints to satisfy existing tests
        # Defer origin formatting to diag_helpers for consistency
        from proof_scaffold.linker.diag_helpers import fmt_origin

        base = f"{self.diag.error_code}: {self.diag.message}"
        segs: list[str] = []
        if self.diag.primary_origin is not None:
            segs.append(fmt_origin(self.diag.primary_origin))
        for ro in self.diag.related_origins:
            if ro is not None:
                segs.append(fmt_origin(ro))
        if segs:
            return base + " [" + ", ".join(segs) + "]"
        return base
