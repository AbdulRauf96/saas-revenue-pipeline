"""One-off: dump the current view definitions."""

from saas_revenue_pipeline.config import load_config
from saas_revenue_pipeline.storage import connect


def main() -> None:
    config = load_config()
    con = connect(config.raw_dir.parent / "saasrev.duckdb")
    rows = con.execute(
        "SELECT view_name, sql FROM duckdb_views() WHERE NOT internal"
    ).fetchall()
    for name, sql in rows:
        print(f"===== {name} =====")
        print(sql)
        print()


if __name__ == "__main__":
    main()