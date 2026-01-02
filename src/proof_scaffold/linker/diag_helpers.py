from __future__ import annotations

from typing import Any, NoReturn

from ..diag import Diagnostic
from ..ir import Origin
from .errors import LinkerDiagError


def fmt_origin(o: Origin | None) -> str:
    if o is None:
        return "<unknown origin>"
    parts: list[str] = []
    if getattr(o, "module", None):
        parts.append(str(o.module))
    if getattr(o, "file", None):
        parts.append(str(o.file))
    if getattr(o, "line", None) is not None:
        parts.append(str(o.line))
    return ":".join(parts) if parts else "<unknown origin>"


def mk_diag(
    code: str,
    message: str,
    primary: Origin | None,
    *,
    related: tuple[Origin | None, ...] | None = None,
    chain: tuple[str, ...] | None = None,
    details: dict[str, Any] | None = None,
) -> Diagnostic:
    return Diagnostic(
        error_code=code,  # type: ignore[arg-type]
        message=message,
        primary_origin=primary,
        related_origins=tuple(related or ()),
        origin_chain=tuple(chain or ()),
        details=dict(details or {}),
    )


def raise_link_error(
    code: str,
    message: str,
    *,
    primary: Origin | None,
    related: tuple[Origin | None, ...] | None = None,
    chain: tuple[str, ...] | None = None,
    details: dict[str, Any] | None = None,
) -> NoReturn:
    raise LinkerDiagError(
        mk_diag(code, message, primary, related=related, chain=chain, details=details)
    )


def push_chain(diag: Diagnostic, *segs: str) -> Diagnostic:
    return Diagnostic(
        error_code=diag.error_code,
        message=diag.message,
        primary_origin=diag.primary_origin,
        related_origins=diag.related_origins,
        origin_chain=tuple(diag.origin_chain) + tuple(segs),
        details=dict(diag.details),
    )
