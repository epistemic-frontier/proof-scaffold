from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from skfd.core.diag import Diagnostic, LinkerDiagError
from skfd.core.symbols import SymbolKind


class LexiconConflictError(LinkerDiagError):
    pass


def _ensure_ascii(text: str) -> None:
    try:
        text.encode("ascii")
    except UnicodeEncodeError as e:
        raise ValueError(f"expected ASCII, got {text!r}") from e


@dataclass(frozen=True)
class LexiconEntry:
    kind: SymbolKind
    canonical: str
    aliases: tuple[str, ...] = ()
    display: str | None = None


class Lexicon:
    def __init__(self) -> None:
        self._alias_to_canonical: dict[tuple[SymbolKind, str], str] = {}
        self._canonical_to_display: dict[tuple[SymbolKind, str], str] = {}

    def merge(self, entries: Iterable[LexiconEntry]) -> None:
        for e in entries:
            self.add(e)

    def add(self, entry: LexiconEntry) -> None:
        _ensure_ascii(entry.canonical)
        if entry.display is not None:
            if entry.display == "":
                raise ValueError("display must be non-empty when provided")
            existing = self._canonical_to_display.get((entry.kind, entry.canonical))
            if existing is not None and existing != entry.display:
                raise LexiconConflictError(
                    Diagnostic(
                        error_code="E_LEXICON_CONFLICT",
                        message="conflicting display for canonical symbol",
                        primary_origin_ref=-1,
                        related_origin_refs=(),
                        origin_chain=(),
                        details={
                            "kind": entry.kind,
                            "canonical": entry.canonical,
                            "existing_display": existing,
                            "new_display": entry.display,
                        },
                    )
                )
            self._canonical_to_display[(entry.kind, entry.canonical)] = entry.display

        for alias in (entry.canonical, *entry.aliases):
            if alias == "":
                raise ValueError("alias must be non-empty")
            existing = self._alias_to_canonical.get((entry.kind, alias))
            if existing is not None and existing != entry.canonical:
                raise LexiconConflictError(
                    Diagnostic(
                        error_code="E_LEXICON_CONFLICT",
                        message="conflicting canonical mapping for alias",
                        primary_origin_ref=-1,
                        related_origin_refs=(),
                        origin_chain=(),
                        details={
                            "kind": entry.kind,
                            "alias": alias,
                            "existing_canonical": existing,
                            "new_canonical": entry.canonical,
                        },
                    )
                )
            self._alias_to_canonical[(entry.kind, alias)] = entry.canonical

    def canonical_for(self, kind: SymbolKind, alias: str) -> str | None:
        return self._alias_to_canonical.get((kind, alias))

    def display_for(self, kind: SymbolKind, canonical: str) -> str | None:
        return self._canonical_to_display.get((kind, canonical))

    def display_items(self) -> list[tuple[SymbolKind, str, str]]:
        items = [(k, c, d) for (k, c), d in self._canonical_to_display.items()]
        items.sort(key=lambda t: (t[0], t[1], t[2]))
        return items


def builtin_lexicon() -> Lexicon:
    lex = Lexicon()
    lex.merge(
        [
            LexiconEntry(kind="Const", canonical="->", aliases=("→", "⇒"), display="→"),
            LexiconEntry(kind="Const", canonical="-.", aliases=("¬", "~"), display="¬"),
            LexiconEntry(kind="Const", canonical="/\\", aliases=("∧", "&"), display="∧"),
            LexiconEntry(kind="Var", canonical="ph", aliases=("φ",), display="φ"),
            LexiconEntry(kind="Var", canonical="ps", aliases=("ψ",), display="ψ"),
            LexiconEntry(kind="Var", canonical="ch", aliases=("χ",), display="χ"),
            LexiconEntry(kind="Var", canonical="th", aliases=("θ",), display="θ"),
            LexiconEntry(kind="Var", canonical="ta", aliases=("τ",), display="τ"),
        ]
    )
    return lex
