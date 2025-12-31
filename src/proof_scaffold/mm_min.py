# proof_scaffold/mm_min.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class MMMinDB:
    f_label_of_var: dict[str, str]      # var -> $f label (e.g., ph -> wph)
    f_order: list[str]                  # vars in $f declaration order
    assertion_stmt: dict[str, list[str]]  # label -> statement tokens (including '|-' etc.)


def _strip_comments(text: str) -> str:
    """
    Remove Metamath comments: $( ... $)
    Very small, non-nested remover (sufficient for mini.mm / early stage).
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        if i + 1 < n and text[i] == "$" and text[i + 1] == "(":
            j = text.find("$)", i + 2)
            if j == -1:
                raise ValueError("Unterminated comment $( ... $)")
            i = j + 2
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def _tokenize(text: str) -> list[str]:
    # Metamath tokens are whitespace-separated once comments are removed
    return _strip_comments(text).split()


def load_mm_min(path: Path) -> MMMinDB:
    toks = _tokenize(path.read_text(encoding="utf-8"))
    i = 0

    f_label_of_var: dict[str, str] = {}
    f_order: list[str] = []
    assertion_stmt: dict[str, list[str]] = {}

    pending_label: str | None = None

    def read_until_dollar_dot(start: int) -> tuple[list[str], int]:
        j = start
        stat: list[str] = []
        while True:
            if j >= len(toks):
                raise ValueError("EOF before $.")
            if toks[j] == "$.":
                return stat, j + 1
            stat.append(toks[j])
            j += 1

    while i < len(toks):
        tok = toks[i]
        i += 1

        if tok.startswith("$"):
            # directives
            if tok in ("$c", "$v"):
                stat, i = read_until_dollar_dot(i)
                # we don't need to store $c/$v in this minimal DB
                continue

            if tok == "$f":
                # format: <type> <var> $.  BUT note: label comes before $f
                if not pending_label:
                    raise ValueError("$f must have a label")
                stat, i = read_until_dollar_dot(i)
                if len(stat) != 2:
                    raise ValueError("$f must have length 2: <type> <var>")
                _, var = stat[0], stat[1]
                # record var -> $f label
                f_label_of_var[var] = pending_label
                if var not in f_order:
                    f_order.append(var)
                pending_label = None
                continue

            if tok in ("$a", "$p"):
                if not pending_label:
                    raise ValueError(f"{tok} must have a label")
                stat, i = read_until_dollar_dot(i)

                # for $p, statement includes "$=" and proof after it. We only need the part before $=
                if tok == "$p":
                    if "$=" not in stat:
                        raise ValueError("$p must contain proof after $=")
                    cut = stat.index("$=")
                    stat = stat[:cut]

                assertion_stmt[pending_label] = stat
                pending_label = None
                continue

            if tok in ("$e", "$d", "${", "$}"):
                # ignore in minimal version
                # For $e, you'd store hypothesis statements to compute mand vars more precisely; later.
                if tok == "$e":
                    # consume statement
                    if not pending_label:
                        raise ValueError("$e must have a label")
                    _, i = read_until_dollar_dot(i)
                    pending_label = None
                continue

            # any other $... ignored for now
            continue

        else:
            # ordinary token: may be a label if next token is a directive
            pending_label = tok

    return MMMinDB(
        f_label_of_var=f_label_of_var,
        f_order=f_order,
        assertion_stmt=assertion_stmt,
    )


def required_f_labels(db: MMMinDB, assertion_label: str) -> list[str]:
    """
    Compute mandatory $f labels needed before using assertion_label in a proof.

    Minimal rule (good enough for mini.mm / early stage):
    - Find variables in the assertion statement that have a $f declaration.
    - Return their $f labels in declaration order.
    """
    if assertion_label not in db.assertion_stmt:
        raise KeyError(f"Assertion not found: {assertion_label}")

    stmt = db.assertion_stmt[assertion_label]
    vars_used = {t for t in stmt if t in db.f_label_of_var}

    labels: list[str] = []
    for v in db.f_order:
        if v in vars_used:
            labels.append(db.f_label_of_var[v])
    return labels
