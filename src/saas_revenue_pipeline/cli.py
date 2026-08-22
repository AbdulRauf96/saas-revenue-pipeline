"""Command-line interface for the SaaS revenue pipeline."""

import argparse
import logging
import sys

logger = logging.getLogger(__name__)


def main() -> int:
    """Entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="saasrev",
        description="SaaS revenue fundamentals pipeline (SEC EDGAR XBRL).",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="enable debug logging"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("fetch", help="download company facts from SEC EDGAR")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)-8s %(message)s",
    )

    if args.command == "fetch":
        logger.info("fetch: not implemented yet")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())