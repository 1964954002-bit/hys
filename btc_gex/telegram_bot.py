"""Poll Telegram for on-demand chart commands."""

from __future__ import annotations

import os
from pathlib import Path

import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

TRIGGER_COMMANDS = frozenset(
    {
        "发图",
        "画图",
        "/发图",
        "chart",
        "push",
        "/chart",
        "/push",
    }
)


def _api(token: str, method: str) -> str:
    return TELEGRAM_API.format(token=token, method=method)


def load_update_offset(path: str | Path) -> int:
    offset_path = Path(path)
    if not offset_path.is_file():
        return 0
    raw = offset_path.read_text(encoding="utf-8").strip()
    return int(raw) if raw.isdigit() else 0


def save_update_offset(path: str | Path, offset: int) -> None:
    offset_path = Path(path)
    offset_path.parent.mkdir(parents=True, exist_ok=True)
    offset_path.write_text(str(offset), encoding="utf-8")


def is_trigger_command(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    if cleaned in TRIGGER_COMMANDS:
        return True
    return cleaned.lower() in TRIGGER_COMMANDS


def fetch_updates(token: str, *, offset: int = 0, timeout: int = 0) -> list[dict]:
    response = requests.get(
        _api(token, "getUpdates"),
        params={"offset": offset, "timeout": timeout},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram getUpdates error: {payload}")
    return payload.get("result", [])


def next_offset(updates: list[dict], current_offset: int) -> int:
    if not updates:
        return current_offset
    return max(current_offset, max(item["update_id"] for item in updates) + 1)


def find_trigger_request(
    updates: list[dict],
    *,
    authorized_chat_id: str,
) -> bool:
    for item in updates:
        message = item.get("message") or item.get("edited_message")
        if not message:
            continue
        chat = message.get("chat") or {}
        if str(chat.get("id")) != str(authorized_chat_id):
            continue
        text = message.get("text") or ""
        if is_trigger_command(text):
            return True
    return False


def poll_for_trigger(
    *,
    token: str | None = None,
    chat_id: str | None = None,
    offset_file: str | Path | None = None,
) -> bool:
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    offset_file = Path(
        offset_file or os.environ.get("TELEGRAM_OFFSET_FILE", ".cache/telegram_update_offset")
    )
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
    if not chat_id:
        raise RuntimeError("Missing TELEGRAM_CHAT_ID")

    offset = load_update_offset(offset_file)
    updates = fetch_updates(token, offset=offset)
    triggered = find_trigger_request(updates, authorized_chat_id=chat_id)
    save_update_offset(offset_file, next_offset(updates, offset))
    return triggered
