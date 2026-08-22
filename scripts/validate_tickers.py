"""One-off: check which SaaS tickers resolve to a working companyfacts endpoint."""

import time

import requests

USER_AGENT = "Abdul Rauf Maroof abdulrauf96@gmail.com"
TICKERS = [
    "CRM", "NOW", "WDAY", "SNOW", "DDOG", "MDB", "ZS", "CRWD", "NET", "TEAM",
    "HUBS", "ZM", "DOCU", "OKTA", "TWLO", "SHOP", "ADBE", "INTU", "PANW", "VEEV",
]


def main() -> None:
    headers = {"User-Agent": USER_AGENT}
    mapping = requests.get(
        "https://www.sec.gov/files/company_tickers.json", headers=headers, timeout=30
    ).json()
    by_ticker = {row["ticker"]: row for row in mapping.values()}

    for ticker in TICKERS:
        row = by_ticker.get(ticker)
        if row is None:
            print(f"{ticker:6} NOT IN SEC TICKER MAP")
            continue

        cik = str(row["cik_str"]).zfill(10)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        resp = requests.get(url, headers=headers, timeout=30)
        time.sleep(0.2)

        if resp.status_code != 200:
            print(f"{ticker:6} {cik}  HTTP {resp.status_code}")
            continue

        facts = resp.json().get("facts", {})
        tags = facts.get("us-gaap", {})
        has_rpo = "RevenueRemainingPerformanceObligation" in tags
        has_dr = "ContractWithCustomerLiabilityCurrent" in tags
        print(
            f"{ticker:6} {cik}  ok  tags={len(tags):4}  "
            f"RPO={'y' if has_rpo else 'n'}  DefRev={'y' if has_dr else 'n'}  "
            f"{row['title'][:30]}"
        )


if __name__ == "__main__":
    main()