"""Storage idempotency — the most important test here."""

import json
from pathlib import Path

import pytest

from saas_revenue_pipeline.parse import parse_company_facts
from saas_revenue_pipeline.storage import connect, fact_count, write_facts

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def facts():
    payload = json.loads((FIXTURES / "shop_trimmed.json").read_text(encoding="utf-8"))
    return parse_company_facts(payload)


def test_write_is_idempotent(tmp_path, facts):
    con = connect(tmp_path / "test.duckdb")

    write_facts(con, facts)
    first = fact_count(con)

    write_facts(con, facts)
    write_facts(con, facts)

    assert fact_count(con) == first
    assert first == len(facts)


def test_restatement_overwrites_older_value(tmp_path, facts):
    """A later filing for the same period replaces the earlier value."""
    con = connect(tmp_path / "test.duckdb")
    write_facts(con, facts)

    row = con.execute(
        """
        SELECT value FROM facts
        WHERE concept = 'revenue' AND period_end = DATE '2022-12-31'
        """
    ).fetchone()
    assert row[0] == 5_600_000_000


def test_instant_start_is_null_in_view(tmp_path, facts):
    con = connect(tmp_path / "test.duckdb")
    write_facts(con, facts)

    nulls = con.execute(
        """
        SELECT count(*) FROM facts_clean
        WHERE period_type = 'instant' AND period_start IS NOT NULL
        """
    ).fetchone()[0]
    assert nulls == 0