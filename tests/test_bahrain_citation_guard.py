from pathlib import Path

from glue.bahrain_payroll.citation_guard import validate_rule_pack_citations


def test_current_bahrain_rule_pack_has_no_uncited_statutory_numbers() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    violations = validate_rule_pack_citations(repo_root)

    assert violations == []


def test_uncited_numeric_literal_fails(tmp_path: Path) -> None:
    source_doc = tmp_path / "BAHRAIN_PAYROLL_SOURCES.md"
    source_doc.write_text(
        "## 2a\nDecision No. (109) of 2023\n4.2% / 8.4% contribution rates\n",
        encoding="utf-8",
    )
    rule_file = tmp_path / "rules.py"
    rule_file.write_text("EOSB_RATE = 4.2\n", encoding="utf-8")

    violations = validate_rule_pack_citations(
        repo_root=tmp_path,
        paths=[rule_file],
        source_doc=source_doc,
    )

    assert len(violations) == 1
    assert "numeric literal" in violations[0].message


def test_statutory_value_with_live_source_reference_passes(tmp_path: Path) -> None:
    source_doc = tmp_path / "BAHRAIN_PAYROLL_SOURCES.md"
    source_doc.write_text(
        "## 2a\nDecision No. (109) of 2023\n4.2% / 8.4% contribution rates\n",
        encoding="utf-8",
    )
    rule_file = tmp_path / "statutory_values.py"
    rule_file.write_text(
        "\n".join(
            [
                "from glue.bahrain_payroll.citation_guard import StatutoryCitation, StatutoryValue",
                "EOSB_RATE = StatutoryValue(",
                "    name='eosb_rate',",
                "    value=4.2,",
                "    unit='percent',",
                "    citation=StatutoryCitation(",
                "        section='§2a',",
                "        instrument='Decision No. (109) of 2023',",
                "        retrieved='2026-08-02',",
                "        quote='4.2% / 8.4% contribution rates',",
                "    ),",
                ")",
            ]
        ),
        encoding="utf-8",
    )

    violations = validate_rule_pack_citations(
        repo_root=tmp_path,
        paths=[rule_file],
        source_doc=source_doc,
    )

    assert violations == []


def test_stale_source_reference_fails(tmp_path: Path) -> None:
    source_doc = tmp_path / "BAHRAIN_PAYROLL_SOURCES.md"
    source_doc.write_text("## 8\nReady table only\n", encoding="utf-8")
    rule_file = tmp_path / "statutory_values.py"
    rule_file.write_text(
        "\n".join(
            [
                "from glue.bahrain_payroll.citation_guard import StatutoryCitation, StatutoryValue",
                "EOSB_RATE = StatutoryValue(",
                "    name='eosb_rate',",
                "    value=4.2,",
                "    citation=StatutoryCitation(",
                "        section='§2a',",
                "        instrument='Decision No. (109) of 2023',",
                "        retrieved='2026-08-02',",
                "    ),",
                ")",
            ]
        ),
        encoding="utf-8",
    )

    violations = validate_rule_pack_citations(
        repo_root=tmp_path,
        paths=[rule_file],
        source_doc=source_doc,
    )

    assert {violation.message for violation in violations} == {
        "citation section '§2a' was not found in docs/BAHRAIN_PAYROLL_SOURCES.md",
        "citation instrument 'Decision No. (109) of 2023' was not found in docs/BAHRAIN_PAYROLL_SOURCES.md",
    }

