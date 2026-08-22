"""Tests for configuration loading and validation."""

import pytest

from saas_revenue_pipeline.config import Company, load_config


def test_loads_all_companies():
    config = load_config()
    assert len(config.companies) == 20


def test_ciks_are_ten_digit_strings():
    config = load_config()
    for company in config.companies:
        assert len(company.cik) == 10, f"{company.ticker} has a malformed CIK"
        assert company.cik.isdigit()


def test_tickers_are_unique():
    config = load_config()
    tickers = [c.ticker for c in config.companies]
    assert len(tickers) == len(set(tickers))


def test_lookup_is_case_insensitive():
    config = load_config()
    assert config.company("snow").ticker == "SNOW"
    assert config.company("SNOW").name == "Snowflake Inc."


def test_unknown_ticker_raises():
    config = load_config()
    with pytest.raises(KeyError):
        config.company("NOTATICKER")


def test_short_cik_is_rejected():
    """Unquoted YAML strips leading zeros — this must fail loudly."""
    with pytest.raises(ValueError, match="10 digits"):
        Company(ticker="X", cik="1108524", name="X", rpo_available=True)