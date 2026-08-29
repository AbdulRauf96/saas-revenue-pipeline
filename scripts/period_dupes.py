"""One-off: multiple duration facts sharing a period_end."""

from saas_revenue_pipeline.config import load_config
from saas_revenue_pipeline.storage import connect


def main() -> None:
    config = load_config()
    con = connect(config.raw_dir.parent / "saasrev.duckdb")

    rows = con.execute(
        """
        SELECT period_end, period_start, grain, value, source_tag
        FROM facts
        WHERE cik = '0000796343' AND concept = 'revenue'
          AND period_end IN (DATE '2008-08-29', DATE '2009-08-28')
        ORDER BY period_end, period_start
        """
    ).fetchall()

    for r in rows:
        print(r)


if __name__ == "__main__":
    main()