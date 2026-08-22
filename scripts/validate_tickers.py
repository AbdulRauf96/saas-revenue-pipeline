"""Health check: verify configured tickers still resolve to working endpoints.

Originally used to validate candidate tickers before building companies.yaml.
Now reads the config, so re-running it confirms the tracked list is still good
and that RPO availability hasn't changed.

Not part of the package. Run with:
    uv run python scripts/validate_tickers.py
"""

import time

import requests

from saas_revenue_pipeline.config import load_config, user_agent

RPO_TAG = "RevenueRemainingPerformanceObligation"
DEFERRED_REVENUE_TAG = "ContractWithCustomerLiabilityCurrent"


def main() -> None:
    config = load_config()
    headers = {"User-Agent": user_agent()}

    for company in config.companies:
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company.cik}.json"
        resp = requests.get(url, headers=headers, timeout=30)
        time.sleep(0.2)

        if resp.status_code != 200:
            print(f"{company.ticker:6} {company.cik}  HTTP {resp.status_code}")
            continue

        tags = resp.json().get("facts", {}).get("us-gaap", {})
        has_rpo = RPO_TAG in tags
        has_dr = DEFERRED_REVENUE_TAG in tags

        drift = "" if has_rpo == company.rpo_available else "  <-- RPO DRIFT"
        print(
            f"{company.ticker:6} {company.cik}  ok  tags={len(tags):4}  "
            f"RPO={'y' if has_rpo else 'n'}  DefRev={'y' if has_dr else 'n'}"
            f"{drift}"
        )