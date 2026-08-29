# saas-revenue-pipeline

[![Weekly refresh](https://github.com/AbdulRauf96/saas-revenue-pipeline/actions/workflows/refresh.yml/badge.svg)](https://github.com/AbdulRauf96/saas-revenue-pipeline/actions/workflows/refresh.yml)

A scheduled data pipeline that extracts XBRL financial facts for 20 public SaaS companies from SEC EDGAR, resolves restatements and tag changes, and computes revenue-quality metrics: deferred revenue, remaining performance obligations, and implied billings.

Runs weekly on GitHub Actions. Current output is in [`output/`](output/).

---

## Why these metrics

Headline revenue growth says what a SaaS company recognised last quarter. It says little about what customers have already committed to pay.

Three disclosures fill that gap, and all three became visible in filings after ASC 606 took effect in 2018:

**Deferred revenue** — cash collected for services not yet delivered. A balance-sheet liability that behaves like a leading indicator: it rises when customers prepay for longer terms and falls when they don't.

**Remaining performance obligations (RPO)** — the total value of contracted revenue not yet recognised, including amounts not yet billed. Companies whose contracts run a year or less may omit this under a practical expedient, which is why four of the twenty companies here don't report it.

**Implied billings** — revenue plus the period-over-period change in deferred revenue. An approximation of what the company actually invoiced, rather than what accounting rules let it recognise.

Together they describe the durability of revenue rather than its size.

---

## Running it

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync

uv run saasrev fetch      # download filings from SEC EDGAR
uv run saasrev build      # parse, store, compute metrics
uv run saasrev export     # write output/ as Parquet and CSV
```

Useful flags:

```bash
uv run saasrev fetch --ticker SNOW        # one company
uv run saasrev fetch -t SNOW -t DDOG      # several
uv run saasrev fetch --force              # bypass the cache
uv run saasrev fetch -v                   # debug logging
```

Tests and linting:

```bash
uv run pytest
uv run ruff check .
```

---

## How it works

```
SEC EDGAR XBRL API
        │  retry, exponential backoff, three-tier cache
        ▼
   data/raw/*.json          (gitignored — ~55 MB)
        │  parse: pool candidate tags, resolve per period by filing date
        ▼
   DuckDB facts table       (idempotent upsert, latest filing wins)
        │  views: pivot concepts, window functions per grain
        ▼
   output/metrics_*.{parquet,csv}   (committed)
```

**Caching.** Files newer than 24 hours are reused without a request. Older ones use conditional requests (`If-Modified-Since`). A zero-byte cache file is always re-downloaded — otherwise an interrupted write would be served as valid indefinitely.

**Parsing.** Each concept has several candidate XBRL tags. Rather than a precedence chain, facts from all tags are pooled and resolved per period by filing date. Shopify reports revenue under `RevenueFromContractWithCustomerExcludingAssessedTax` through 2023 and under `Revenues` from 2023 onward — neither tag supersedes the other wholesale, so a fixed priority order would drop data.

**Period resolution.** The same period appears repeatedly across filings: in an original 10-Q, again as a prior-year comparative in the next 10-K, sometimes with a restated value. For each `(concept, period_type, period_start, period_end, unit)` the latest filed fact wins.

**Period grain.** Durations are bucketed by length: quarterly (~91 days), half-year, three-quarters, annual (~364 days). Quarterly filings include year-to-date cumulative figures alongside the quarter itself, and mixing those into a quarterly series would compare a nine-month cumulative against a three-month figure. Every window function partitions on grain.

**Storage.** DuckDB, with a primary key covering company, concept, period type, both period dates, and unit. Re-running the pipeline over the same data produces the same table.

---

## Known limitations

Named rather than hidden. Each was found by inspecting real output.

**The SEC returns no cache-validation headers.** No `Last-Modified`, no `ETag`, no `Cache-Control`. Conditional requests therefore succeed roughly half the time, non-deterministically, and the hit rate cannot be improved from the client side. The 24-hour TTL exists to give deterministic behaviour for repeated runs.

**Implied billings is distorted by acquisitions and foreign exchange.** An acquired deferred revenue balance appears as a change without corresponding billing activity. FX movements on non-USD contracts do the same. The figure is directionally useful, not exact.

**RPO only exists after 2018.** ASC 606 introduced the disclosure. Pre-2019 rows are null, not zero — the distinction matters, and the pipeline preserves it. Four companies (Shopify, Intuit, Veeva, and historically others) omit RPO entirely under the practical expedient for contracts of a year or less.

**Quarterly series have a structural gap.** Companies file a 10-K rather than a fourth 10-Q, so Q4 never appears as a standalone quarterly fact. Trailing-twelve-month figures spanning that gap cover four rows but five quarters of calendar time.

**Early trailing-twelve-month values are partial.** The rolling window sums whatever rows precede it, so the first three quarters of any company's series are not true TTM figures.

**Missing values are null, never zero.** A company that doesn't disclose a concept and a company reporting zero are different facts. Where a value is absent, downstream metrics that depend on it are also null rather than silently computed from a substituted zero.

---

## Data source

SEC EDGAR XBRL company facts API. Public, no authentication, no cost.

```
https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json
```

The SEC requires a descriptive `User-Agent` header identifying the requester; requests without one receive HTTP 403. Rate limit is 10 requests per second.

Companies tracked are in [`config/companies.yaml`](config/companies.yaml), each validated against the live API before being committed.

---

## Testing

24 tests covering config validation, parsing, storage idempotency, and metric correctness.

Two are worth calling out:

**`test_metrics_match_reported_revenue`** asserts Salesforce FY2024 revenue equals $34.857bn — the figure in their 10-K. Most tests verify internal consistency; this one verifies correctness against the outside world.

**`test_ttm_is_plausible_multiple_of_quarterly_revenue`** asserts no trailing-twelve-month figure exceeds six times its quarter. It doesn't check a specific number — it checks that a whole class of window-partitioning bug is absent. It was written after exactly that bug appeared in production output and passed 23 existing tests.

Tests that depend on cached filings skip when `data/raw/` is empty, which is the case on a fresh CI checkout. The badge covers the fixture-based tests.

---

## Stack

Python 3.12 · uv · DuckDB · pytest · ruff · GitHub Actions

DuckDB rather than Postgres or a cloud warehouse: the dataset is a few thousand rows, it runs embedded with no server, and it reads and writes Parquet natively. Choosing the smallest tool that fits is part of the point.

---

## Licence

MIT
