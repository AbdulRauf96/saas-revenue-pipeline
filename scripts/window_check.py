"""One-off: is the TTM window deterministic, and is the series dense?"""

from saas_revenue_pipeline.config import load_config
from saas_revenue_pipeline.storage import connect

Q = """
SELECT period_end, revenue, ttm_revenue
FROM metrics_final
WHERE cik = '0000796343' AND grain = 'quarterly'
ORDER BY period_end
"""


def main() -> None:
    config = load_config()
    con = connect(config.raw_dir.parent / "saasrev.duckdb")

    runs = [con.execute(Q).fetchall() for _ in range(3)]
    print("deterministic:", all(r == runs[0] for r in runs))

    print("\nfirst 12 rows, with gap in days:")
    prev = None
    for end, rev, ttm in runs[0][:12]:
        gap = (end - prev).days if prev else None
        print(f"  {end}  rev={rev:>15,.0f}  ttm={ttm:>15,.0f}  gap={gap}")
        prev = end


if __name__ == "__main__":
    main()