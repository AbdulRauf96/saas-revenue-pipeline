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

def test_missing_deferred_revenue_is_null_not_zero(tmp_path):
    """A company with no deferred revenue fact must yield NULL, not 0."""
    from saas_revenue_pipeline.config import load_config
    from saas_revenue_pipeline.metrics import build_views
    from saas_revenue_pipeline.parse import parse_file

    config = load_config()
    path = config.raw_dir / "CIK0001640147.json"
    if not path.exists():
        pytest.skip("SNOW not cached")

    con = connect(tmp_path / "test.duckdb")
    write_facts(con, parse_file(path))
    build_views(con)

    row = con.execute(
        """
        SELECT deferred_revenue FROM metrics_final
        WHERE cik = '0001640147' AND grain = 'annual'
          AND period_end = DATE '2019-01-31'
        """
    ).fetchone()
    assert row is not None
    assert row[0] is None

def test_metrics_match_reported_revenue(tmp_path):
    """CRM FY2024 revenue was $34.857bn as reported. The pipeline must agree."""
    from saas_revenue_pipeline.config import load_config
    from saas_revenue_pipeline.metrics import build_views
    from saas_revenue_pipeline.parse import parse_file

    config = load_config()
    path = config.raw_dir / "CIK0001108524.json"
    if not path.exists():
        pytest.skip("CRM not cached")

    con = connect(tmp_path / "test.duckdb")
    write_facts(con, parse_file(path))
    build_views(con)

    row = con.execute(
        """
        SELECT revenue FROM metrics_final
        WHERE cik = '0001108524' AND grain = 'annual'
          AND period_end = DATE '2024-01-31'
        """
    ).fetchone()
    assert row is not None
    assert row[0] == 34_857_000_000


def test_no_grain_mixing_in_windows(tmp_path):
    """A quarterly row's prior-year comparison must also be quarterly."""
    from saas_revenue_pipeline.config import load_config
    from saas_revenue_pipeline.metrics import build_views
    from saas_revenue_pipeline.parse import parse_file

    config = load_config()
    path = config.raw_dir / "CIK0001108524.json"
    if not path.exists():
        pytest.skip("CRM not cached")

    con = connect(tmp_path / "test.duckdb")
    write_facts(con, parse_file(path))
    build_views(con)

    # An annual figure is roughly 4x a quarterly one. If a window crossed
    # grains, some yoy value would be wildly out of range.
    bad = con.execute(
        """
        SELECT count(*) FROM metrics_final
        WHERE grain = 'quarterly'
          AND revenue_yoy IS NOT NULL
          AND (revenue_yoy > 5 OR revenue_yoy < -0.9)
        """
    ).fetchone()[0]
    assert bad == 0