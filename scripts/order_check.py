"""One-off: is the export ordering deterministic across repeated queries?"""

from saas_revenue_pipeline.config import load_config
from saas_revenue_pipeline.storage import connect

QUERY = """
SELECT cik, period_end FROM metrics_final
WHERE grain = 'quarterly'
ORDER BY cik, period_end
"""


def main() -> None:
    config = load_config()
    con = connect(config.raw_dir.parent / "saasrev.duckdb")

    runs = [con.execute(QUERY).fetchall() for _ in range(5)]
    first = runs[0]

    print(f"{len(first)} rows")
    for i, run in enumerate(runs[1:], start=2):
        same = run == first
        print(f"  run {i}: {'identical' if same else 'DIFFERENT'}")
        if not same:
            for j, (a, b) in enumerate(zip(first, run)):
                if a != b:
                    print(f"    first divergence at row {j}: {a} vs {b}")
                    break


if __name__ == "__main__":
    main()