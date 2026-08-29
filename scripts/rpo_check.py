"""One-off: compare cached vs live RPO availability for the four no-RPO companies."""

import json
import time

import requests

from saas_revenue_pipeline.config import load_config, user_agent

RPO_TAG = "RevenueRemainingPerformanceObligation"
SUSPECT = ["SHOP", "ADBE", "INTU", "VEEV"]


def main() -> None:
    config = load_config()
    headers = {"User-Agent": user_agent()}

    for ticker in SUSPECT:
        company = config.company(ticker)
        path = config.raw_dir / f"CIK{company.cik}.json"

        cached_tags = json.loads(path.read_text(encoding="utf-8"))["facts"]["us-gaap"]
        cached = RPO_TAG in cached_tags

        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company.cik}.json"
        live_tags = requests.get(url, headers=headers, timeout=60).json()["facts"]["us-gaap"]
        live = RPO_TAG in live_tags
        time.sleep(0.2)

        flag = "" if cached == live else "  <-- MISMATCH"
        print(
            f"{ticker:6} config={company.rpo_available!s:5} "
            f"cached={cached!s:5} live={live!s:5} "
            f"tags cached={len(cached_tags)} live={len(live_tags)}{flag}"
        )


if __name__ == "__main__":
    main()