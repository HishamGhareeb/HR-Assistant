# Bahrain payroll rule-pack contribution rules

The Bahrain payroll rule pack must be deterministic and citation-backed. Do
not add statutory numbers from memory, from an LLM answer, or from an
uncited website summary.

## Required convention

1. Put Bahrain payroll rule code under `glue/bahrain_payroll/rules`.
2. Put statutory rates, thresholds, caps, deadlines, day/month counts, fund
   names, and penalty multipliers in `glue/bahrain_payroll/statutory_values.py`.
3. Wrap every statutory number in `StatutoryValue(...)` with a
   `StatutoryCitation(...)` that points back to
   `docs/BAHRAIN_PAYROLL_SOURCES.md`.
4. If a number is purely computational and not statutory, keep it rare and add
   an inline marker: `# NON_STATUTORY_NUMBER: <reason>`.

Example:

```python
EOSB_FIRST_THREE_YEARS_RATE = StatutoryValue(
    name="eosb_first_three_years_rate",
    value=4.2,
    unit="percent",
    citation=StatutoryCitation(
        section="§2a",
        instrument="Decision No. (109) of 2023",
        retrieved="2026-08-02",
        quote="4.2% / 8.4% contribution rates",
    ),
)
```

## CI enforcement

`tests/test_bahrain_citation_guard.py` scans the Bahrain rule-pack paths and
fails if:

- a numeric literal appears in rule-pack code without citation wrapping or an
  explicit non-statutory marker;
- a `StatutoryValue` is missing `StatutoryCitation`;
- the citation section, legal instrument, or quote no longer appears in
  `docs/BAHRAIN_PAYROLL_SOURCES.md`.

This is intentional. Payroll and labor-law calculations affect money,
compliance, and liability, so source drift must fail in CI rather than rely on
review memory.

## Explicit exclusions

Before adding country-law edge cases, check
`docs/BAHRAIN_RULE_PACK_SCOPE.md`. Flexi Permit / flexible-worker logic and Law
No. (68) of 2006 GCC social-insurance-protection logic are deliberately excluded
from the current Bahrain rule-pack gate until official full-text sources are
available.
