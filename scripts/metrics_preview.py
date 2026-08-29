"""One-off: show computed metrics for one company."""

import sys

from saas_revenue_pipeline.config import load_config
from saas_revenue_pipeline.storage import connect


def main(ticker: str, grain: str = "annual") -> None:
    config = load_config()
    company = config.company(ticker)
    con = connect(config.raw_dir.parent / "saasrev.duckdb")

    rows = con.execute(
        """
        SELECT period_end, revenue, deferred_revenue, rpo,
               implied_billings, revenue_yoy, rpo_coverage
        FROM metrics_final
        WHERE cik = ? AND grain = ?
        ORDER BY period_end DESC
        LIMIT 12
        """,
        [company.cik, grain],
    ).fetchall()

    print(f"{company.ticker} — {grain}")
    print(f"{'period':>12} {'revenue':>14} {'def rev':>14} {'RPO':>14} "
          f"{'billings':>14} {'yoy':>7} {'rpo cov':>8}")

    def num(value, width=14, places=0):
        """Format a number, or an em dash when the value is missing."""
        if value is None:
            return f"{'—':>{width}}"
        return f"{value:>{width},.{places}f}"

    def pct(value, width=7):
        if value is None:
            return f"{'—':>{width}}"
        return f"{value * 100:>{width - 1}.1f}%"

    for end, rev, dr, rpo, bill, yoy, cov in rows:
        print(
            f"{end!s:>12} {num(rev)} {num(dr)} {num(rpo)} {num(bill)} "
            f"{pct(yoy)} {num(cov, width=8, places=2)}"
        )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "SNOW",
         sys.argv[2] if len(sys.argv) > 2 else "annual")