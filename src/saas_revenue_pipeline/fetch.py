"""Fetch raw XBRL company facts from SEC EDGAR."""

import json
import logging
import time
from datetime import date
from pathlib import Path

import requests

from saas_revenue_pipeline.config import Company, load_config, user_agent

logger = logging.getLogger(__name__)

COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# SEC rate limit is 10 requests/second. Stay well under it.
REQUEST_DELAY_SECONDS = 0.2


def fetch_company_facts(company: Company, output_dir: Path) -> Path:
    """Download all XBRL facts for one company and save the raw JSON.

    Args:
        company: Validated config entry. Its CIK is already 10-digit padded.
        output_dir: Directory to write into. Created if absent.

    Returns:
        Path to the written file.
    """
    url = COMPANY_FACTS_URL.format(cik=company.cik)

    logger.info("Fetching %s (CIK %s)", company.ticker, company.cik)
    response = requests.get(
        url, headers={"User-Agent": user_agent()}, timeout=30
    )
    response.raise_for_status()
    time.sleep(REQUEST_DELAY_SECONDS)

    payload = response.json()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"CIK{company.cik}_{date.today().isoformat()}.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    logger.info(
        "Wrote %s (%s, %d KB)",
        output_path.name,
        payload.get("entityName", "unknown"),
        output_path.stat().st_size // 1024,
    )
    return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    config = load_config()
    fetch_company_facts(config.company("SNOW"), config.raw_dir)