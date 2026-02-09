import re

import pytest

from skfd.core.diag import LinkerDiagError
from skfd.names import Lexicon, LexiconConflictError, LexiconEntry, NameResolver


def test_name_resolver_builtin_mappings_records_usage() -> None:
    r = NameResolver()
    assert r.canonicalize("Var", "φ") == "ph"
    assert r.canonicalize("Const", "→") == "->"

    obj = r.used_mappings()
    assert obj["format"] == "skfd-names-v1"
    used = {(x["kind"], x["alias"], x["canonical"]) for x in obj["used"]}
    assert ("Var", "φ", "ph") in used
    assert ("Const", "→", "->") in used

    display = {(x["kind"], x["canonical"], x["display"]) for x in obj["display"]}
    assert ("Var", "ph", "φ") in display
    assert ("Const", "->", "→") in display


def test_name_resolver_unknown_unicode_alias_raises() -> None:
    r = NameResolver()
    with pytest.raises(LinkerDiagError) as e:
        r.canonicalize("Const", "∴")
    assert e.value.diag.error_code == "E_UNKNOWN_UNICODE_ALIAS"


def test_lexicon_conflict_raises() -> None:
    lex = Lexicon()
    lex.add(LexiconEntry(kind="Const", canonical="->", aliases=("→",), display="→"))
    with pytest.raises(LexiconConflictError) as e:
        lex.add(LexiconEntry(kind="Const", canonical="-.", aliases=("→",), display="¬"))
    assert e.value.diag.error_code == "E_LEXICON_CONFLICT"


def test_label_canonicalization_is_stable() -> None:
    r = NameResolver()
    c1 = r.canonicalize("Label", "中文")
    c2 = r.canonicalize("Label", "中文")
    assert c1 == c2
    assert re.fullmatch(r"u_[a-z0-9]{10}", c1)

