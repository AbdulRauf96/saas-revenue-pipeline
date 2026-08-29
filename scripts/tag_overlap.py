"""One-off: find periods reported under more than one tag for the same concept."""

import json
import sys
from collections import defaultdict
from pathlib import Path

REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
]


def main(path: str) -> None:
    tags = json.loads(Path(path).read_text(encoding="utf-8"))["facts"]["us-gaap"]

    by_period = defaultdict(list)
    for tag in REVENUE_TAGS:
        if tag not in tags:
            continue
        for unit, facts in tags[tag]["units"].items():
            for f in facts:
                key = (f.get("start"), f["end"], unit)
                by_period[key].append((tag, f["val"], f["accn"], f["filed"]))

    for key, entries in sorted(by_period.items(), key=lambda kv: str(kv[0][1])):
        if len(entries) > 1:
            print(f"\n{key[0]} -> {key[1]} ({key[2]})")
            for tag, val, accn, filed in entries:
                print(f"   {val:>18,}  {tag:52} {accn}  filed {filed}")


if __name__ == "__main__":
    main(sys.argv[1])