"""Derived SaaS revenue metrics computed over stored facts."""

from __future__ import annotations

import logging

import duckdb

logger = logging.getLogger(__name__)

# One row per company-period, with each concept pivoted into a column.
# Grain is filtered by the caller — never mix quarterly and annual in a window
# function, and never let a year-to-date cumulative into a quarterly series.
PIVOT = """
CREATE OR REPLACE VIEW periods AS
WITH duration AS (
    SELECT cik, period_end, grain,
           max(CASE WHEN concept = 'revenue' THEN value END) AS revenue
    FROM facts
    WHERE period_type = 'duration' AND unit = 'USD'
    GROUP BY cik, period_end, grain
),
instant AS (
    SELECT cik, period_end,
           max(CASE WHEN concept = 'deferred_revenue_current'    THEN value END) AS dr_current,
           max(CASE WHEN concept = 'deferred_revenue_noncurrent' THEN value END) AS dr_noncurrent,
           max(CASE WHEN concept = 'rpo'                         THEN value END) AS rpo
    FROM facts
    WHERE period_type = 'instant' AND unit = 'USD'
    GROUP BY cik, period_end
)
SELECT
    d.cik,
    d.period_end,
    d.grain,
    d.revenue,
    i.dr_current,
    i.dr_noncurrent,
    CASE
        WHEN i.dr_current IS NULL AND i.dr_noncurrent IS NULL THEN NULL
        ELSE coalesce(i.dr_current, 0) + coalesce(i.dr_noncurrent, 0)
    END AS deferred_revenue,
    i.rpo
FROM duration d
LEFT JOIN instant i USING (cik, period_end);
"""

# Window functions over a single grain. LAG(1) is the prior period of the same
# grain; LAG(4) on quarterly data is the same quarter a year earlier.
METRICS = """
CREATE OR REPLACE VIEW metrics AS
SELECT
    cik,
    period_end,
    grain,
    revenue,
    deferred_revenue,
    rpo,

    -- Implied billings: revenue recognised plus the change in what customers
    -- have paid for but not yet consumed. Distorted by acquisitions and FX.
    revenue + (
        deferred_revenue
        - lag(deferred_revenue) OVER (PARTITION BY cik, grain ORDER BY period_end)
    ) AS implied_billings,

    -- Trailing twelve months. Quarterly: 4 periods. Annual: the period itself.
    CASE WHEN grain = 'quarterly'
         THEN sum(revenue) OVER (
             PARTITION BY cik ORDER BY period_end ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
         )
         ELSE revenue
    END AS ttm_revenue,

    lag(revenue, CASE WHEN grain = 'quarterly' THEN 4 ELSE 1 END)
        OVER (PARTITION BY cik, grain ORDER BY period_end) AS revenue_prior_year
FROM periods
WHERE revenue IS NOT NULL;
"""

RATIOS = """
CREATE OR REPLACE VIEW metrics_final AS
SELECT
    *,
    CASE WHEN revenue_prior_year > 0
         THEN revenue / revenue_prior_year - 1
    END AS revenue_yoy,

    CASE WHEN ttm_revenue > 0 AND rpo IS NOT NULL
         THEN rpo / ttm_revenue
    END AS rpo_coverage,

    CASE WHEN ttm_revenue > 0
         THEN deferred_revenue / ttm_revenue
    END AS deferred_revenue_ratio
FROM metrics;
"""


def build_views(con: duckdb.DuckDBPyConnection) -> None:
    """Create or replace all derived views. Safe to run repeatedly."""
    for statement in (PIVOT, METRICS, RATIOS):
        con.execute(statement)
    logger.info("built derived views")