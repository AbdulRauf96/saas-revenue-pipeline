"""Smoke tests - prove the package is importable under pytest."""


def test_package_imports():
    import saas_revenue_pipeline

    assert saas_revenue_pipeline is not None


def test_fetch_module_imports():
    from saas_revenue_pipeline import fetch

    assert hasattr(fetch, "fetch_company_facts")


def test_cik_padding():
    """CIK must be zero-padded to 10 digits or the API returns 404."""
    assert str(1640147).zfill(10) == "0001640147"
