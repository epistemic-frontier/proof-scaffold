from __future__ import annotations

import re
from dataclasses import dataclass


_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/#-]*\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True, order=True, slots=True)
class _Id:
    value: str

    def __post_init__(self) -> None:
        if not _ID.fullmatch(self.value):
            raise ValueError(f"invalid canonical ASCII {type(self).__name__}: {self.value!r}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True, slots=True)
class SortId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class VariableKindId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class ConstructorId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class LanguageId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class NotationId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class BackendBindingId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class BackendVocabularyId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class AssertionSemanticId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class AssertionCatalogId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class AssertionProfileId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class JudgmentKindId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class RuleId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class CalculusId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class FoundationId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class OwnerId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class ProofId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class StepId(_Id):
    pass


@dataclass(frozen=True, order=True, slots=True)
class Digest:
    value: str

    def __post_init__(self) -> None:
        if not _DIGEST.fullmatch(self.value):
            raise ValueError(f"invalid SHA256 digest: {self.value!r}")

    def __str__(self) -> str:
        return self.value
