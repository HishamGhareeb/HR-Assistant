"""Citation-integrity guardrails for Bahrain payroll rule-pack code.

The rule-pack is allowed to be deterministic. It is not allowed to invent or
remember statutory numbers. Every statutory value must point back to the
official-source inventory in ``docs/BAHRAIN_PAYROLL_SOURCES.md``.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


SOURCE_DOC_TEXT = "docs/BAHRAIN_PAYROLL_SOURCES.md"
SOURCE_DOC = Path(SOURCE_DOC_TEXT)
STATUTORY_VALUE_CLASS = "StatutoryValue"
STATUTORY_CITATION_CLASS = "StatutoryCitation"
NON_STATUTORY_MARKER = "NON_STATUTORY_NUMBER:"


@dataclass(frozen=True)
class StatutoryCitation:
    """Traceability metadata for one payroll/legal constant."""

    section: str
    instrument: str
    retrieved: str
    source_doc: str = SOURCE_DOC_TEXT
    quote: str | None = None


@dataclass(frozen=True)
class StatutoryValue:
    """A numeric statutory parameter with its official-source citation."""

    name: str
    value: int | float | str
    citation: StatutoryCitation
    unit: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class CitationGuardViolation:
    """One CI-actionable citation violation."""

    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def default_rule_pack_paths(repo_root: Path) -> list[Path]:
    """Return the Bahrain payroll files that should be citation-scanned.

    Future payroll implementation tickets should place deterministic rule code
    under ``glue/bahrain_payroll/rules`` and statutory constants in
    ``glue/bahrain_payroll/statutory_values.py``. Missing paths are ignored so
    this guard can land before the rule pack itself.
    """

    return [
        repo_root / "glue" / "bahrain_payroll" / "statutory_values.py",
        repo_root / "glue" / "bahrain_payroll" / "rules",
    ]


def validate_rule_pack_citations(
    repo_root: Path,
    paths: Sequence[Path] | None = None,
    source_doc: Path | None = None,
) -> list[CitationGuardViolation]:
    """Validate Bahrain payroll code against the official-source inventory."""

    repo_root = repo_root.resolve()
    source_doc = (source_doc or repo_root / SOURCE_DOC).resolve()
    source_text = source_doc.read_text(encoding="utf-8")
    scanned_paths = paths or default_rule_pack_paths(repo_root)

    violations: list[CitationGuardViolation] = []
    for path in _iter_python_files(scanned_paths):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        source_lines = path.read_text(encoding="utf-8").splitlines()
        violations.extend(_find_uncited_numeric_literals(path, tree, source_lines))
        violations.extend(_validate_statutory_value_calls(path, tree, source_text))
    return violations


def _iter_python_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if not path.exists():
            continue
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            yield from sorted(path.rglob("*.py"))


def _find_uncited_numeric_literals(
    path: Path,
    tree: ast.AST,
    source_lines: Sequence[str],
) -> list[CitationGuardViolation]:
    parent_by_child = _parent_map(tree)
    violations: list[CitationGuardViolation] = []
    for node in ast.walk(tree):
        if not _is_numeric_literal(node):
            continue
        if _line_has_non_statutory_marker(node, source_lines):
            continue
        if _is_wrapped_statutory_value(node, parent_by_child):
            continue
        violations.append(
            CitationGuardViolation(
                path=path,
                line=getattr(node, "lineno", 1),
                message=(
                    "numeric literal in Bahrain payroll code must be wrapped "
                    "in StatutoryValue(...) with a StatutoryCitation, or marked "
                    "with NON_STATUTORY_NUMBER: <reason>"
                ),
            )
        )
    return violations


def _validate_statutory_value_calls(
    path: Path,
    tree: ast.AST,
    source_text: str,
) -> list[CitationGuardViolation]:
    violations: list[CitationGuardViolation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node) != STATUTORY_VALUE_CLASS:
            continue
        citation_node = _keyword_value(node, "citation")
        if not isinstance(citation_node, ast.Call) or _call_name(citation_node) != STATUTORY_CITATION_CLASS:
            violations.append(
                CitationGuardViolation(
                    path=path,
                    line=getattr(node, "lineno", 1),
                    message="StatutoryValue must include citation=StatutoryCitation(...)",
                )
            )
            continue
        violations.extend(_validate_citation_call(path, citation_node, source_text))
    return violations


def _validate_citation_call(
    path: Path,
    node: ast.Call,
    source_text: str,
) -> list[CitationGuardViolation]:
    values = {
        name: _literal_string(_keyword_value(node, name))
        for name in ("source_doc", "section", "instrument", "retrieved", "quote")
    }
    line = getattr(node, "lineno", 1)
    violations: list[CitationGuardViolation] = []

    source_doc = values["source_doc"] or SOURCE_DOC_TEXT
    if source_doc != SOURCE_DOC_TEXT:
        violations.append(
            CitationGuardViolation(
                path=path,
                line=line,
                message=f"citation source_doc must be {SOURCE_DOC_TEXT}, got {source_doc!r}",
            )
        )

    for field in ("section", "instrument", "retrieved"):
        if not values[field]:
            violations.append(
                CitationGuardViolation(
                    path=path,
                    line=line,
                    message=f"StatutoryCitation is missing required {field!r}",
                )
            )

    section = values["section"]
    if section and not _section_exists(section, source_text):
        violations.append(
            CitationGuardViolation(
                path=path,
                line=line,
                message=f"citation section {section!r} was not found in {SOURCE_DOC_TEXT}",
            )
        )

    instrument = values["instrument"]
    if instrument and instrument not in source_text:
        violations.append(
            CitationGuardViolation(
                path=path,
                line=line,
                message=f"citation instrument {instrument!r} was not found in {SOURCE_DOC_TEXT}",
            )
        )

    quote = values["quote"]
    if quote and _normalize(quote) not in _normalize(source_text):
        violations.append(
            CitationGuardViolation(
                path=path,
                line=line,
                message=f"citation quote was not found in {SOURCE_DOC_TEXT}",
            )
        )

    return violations


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}


def _is_numeric_literal(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    )


def _line_has_non_statutory_marker(node: ast.AST, source_lines: Sequence[str]) -> bool:
    line_number = getattr(node, "lineno", 1)
    if line_number <= 0 or line_number > len(source_lines):
        return False
    return NON_STATUTORY_MARKER in source_lines[line_number - 1]


def _is_wrapped_statutory_value(
    node: ast.AST,
    parent_by_child: dict[ast.AST, ast.AST],
) -> bool:
    current = node
    while current in parent_by_child:
        current = parent_by_child[current]
        if isinstance(current, ast.Call) and _call_name(current) == STATUTORY_VALUE_CLASS:
            value_node = _keyword_value(current, "value")
            citation_node = _keyword_value(current, "citation")
            return value_node is node and citation_node is not None
    return False


def _keyword_value(node: ast.Call, name: str) -> ast.AST | None:
    for keyword in node.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _section_exists(section: str, source_text: str) -> bool:
    if section in source_text:
        return True
    section_number = section.removeprefix("§")
    return f"## {section_number}" in source_text or f"## {section}" in source_text
