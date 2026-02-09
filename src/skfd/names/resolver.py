from __future__ import annotations

import base64
import hashlib
import re

from skfd.core.diag import Diagnostic, LinkerDiagError
from skfd.core.symbols import SymbolKind

from .lexicon import Lexicon, builtin_lexicon


_LABEL_CANONICAL_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _is_ascii(text: str) -> bool:
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _stable_hash(text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).digest()
    return base64.b32encode(digest).decode("ascii").lower().rstrip("=")


class NameResolver:
    def __init__(self, lexicon: Lexicon | None = None) -> None:
        self._lexicon = lexicon if lexicon is not None else builtin_lexicon()
        self._used: set[tuple[SymbolKind, str, str]] = set()

    def canonicalize(self, kind: SymbolKind, name: str) -> str:
        mapped = self._lexicon.canonical_for(kind, name)
        if mapped is not None:
            if name != mapped:
                self.record_use(kind, name, mapped)
            return mapped

        if kind == "Label":
            if _LABEL_CANONICAL_RE.fullmatch(name) and _is_ascii(name):
                return name
            canonical = f"u_{_stable_hash(name)[:10]}"
            self.record_use(kind, name, canonical)
            return canonical

        if _is_ascii(name):
            if any(ch.isspace() for ch in name):
                raise LinkerDiagError(
                    Diagnostic(
                        error_code="E_BAD_SYMBOL_NAME",
                        message="symbol name must not contain whitespace",
                        primary_origin_ref=-1,
                        related_origin_refs=(),
                        origin_chain=(),
                        details={"kind": kind, "name": name},
                    )
                )
            return name

        raise LinkerDiagError(
            Diagnostic(
                error_code="E_UNKNOWN_UNICODE_ALIAS",
                message="unicode/alias symbol must be mapped by lexicon",
                primary_origin_ref=-1,
                related_origin_refs=(),
                origin_chain=(),
                details={"kind": kind, "alias": name},
            )
        )

    def display(self, kind: SymbolKind, canonical: str) -> str | None:
        return self._lexicon.display_for(kind, canonical)

    def record_use(self, kind: SymbolKind, alias: str, canonical: str) -> None:
        self._used.add((kind, alias, canonical))

    def used_mappings(self) -> dict:
        used_items = [
            {"kind": k, "alias": a, "canonical": c}
            for (k, a, c) in sorted(self._used, key=lambda t: (t[0], t[1], t[2]))
        ]
        display_items = [
            {"kind": k, "canonical": c, "display": d}
            for (k, c, d) in self._lexicon.display_items()
        ]
        return {"format": "skfd-names-v1", "used": used_items, "display": display_items}

