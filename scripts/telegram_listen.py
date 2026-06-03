#!/usr/bin/env python3
"""Poll Telegram; set GitHub Actions output push=true when user requests a chart."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from btc_gex.notify import send_telegram_message
from btc_gex.telegram_bot import poll_for_trigger


def _write_github_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def main() -> None:
    triggered = poll_for_trigger()
    if triggered:
        send_telegram_message("正在生成 BTC GEX 图，约 1–2 分钟…")
        _write_github_output("push", "true")
        print("Trigger: on-demand chart requested")
    else:
        _write_github_output("push", "false")
        print("No on-demand request")


if __name__ == "__main__":
    main()
