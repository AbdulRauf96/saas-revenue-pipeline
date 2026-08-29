"""One-off: parse a cached companyfacts file and summarise the result."""

import sys
from collections import Counter

from saas_revenue_pipeline.config import load_config
from saas_revenue_pipeline.parse import parse_file


def main(ticker: str) -> None:
    config = load_config()
    company = config.company(ticker)
    facts = parse_file(config.raw_dir / f"CIK{company.cik}.json")

    print(f"{company.ticker} — {len(facts)} facts")
    for concept, count in sorted(Counter(f.concept for f in facts).items()):
        periods = [f.period_end for f in facts if f.concept == concept]
        print(f"  {concept:28} {count:4}  {min(periods)} to {max(periods)}")

    units = Counter(f.unit for f in facts)
    if len(units) > 1:
        print(f"  units: {dict(units)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "SHOP")