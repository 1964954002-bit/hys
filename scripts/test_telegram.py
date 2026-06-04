#!/usr/bin/env python3
"""Send a short test message to verify Telegram secrets (no chart)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests

from btc_gex.notify import send_telegram_message

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _verify_bot_token(token: str) -> str:
    response = requests.get(TELEGRAM_API.format(token=token, method="getMe"), timeout=30)
    payload = response.json()
    if not response.ok or not payload.get("ok"):
        description = payload.get("description", response.text)
        raise SystemExit(
            f"ERROR: Bot token is invalid ({response.status_code}): {description}\n"
            "Fix: BotFather → /mybots → your bot → API Token, or /revoke then update "
            "GitHub secret TELEGRAM_BOT_TOKEN."
        )
    result = payload.get("result", {})
    username = result.get("username", "?")
    bot_user_id = str(result.get("id", ""))
    return username, bot_user_id


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
    if not chat_id.lstrip("-").isdigit():
        raise SystemExit(
            f"ERROR: TELEGRAM_CHAT_ID must be digits only, got: {chat_id!r}\n"
            "Fix: open https://api.telegram.org/bot<token>/getUpdates after messaging your bot."
        )
    if ":" not in token:
        raise SystemExit(
            "ERROR: TELEGRAM_BOT_TOKEN looks wrong (expected format 123456:AA...).\n"
            "Fix: copy the full token from BotFather, not your GitHub token."
        )

    print(f"Token length: {len(token)}, chat_id: {chat_id}")
    bot_name, bot_user_id = _verify_bot_token(token)
    print(f"Bot token OK (@{bot_name}, bot id={bot_user_id})")
    if chat_id == bot_user_id:
        raise SystemExit(
            "ERROR: TELEGRAM_CHAT_ID is the BOT's id, not yours.\n"
            "Fix: message your bot in Telegram (send hi), then getUpdates — "
            "use the id inside message.chat.id (your account), NOT the bot id."
        )
    send_telegram_message("BTC GEX bot test OK. Secrets work.")
    print("SUCCESS: test message sent to Telegram.")


if __name__ == "__main__":
    main()
