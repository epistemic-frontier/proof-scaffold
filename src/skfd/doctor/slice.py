# skfd/doctor/slice.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SliceReport:
    """A debug slice containing the active context for a statement."""

    label: str
    target_file: str
    line_number: int
    origin_info: str | None

    # Active context
    constants: list[str]
    variables: list[str]
    hypotheses: dict[str, tuple[str, str]]  # label -> (typecode, string_repr)
    disjoints: list[set[str]]

    # The statement itself
    stmt_type: str  # $a or $p
    stmt_expr: list[str]

    def render(self) -> str:
        lines = []
        lines.append(f"=== Slice for theorem '{self.label}' ===")
        if self.origin_info:
            lines.append(f"Defined at: {self.origin_info}")
        lines.append(f"Location: {self.target_file}:{self.line_number}")
        lines.append("")

        lines.append(f"Active Constants: {' '.join(sorted(self.constants))}")
        lines.append(f"Active Variables: {' '.join(sorted(self.variables))}")
        lines.append("")

        lines.append("Active Hypotheses ($f/$e):")
        if not self.hypotheses:
            lines.append("  (None)")
        else:
            # Sort by label for stability
            for label, (kind, content) in sorted(self.hypotheses.items()):
                lines.append(f"  {label}: ${kind} {content} $.")
        lines.append("")

        lines.append("Active Disjoints ($d):")
        if not self.disjoints:
            lines.append("  (None)")
        else:
            for group in self.disjoints:
                lines.append(f"  $d {' '.join(sorted(group))} $.")
        lines.append("")

        lines.append(f"Statement ({self.stmt_type}):")
        lines.append(f"  {self.label} ${self.stmt_type} {' '.join(self.stmt_expr)} $.")

        return "\n".join(lines)


class Tokenizer:
    def __init__(self, f: Any) -> None:
        self.f = f
        self.line_num = 0
        self.tokbuf: list[str] = []

    def next(self) -> str | None:
        while not self.tokbuf:
            line = self.f.readline()
            self.line_num += 1
            if not line:
                return None

            # Simple comment stripping: ignore everything after $( until $)
            # Note: This is NOT fully robust for multi-line comments but sufficient for generated files
            # which usually put comments on separate lines or strictly delimited.
            # Actually, generated files from skfd output don't use comments inside statements.
            # But the header might have them.
            # Let's assume generated files are clean for now or implement better skipping if needed.

            self.tokbuf = line.split()
            self.tokbuf.reverse()

        return self.tokbuf.pop()


class MetamathContextParser:
    """
    A lightweight streaming parser that tracks scoping and context.
    """

    def __init__(self, mm_file: Path):
        self.mm_file = mm_file
        self.stack: list[dict[str, Any]] = []
        self._push_scope()

        self.constants: set[str] = set()
        self.variables: set[str] = set()

    def _push_scope(self) -> None:
        self.stack.append(
            {
                "hypotheses": {},  # label -> (kind, content)
                "disjoints": [],  # list of sets
            }
        )

    def _pop_scope(self) -> None:
        if len(self.stack) > 1:
            self.stack.pop()

    def _collect_hypotheses(self) -> dict[str, tuple[str, str]]:
        """Collect all active hypotheses from the stack (bottom-up)."""
        hyps = {}
        for frame in self.stack:
            hyps.update(frame["hypotheses"])
        return hyps

    def _collect_disjoints(self) -> list[set[str]]:
        """Collect all active disjoints from the stack."""
        ds = []
        for frame in self.stack:
            ds.extend(frame["disjoints"])
        return ds

    def scan(self, target_label: str) -> SliceReport | None:
        """Scan the file linearly until target_label is found."""
        with open(self.mm_file, encoding="utf-8") as f:
            toks = Tokenizer(f)

            label = None
            while True:
                tok = toks.next()
                if tok is None:
                    break

                if tok == "$c":
                    self._read_until(toks, "$.", lambda t: self.constants.add(t))
                    label = None
                elif tok == "$v":
                    self._read_until(toks, "$.", lambda t: self.variables.add(t))
                    label = None
                elif tok == "$d":
                    d_group: set[str] = set()
                    self._read_until(toks, "$.", d_group.add)
                    self.stack[-1]["disjoints"].append(d_group)
                    label = None
                elif tok == "${":
                    self._push_scope()
                    label = None
                elif tok == "$}":
                    self._pop_scope()
                    label = None
                elif tok == "$f":
                    content = self._read_stat(toks)
                    if label:
                        self.stack[-1]["hypotheses"][label] = ("f", " ".join(content))
                    label = None
                elif tok == "$e":
                    content = self._read_stat(toks)
                    if label:
                        self.stack[-1]["hypotheses"][label] = ("e", " ".join(content))
                    label = None
                elif tok == "$a":
                    current_line = toks.line_num
                    content = self._read_stat(toks)
                    if label == target_label:
                        assert label is not None
                        return self._build_report(label, "a", content, current_line)
                    label = None
                elif tok == "$p":
                    current_line = toks.line_num
                    # $p ... $= ... $.
                    stmt_content = []
                    t = toks.next()
                    while t and t != "$=":
                        stmt_content.append(t)
                        t = toks.next()

                    if label == target_label:
                        assert label is not None
                        return self._build_report(
                            label, "p", stmt_content, current_line
                        )

                    # Skip proof
                    # For skfd generated files, proofs are simple tokens until $.
                    # But compressed proofs exist ( A B C D Z ...)
                    # We just skip until $.
                    t = toks.next()
                    while t and t != "$.":
                        t = toks.next()
                    label = None
                elif tok.startswith("$"):
                    # Unknown keyword, ignore statement
                    # Be careful if it's a block command
                    label = None
                else:
                    # It's a label
                    label = tok

        return None

    def _build_report(
        self, label: str, kind: str, content: list[str], line: int
    ) -> SliceReport:
        return SliceReport(
            label=label,
            target_file=str(self.mm_file),
            line_number=line,
            origin_info=None,  # Will be filled by caller using SourceMap
            constants=sorted(self.constants),
            variables=sorted(self.variables),
            hypotheses=self._collect_hypotheses(),
            disjoints=self._collect_disjoints(),
            stmt_type=kind,
            stmt_expr=content,
        )

    def _read_stat(self, toks: Tokenizer) -> list[str]:
        """Read tokens until $."""
        res = []
        t = toks.next()
        while t and t != "$.":
            res.append(t)
            t = toks.next()
        return res

    def _read_until(self, toks: Tokenizer, end: str, callback):
        t = toks.next()
        while t and t != end:
            callback(t)
            t = toks.next()


def slice_package(mm_file: Path, map_file: Path | None, label: str) -> SliceReport:
    """Generate a slice report for a specific label in a package."""

    if not mm_file.exists():
        raise RuntimeError(f"Metamath file not found: {mm_file}")

    parser = MetamathContextParser(mm_file)
    report = parser.scan(label)

    if not report:
        raise RuntimeError(f"Label '{label}' not found in {mm_file}")

    # Enrich with Source Map if available
    if map_file and map_file.exists():
        try:
            with open(map_file, encoding="utf-8") as f:
                map_data = json.load(f)

            # Map LINE -> ORIGIN
            line = report.line_number
            origin_ref = None

            # Iterate mappings. Note: Assuming sorted by line or unsorted list
            for entry in map_data.get("mappings", []):
                # Check for exact line match
                # Generated map is precise.
                if entry.get("line") == line:
                    origin_ref = entry.get("origin_ref")
                    break

            if origin_ref is not None:
                origins = map_data.get("origins", [])
                if 0 <= origin_ref < len(origins):
                    orig = origins[origin_ref]
                    f_path = orig.get("file", "??")
                    f_line = orig.get("line", "??")
                    report.origin_info = f"{f_path}:{f_line}"

        except Exception as e:
            report.origin_info = f"(Source Map Error: {e})"

    return report
