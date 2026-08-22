"""Fetch raw XBRL company facts from SEC EDGAR."""

import json
import logging
import time
from datetime import date
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# SEC requires a descriptive User-Agent identifying the requester.
# Requests without one are rejected with HTTP 403.
USER_AGENT = "Abdul Rauf Maroof abdulrauf96@gmail.com"

COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# SEC rate limit is 10 requests/second. Stay well under it.
REQUEST_DELAY_SECONDS = 0.2


def fetch_company_facts(cik: int, output_dir: Path) -> Path:
    """Download all XBRL facts for one company and save the raw JSON.

    Args:
        cik: SEC Central Index Key, unpadded (e.g. 1640147 for Snowflake).
        output_dir: Directory to write into. Created if absent.

    Returns:
        Path to the written file.
    """
    padded_cik = str(cik).zfill(10)
    url = COMPANY_FACTS_URL.format(cik=padded_cik)

    logger.info("Fetching CIK %s", padded_cik)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    time.sleep(REQUEST_DELAY_SECONDS)

    payload = response.json()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"CIK{padded_cik}_{date.today().isoformat()}.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    logger.info(
        "Wrote %s (%s, %d KB)",
        output_path.name,
        payload.get("entityName", "unknown"),
        output_path.stat().st_size // 1024,
    )
    return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    fetch_company_facts(cik=1640147, output_dir=Path("data/raw"))