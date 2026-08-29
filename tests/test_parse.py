"""Tests for companyfacts parsing and period resolution.

Cases are taken from the real Shopify fixture, not invented.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from saas_revenue_pipeline.parse import (
    INSTANT_SENTINEL,
    parse_company_facts,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def shop() -> dict:
    return json.loads((FIXTURES / "shop_trimmed.json").read_text(encoding="utf-8"))


@pytest.fixture
def snow() -> dict:
    return json.loads((FIXTURES / "snow_trimmed.json").read_text(encoding="utf-8"))


def _find(facts, concept, end, start=None):
    matches = [
        f
        for f in facts
        if f.concept == concept
        and f.period_end == end
        and (start is None or f.period_start == start)
    ]
    return matches


def test_dedupe_produces_one_row_per_period(shop):
    """FY2021 revenue appears in two filings with identical values."""
    facts = parse_company_facts(shop)
    matches = _find(facts, "revenue", date(2021, 12, 31), date(2021, 1, 1))
    assert len(matches) == 1
    assert matches[0].value == 4_611_856_000


def test_restatement_takes_latest_filed(shop):
    """FY2022 revenue was restated from 5,599,864,000 to 5,600,000,000."""
    facts = parse_company_facts(shop)
    matches = _find(facts, "revenue", date(2022, 12, 31), date(2022, 1, 1))
    assert len(matches) == 1
    assert matches[0].value == 5_600_000_000
    assert matches[0].filed == date(2024, 2, 13)


def test_tag_migration_resolves_to_single_row(shop):
    """FY2023 revenue is reported under two different tags."""
    facts = parse_company_facts(shop)
    matches = _find(facts, "revenue", date(2023, 12, 31), date(2023, 1, 1))
    assert len(matches) == 1
    assert matches[0].value == 7_060_000_000
    # The later filing used the legacy tag name.
    assert matches[0].source_tag == "Revenues"


def test_instant_facts_have_no_real_start(shop):
    facts = parse_company_facts(shop)
    instants = [f for f in facts if f.concept == "deferred_revenue_current"]
    assert instants
    for fact in instants:
        assert fact.period_type == "instant"
        assert fact.period_start == INSTANT_SENTINEL


def test_duration_facts_have_both_dates(shop):
    facts = parse_company_facts(shop)
    durations = [f for f in facts if f.concept == "revenue"]
    assert durations
    for fact in durations:
        assert fact.period_type == "duration"
        assert fact.period_start != INSTANT_SENTINEL
        assert fact.period_start < fact.period_end


def test_missing_concept_yields_no_facts(shop):
    """Shopify does not disclose RPO — absence must not raise."""
    facts = parse_company_facts(shop)
    assert [f for f in facts if f.concept == "rpo"] == []


def test_present_concept_yields_facts(snow):
    """Snowflake does disclose RPO."""
    facts = parse_company_facts(snow)
    assert [f for f in facts if f.concept == "rpo"]


def test_cik_is_zero_padded(shop):
    facts = parse_company_facts(shop)
    assert all(len(f.cik) == 10 for f in facts)