"""Fetch raw XBRL company facts from SEC EDGAR."""

import json
import logging
import time
from email.utils import formatdate
from pathlib import Path

import requests

from saas_revenue_pipeline.config import Company, load_config, user_agent

logger = logging.getLogger(__name__)

COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# SEC rate limit is 10 requests/second. Stay well under it.
REQUEST_DELAY_SECONDS = 0.2

# Skip the network entirely for cache files younger than this.
CACHE_TTL_SECONDS = 24 * 60 * 60

# Retry policy for transient failures.
MAX_ATTEMPTS = 4
BACKOFF_BASE_SECONDS = 1.0
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class FetchError(RuntimeError):
    """Raised when a company's facts could not be retrieved."""


def _get_with_retry(url: str, headers: dict[str, str]) -> requests.Response:
    """GET with exponential backoff on transient failures.

    Retries on 429 and 5xx responses and on connection errors. Client errors
    other than 429 are not retried — they will not succeed on a second attempt.
    """
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(url, headers=headers, timeout=30)
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.status_code not in RETRY_STATUS_CODES:
                return response
            last_error = FetchError(f"HTTP {response.status_code}")

        if attempt < MAX_ATTEMPTS:
            delay = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
            logger.warning(
                "attempt %d/%d failed (%s), retrying in %.1fs",
                attempt,
                MAX_ATTEMPTS,
                last_error,
                delay,
            )
            time.sleep(delay)

    raise FetchError(f"giving up after {MAX_ATTEMPTS} attempts: {last_error}")


def fetch_company_facts(
    company: Company, output_dir: Path, *, force: bool = False
) -> Path:
    """Download one company's XBRL facts, using a local cache when unchanged.

    Sends If-Modified-Since based on the cached file's modification time. A 304
    response means the SEC has nothing newer and the cached copy is returned.

    Args:
        company: Validated config entry. Its CIK is already 10-digit padded.
        output_dir: Cache directory. Created if absent.
        force: Skip the conditional header and always download a full body.

    Returns:
        Path to the cached file.

    Raises:
        FetchError: If the request failed after retries.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"CIK{company.cik}.json"

    headers = {"User-Agent": user_agent()}
    if output_path.exists() and not force:
        stat = output_path.stat()
        age = time.time() - stat.st_mtime

        if stat.st_size == 0:
            logger.warning("%s cache is empty, re-downloading", company.ticker)
        elif age < CACHE_TTL_SECONDS:
            logger.info("%s cached %.1fh ago, skipping", company.ticker, age / 3600)
            return output_path
        else:
            headers["If-Modified-Since"] = formatdate(stat.st_mtime, usegmt=True)

    logger.info("fetching %s (CIK %s)", company.ticker, company.cik)
    response = _get_with_retry(COMPANY_FACTS_URL.format(cik=company.cik), headers)
    time.sleep(REQUEST_DELAY_SECONDS)

    if response.status_code == 304:
        logger.info("%s unchanged since last fetch, using cache", company.ticker)
        return output_path

    response.raise_for_status()

    payload = response.json()
    output_path.write_text(json.dumps(payload), encoding="utf-8")

    logger.info(
        "wrote %s (%s, %d KB)",
        output_path.name,
        payload.get("entityName", "unknown"),
        output_path.stat().st_size // 1024,
    )
    return output_path


def fetch_all(
    companies: list[Company], output_dir: Path, *, force: bool = False
) -> list[Path]:
    """Fetch several companies, continuing past individual failures."""
    paths: list[Path] = []
    for company in companies:
        try:
            paths.append(fetch_company_facts(company, output_dir, force=force))
        except (FetchError, requests.HTTPError) as exc:
            logger.error("%s failed: %s", company.ticker, exc)
    return paths


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    config = load_config()
    fetch_company_facts(config.company("SNOW"), config.raw_dir)