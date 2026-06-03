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


def main() -> None:
    chain = fetch_btc_option_chain("BTC")
    spot = fetch_index_price("btc_usd")
    snapshot = compute_gex_snapshot(chain, spot=spot)
    path = render_gex_heatmap(snapshot, OUTPUT_PATH)
    caption = format_telegram_caption(snapshot)
    send_telegram_photo(path, caption=caption)
    print(f"Sent to Telegram: {path}")


if __name__ == "__main__":
    main()
