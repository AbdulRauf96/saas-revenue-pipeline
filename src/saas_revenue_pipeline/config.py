"""Configuration loading for the pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

# Project root: this file is at src/saas_revenue_pipeline/config.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "companies.yaml"
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"


@dataclass(frozen=True)
class Company:
    """One tracked company."""

    ticker: str
    cik: str
    name: str
    rpo_available: bool

    def __post_init__(self) -> None:
        if len(self.cik) != 10 or not self.cik.isdigit():
            raise ValueError(
                f"{self.ticker}: cik must be 10 digits, got {self.cik!r}. "
                "Quote it in YAML to preserve leading zeros."
            )


@dataclass(frozen=True)
class Config:
    """Runtime configuration."""

    companies: tuple[Company, ...]
    raw_dir: Path

    def company(self, ticker: str) -> Company:
        """Look up one company by ticker, case-insensitively."""
        wanted = ticker.upper()
        for c in self.companies:
            if c.ticker == wanted:
                return c
        raise KeyError(f"unknown ticker: {ticker}")


def load_config(
    path: Path | None = None, raw_dir: Path | None = None
) -> Config:
    """Load configuration from YAML.

    Args:
        path: Path to companies.yaml. Defaults to config/companies.yaml.
        raw_dir: Where raw API responses are cached. Defaults to data/raw.
    """
    path = path or DEFAULT_CONFIG_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    companies = tuple(
        Company(
            ticker=entry["ticker"].upper(),
            cik=str(entry["cik"]),
            name=entry["name"],
            rpo_available=bool(entry["rpo_available"]),
        )
        for entry in raw["companies"]
    )
    if not companies:
        raise ValueError(f"no companies found in {path}")

    return Config(companies=companies, raw_dir=raw_dir or DEFAULT_RAW_DIR)

DEFAULT_USER_AGENT = "Abdul Rauf Maroof abdulrauf96@gmail.com"


def user_agent() -> str:
    """SEC-required identifying header.

    Reads SEC_USER_AGENT so CI can supply it as a secret; falls back to the
    local default for development.
    """
    return os.environ.get("SEC_USER_AGENT", DEFAULT_USER_AGENT)