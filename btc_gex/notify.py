"""Send GEX snapshot + heatmap to Telegram."""

from __future__ import annotations

import os
from pathlib import Path

import requests

from btc_gex.gex import GexSnapshot

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _format_usd(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"${value / 1_000:.2f}K"
    return f"${value:,.0f}"


def format_telegram_caption(snapshot: GexSnapshot) -> str:
    flip = f"{snapshot.gamma_flip:,.0f}" if snapshot.gamma_flip else "n/a"
    return (
        f"BTC GEX (Deribit)\n"
        f"UTC {snapshot.as_of.strftime('%Y-%m-%d %H:%M')}\n"
        f"Spot ${snapshot.spot:,.0f}\n"
        f"Net GEX {_format_usd(snapshot.net_gex)}\n"
        f"Regime {snapshot.regime}\n"
        f"{snapshot.regime_cn}\n"
        f"Flip {flip} | King ${snapshot.king_strike:,.0f}"
    )


def send_telegram_message(
    text: str,
    *,
    token: str | None = None,
    chat_id: str | None = None,
) -> None:
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
    if not chat_id:
        raise RuntimeError("Missing TELEGRAM_CHAT_ID")

    url = TELEGRAM_API.format(token=token, method="sendMessage")
    response = requests.post(
        url,
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    payload = response.json()
    if not response.ok or not payload.get("ok"):
        description = payload.get("description", response.text)
        raise RuntimeError(
            f"Telegram sendMessage failed ({response.status_code}): {description}. "
            "Check TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and that you messaged the bot first."
        )


def send_telegram_photo(
    image_path: str | Path,
    *,
    caption: str,
    token: str | None = None,
    chat_id: str | None = None,
) -> None:
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
    if not chat_id:
        raise RuntimeError("Missing TELEGRAM_CHAT_ID")

    image_path = Path(image_path)
    if not image_path.is_file():
        raise FileNotFoundError(f"Heatmap not found: {image_path}")

    url = TELEGRAM_API.format(token=token, method="sendPhoto")
    with image_path.open("rb") as image_file:
        response = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": image_file},
            timeout=60,
        )
    payload = response.json()
    if not response.ok or not payload.get("ok"):
        description = payload.get("description", response.text)
        raise RuntimeError(
            f"Telegram sendPhoto failed ({response.status_code}): {description}. "
            "Check TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and that you messaged the bot first."
        )
