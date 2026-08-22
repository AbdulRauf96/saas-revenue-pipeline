"""Smoke tests - prove the package is importable under pytest."""


def test_package_imports():
    import saas_revenue_pipeline

    assert saas_revenue_pipeline is not None


def test_fetch_module_imports():
    from saas_revenue_pipeline import fetch

    assert hasattr(fetch, "fetch_company_facts")

