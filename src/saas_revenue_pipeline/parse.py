"""Parse raw SEC companyfacts payloads into normalised financial facts."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

# Candidate XBRL tags per concept. Order carries no precedence — facts from
# every tag are pooled and resolved per period by filing date. Shopify reports
# revenue under RevenueFromContractWithCustomer... through 2023 and under
# Revenues from 2023 onward, so neither tag supersedes the other wholesale.
CONCEPT_TAGS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "deferred_revenue_current": (
        "ContractWithCustomerLiabilityCurrent",
        "DeferredRevenueCurrent",
    ),
    "deferred_revenue_noncurrent": (
        "ContractWithCustomerLiabilityNoncurrent",
        "DeferredRevenueNoncurrent",
    ),
    "rpo": ("RevenueRemainingPerformanceObligation",),
}

# Instant facts have no start date. A sentinel keeps the storage primary key
# valid, since DuckDB rejects NULLs in primary keys.
INSTANT_SENTINEL = date(1900, 1, 1)


@dataclass(frozen=True)
class Fact:
    """One resolved financial fact for a single company and period."""

    cik: str
    concept: str
    period_type: str  # "duration" | "instant"
    period_start: date
    period_end: date
    value: float
    unit: str
    source_tag: str
    accn: str
    filed: date
    form: str

    @property
    def is_instant(self) -> bool:
        return self.period_type == "instant"


def _to_date(value: str) -> date:
    return date.fromisoformat(value)


def _iter_raw_facts(us_gaap: dict, concept: str, cik: str):
    """Yield a Fact for every entry across all candidate tags for a concept."""
    for tag in CONCEPT_TAGS[concept]:
        body = us_gaap.get(tag)
        if body is None:
            continue

        for unit, entries in body.get("units", {}).items():
            for entry in entries:
                start_raw = entry.get("start")
                yield Fact(
                    cik=cik,
                    concept=concept,
                    period_type="duration" if start_raw else "instant",
                    period_start=_to_date(start_raw) if start_raw else INSTANT_SENTINEL,
                    period_end=_to_date(entry["end"]),
                    value=float(entry["val"]),
                    unit=unit,
                    source_tag=tag,
                    accn=entry["accn"],
                    filed=_to_date(entry["filed"]),
                    form=entry["form"],
                )


def parse_company_facts(payload: dict) -> list[Fact]:
    """Extract and resolve all tracked concepts from one companyfacts payload.

    The same period is routinely reported more than once: in an original filing
    and again as a comparative in a later one, sometimes under a different tag
    and sometimes with a restated value. For each
    (concept, period_type, period_start, period_end, unit) the fact with the
    latest filing date wins — that is the figure the company currently stands
    behind.

    Args:
        payload: A parsed companyfacts JSON document.

    Returns:
        Resolved facts, sorted by concept then period end.
    """
    cik = str(payload["cik"]).zfill(10)
    us_gaap = payload.get("facts", {}).get("us-gaap", {})

    resolved: dict[tuple, Fact] = {}

    for concept in CONCEPT_TAGS:
        for fact in _iter_raw_facts(us_gaap, concept, cik):
            key = (
                fact.concept,
                fact.period_type,
                fact.period_start,
                fact.period_end,
                fact.unit,
            )
            incumbent = resolved.get(key)
            if incumbent is None or fact.filed > incumbent.filed:
                resolved[key] = fact

    facts = sorted(resolved.values(), key=lambda f: (f.concept, f.period_end))
    logger.info("parsed %d facts for CIK %s", len(facts), cik)
    return facts


def parse_file(path: Path) -> list[Fact]:
    """Parse a cached companyfacts file from disk."""
    return parse_company_facts(json.loads(path.read_text(encoding="utf-8")))