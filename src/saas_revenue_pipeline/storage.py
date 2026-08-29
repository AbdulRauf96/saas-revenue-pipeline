"""DuckDB persistence for parsed facts and derived metrics."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from saas_revenue_pipeline.parse import Fact

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    cik           VARCHAR NOT NULL,
    concept       VARCHAR NOT NULL,
    period_type   VARCHAR NOT NULL,
    period_start  DATE    NOT NULL,
    period_end    DATE    NOT NULL,
    value         DOUBLE,
    unit          VARCHAR,
    source_tag    VARCHAR,
    accn          VARCHAR,
    filed         DATE,
    form          VARCHAR,
    PRIMARY KEY (cik, concept, period_type, period_start, period_end, unit)
);

CREATE OR REPLACE VIEW facts_clean AS
SELECT
    cik,
    concept,
    period_type,
    CASE WHEN period_type = 'instant' THEN NULL ELSE period_start END AS period_start,
    period_end,
    value,
    unit,
    source_tag,
    accn,
    filed,
    form
FROM facts;
"""

UPSERT = """
INSERT INTO facts (
    cik, concept, period_type, period_start, period_end,
    value, unit, source_tag, accn, filed, form
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (cik, concept, period_type, period_start, period_end, unit)
DO UPDATE SET
    value      = excluded.value,
    source_tag = excluded.source_tag,
    accn       = excluded.accn,
    filed      = excluded.filed,
    form       = excluded.form
WHERE excluded.filed >= facts.filed;
"""


def connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection and ensure the schema exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(SCHEMA)
    return con


def write_facts(con: duckdb.DuckDBPyConnection, facts: list[Fact]) -> int:
    """Upsert facts. Re-running with the same input changes nothing.

    A row is replaced only when the incoming fact was filed no earlier than
    the stored one, so a partial re-parse of older data cannot overwrite a
    restatement already captured.
    """
    rows = [
        (
            f.cik,
            f.concept,
            f.period_type,
            f.period_start,
            f.period_end,
            f.value,
            f.unit,
            f.source_tag,
            f.accn,
            f.filed,
            f.form,
        )
        for f in facts
    ]
    con.executemany(UPSERT, rows)
    return len(rows)


def fact_count(con: duckdb.DuckDBPyConnection) -> int:
    return con.execute("SELECT count(*) FROM facts").fetchone()[0]