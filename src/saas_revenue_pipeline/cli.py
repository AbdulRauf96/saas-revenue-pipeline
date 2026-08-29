"""Command-line interface for the SaaS revenue pipeline."""

import argparse
import logging
import sys

from saas_revenue_pipeline.config import load_config
from saas_revenue_pipeline.fetch import fetch_all

logger = logging.getLogger(__name__)


def main() -> int:
    """Entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="saasrev",
        description="SaaS revenue fundamentals pipeline (SEC EDGAR XBRL).",
    )
    # Accepted before the subcommand: `saasrev -v fetch`
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="enable debug logging",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser(
        "fetch", help="download company facts from SEC EDGAR"
    )
    fetch_parser.add_argument(
        "-t",
        "--ticker",
        action="append",
        metavar="TICKER",
        help="fetch only this ticker; repeatable. Default: all configured companies",
    )
    fetch_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="re-download even if a cached copy exists",
    )
    # Also accepted after the subcommand: `saasrev fetch -v`.
    # default=None so an omitted flag here doesn't overwrite the parent's value.
    fetch_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=None,
        help="enable debug logging",
    )

    build_parser = subparsers.add_parser(
        "build", help="parse cached filings and compute metrics"
    )
    build_parser.add_argument(
        "-t",
        "--ticker",
        action="append",
        metavar="TICKER",
        help="build only this ticker; repeatable. Default: all configured companies",
    )
    build_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=None,
        help="enable debug logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)-8s %(message)s",
    )

    if args.command == "fetch":
        config = load_config()

        if args.ticker:
            companies = [config.company(t) for t in args.ticker]
        else:
            companies = list(config.companies)

        logger.info("fetching %d companies", len(companies))
        paths = fetch_all(companies, config.raw_dir, force=args.force)
        logger.info("%d/%d succeeded", len(paths), len(companies))
        return 0 if len(paths) == len(companies) else 1

    if args.command == "build":
        # Imported here so `saasrev fetch` doesn't pay DuckDB's import cost.
        from saas_revenue_pipeline.metrics import build_views
        from saas_revenue_pipeline.parse import parse_file
        from saas_revenue_pipeline.storage import connect, fact_count, write_facts

        config = load_config()
        companies = (
            [config.company(t) for t in args.ticker]
            if args.ticker
            else list(config.companies)
        )

        con = connect(config.raw_dir.parent / "saasrev.duckdb")
        written = 0
        skipped = 0

        for company in companies:
            path = config.raw_dir / f"CIK{company.cik}.json"
            if not path.exists():
                logger.warning("%s: no cached file, run fetch first", company.ticker)
                skipped += 1
                continue
            facts = parse_file(path)
            written += write_facts(con, facts)
            logger.info("%s: %d facts", company.ticker, len(facts))

        build_views(con)
        logger.info("wrote %d facts, %d total in db", written, fact_count(con))
        con.close()
        return 1 if skipped else 0

    parser.error(f"unhandled command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())