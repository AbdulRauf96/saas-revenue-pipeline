"""One-off: find period_ends with more than one metrics row per company."""

from saas_revenue_pipeline.config import load_config
from saas_revenue_pipeline.storage import connect


def main() -> None:
    config = load_config()
    con = connect(config.raw_dir.parent / "saasrev.duckdb")

    rows = con.execute(
        """
        SELECT cik, period_end, grain, count(*) AS n
        FROM metrics_final
        GROUP BY cik, period_end, grain
        HAVING count(*) > 1
        ORDER BY n DESC, cik, period_end
        LIMIT 20
        """
    ).fetchall()

    print(f"{len(rows)} duplicated (cik, period_end, grain) keys")
    for cik, end, grain, n in rows:
        print(f"  {cik} {end} {grain} -> {n} rows")


if __name__ == "__main__":
    main()