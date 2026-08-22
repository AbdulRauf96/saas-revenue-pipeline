# saas-revenue-pipeline

A data pipeline that pulls XBRL financial facts for public SaaS companies from
SEC EDGAR, computes revenue-quality metrics (deferred revenue, RPO, implied
billings), and stores them in DuckDB.

**Status:** in development. Ingestion working; parsing and metrics in progress.

## Why

Deferred revenue and remaining performance obligations are where ASC 606 revenue
recognition becomes visible in public filings. Together they say more about the
durability of a SaaS company's revenue than the headline growth rate does.

## Running locally

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python -m saas_revenue_pipeline.fetch
uv run pytest
```

## Data source

SEC EDGAR XBRL company facts API. No authentication required; the SEC requires a
descriptive `User-Agent` header identifying the requester.

## Known limitations

- Implied billings is distorted by acquisitions and foreign exchange movements
- Companies changed XBRL tags on ASC 606 adoption (2018–19); the parser handles
  the migration but the older history is less consistent
- Fiscal years vary by company; all aggregation is on period end date, never on
  the reported fiscal year label
