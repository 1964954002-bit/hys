"""Fetch BTC options data from Deribit public API."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import requests

DERIBIT_BASE = "https://www.deribit.com/api/v2/public"
INSTRUMENT_RE = re.compile(
    r"^(?P<currency>[A-Z]+)-(?P<expiry>\d{1,2}[A-Z]{3}\d{2})-(?P<strike>\d+(?:\d)?)-(?P<type>[CP])$"
)
EXPIRY_RE = re.compile(r"^(?P<day>\d{1,2})(?P<mon>[A-Z]{3})(?P<year>\d{2})$")
MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


@dataclass(frozen=True)
class OptionRow:
    instrument_name: str
    strike: float
    option_type: Literal["C", "P"]
    expiry: datetime
    open_interest: float
    mark_iv: float
    underlying_price: float
    interest_rate: float


def _fetch_json(path: str, params: dict | None = None) -> dict:
    response = requests.get(f"{DERIBIT_BASE}/{path}", params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload


def parse_instrument_name(name: str) -> tuple[float, Literal["C", "P"], datetime] | None:
    match = INSTRUMENT_RE.match(name)
    if not match:
        return None

    expiry_match = EXPIRY_RE.match(match.group("expiry"))
    if not expiry_match:
        return None

    day = int(expiry_match.group("day"))
    month = MONTHS[expiry_match.group("mon")]
    year = 2000 + int(expiry_match.group("year"))
    expiry = datetime(year, month, day, 8, 0, tzinfo=timezone.utc)

    return float(match.group("strike")), match.group("type"), expiry


def fetch_btc_option_chain(currency: str = "BTC") -> list[OptionRow]:
    raw = _fetch_json(
        "get_book_summary_by_currency",
        params={"currency": currency, "kind": "option"},
    )
    rows: list[OptionRow] = []
    for item in raw["result"]:
        parsed = parse_instrument_name(item.get("instrument_name", ""))
        if parsed is None:
            continue

        strike, option_type, expiry = parsed
        open_interest = float(item.get("open_interest") or 0.0)
        if open_interest <= 0:
            continue

        mark_iv = float(item.get("mark_iv") or 0.0)
        underlying_price = float(item.get("underlying_price") or 0.0)
        if mark_iv <= 0 or underlying_price <= 0:
            continue

        rows.append(
            OptionRow(
                instrument_name=item["instrument_name"],
                strike=strike,
                option_type=option_type,
                expiry=expiry,
                open_interest=open_interest,
                mark_iv=mark_iv,
                underlying_price=underlying_price,
                interest_rate=float(item.get("interest_rate") or 0.0),
            )
        )
    return rows


def fetch_index_price(index_name: str = "btc_usd") -> float:
    raw = _fetch_json("get_index_price", params={"index_name": index_name})
    return float(raw["result"]["index_price"])
