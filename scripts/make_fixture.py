"""One-off: trim a real companyfacts payload into a small test fixture.

Keeps only the four concepts the parser cares about, and only the most recent
handful of facts for each — enough to exercise dedupe, tag fallback, and
period typing without committing a multi-megabyte file.

    uv run python scripts/make_fixture.py SNOW
"""

import json
import sys
from pathlib import Path

from saas_revenue_pipeline.config import load_config

KEEP_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "ContractWithCustomerLiabilityCurrent",
    "ContractWithCustomerLiabilityNoncurrent",
    "DeferredRevenueCurrent",
    "DeferredRevenueNoncurrent",
    "RevenueRemainingPerformanceObligation",
]

FACTS_PER_TAG = 12


def main(ticker: str) -> None:
    config = load_config()
    company = config.company(ticker)
    source = config.raw_dir / f"CIK{company.cik}.json"
    payload = json.loads(source.read_text(encoding="utf-8"))

    us_gaap = payload["facts"]["us-gaap"]
    trimmed: dict = {}

    for tag in KEEP_TAGS:
        if tag not in us_gaap:
            print(f"  {tag}: absent")
            continue
        units = {}
        for unit, facts in us_gaap[tag]["units"].items():
            # Keep the most recently filed facts — these carry the
            # duplicate periods and restatements worth testing against.
            facts = sorted(facts, key=lambda f: f["filed"])[-FACTS_PER_TAG:]
            units[unit] = facts
        trimmed[tag] = {"label": us_gaap[tag].get("label"), "units": units}
        print(f"  {tag}: {sum(len(v) for v in units.values())} facts")

    out = {
        "cik": payload["cik"],
        "entityName": payload["entityName"],
        "facts": {"us-gaap": trimmed},
    }

    dest = Path("tests/fixtures") / f"{company.ticker.lower()}_trimmed.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {dest} ({dest.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "SNOW")