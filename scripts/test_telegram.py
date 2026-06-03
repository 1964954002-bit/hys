#!/usr/bin/env python3
"""Send a short test message to verify Telegram secrets (no chart)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from btc_gex.notify import send_telegram_message


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token:
        raise SystemExit(
            "ERROR: TELEGRAM_BOT_TOKEN is empty. "
            "Add it under Settings → Secrets → Actions."
        )
    if not chat_id:
        raise SystemExit(
            "ERROR: TELEGRAM_CHAT_ID is empty. "
            "Use numeric id from getUpdates (message the bot first)."
        )
    print(f"Token length: {len(token)}, chat_id: {chat_id}")
    send_telegram_message("BTC GEX bot test OK. Secrets work.")
    print("SUCCESS: test message sent to Telegram.")


if __name__ == "__main__":
    main()
