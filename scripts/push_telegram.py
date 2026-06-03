#!/usr/bin/env python3
"""Generate BTC GEX heatmap and send it to Telegram."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from btc_gex.deribit import fetch_btc_option_chain, fetch_index_price
from btc_gex.gex import compute_gex_snapshot
from btc_gex.heatmap import render_gex_heatmap
from btc_gex.notify import format_telegram_caption, send_telegram_photo

OUTPUT_PATH = ROOT / "output" / "btc_gex_heatmap.png"


def _require_telegram_env() -> None:
    import os

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing. Add it in GitHub: "
            "repo Settings → Secrets and variables → Actions → New repository secret"
        )
    if not chat_id:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID is missing. Add it in GitHub Secrets "
            "(numeric id from getUpdates, not your phone number)"
        )


def main() -> None:
    _require_telegram_env()
    print("Step 1/4: Fetching Deribit option chain...")
    chain = fetch_btc_option_chain("BTC")
    print(f"  contracts: {len(chain)}")
    print("Step 2/4: Fetching BTC index price...")
    spot = fetch_index_price("btc_usd")
    print(f"  spot: {spot}")
    print("Step 3/4: Computing GEX and rendering heatmap...")
    snapshot = compute_gex_snapshot(chain, spot=spot)
    path = render_gex_heatmap(snapshot, OUTPUT_PATH)
    print(f"  saved: {path}")
    print("Step 4/4: Sending photo to Telegram...")
    caption = format_telegram_caption(snapshot)
    send_telegram_photo(path, caption=caption)
    print(f"SUCCESS: Sent to Telegram: {path}")


if __name__ == "__main__":
    main()
