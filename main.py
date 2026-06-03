#!/usr/bin/env python3
"""Check BTC dealer gamma regime from Deribit options data."""

from __future__ import annotations

import argparse

from btc_gex.deribit import fetch_btc_option_chain, fetch_index_price
from btc_gex.gex import compute_gex_snapshot
from btc_gex.heatmap import render_gex_heatmap


def _format_usd(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"${value / 1_000:.2f}K"
    return f"${value:,.0f}"


def print_snapshot(snapshot) -> None:
    print()
    print("=== BTC Dealer Gamma Regime (Deribit) ===")
    print(f"As of UTC     : {snapshot.as_of.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Spot          : ${snapshot.spot:,.2f}")
    print(f"Contracts used: {snapshot.contracts_used:,}")
    print()
    print(f"Net GEX       : {_format_usd(snapshot.net_gex)}")
    print(f"Call GEX      : {_format_usd(snapshot.call_gex)}")
    print(f"Put GEX       : {_format_usd(snapshot.put_gex)}")
    print(f"Gamma Flip    : {snapshot.gamma_flip:,.0f} (dynamic)" if snapshot.gamma_flip else "Gamma Flip    : n/a")
    if snapshot.static_gamma_flip and snapshot.static_gamma_flip != snapshot.gamma_flip:
        print(f"Static Flip   : {snapshot.static_gamma_flip:,.0f} (strike profile)")
    print(f"King Strike   : ${snapshot.king_strike:,.0f} ({_format_usd(snapshot.king_gex)})")
    print()
    print(f"Regime        : {snapshot.regime}")
    print(f"Interpretation: {snapshot.regime_cn}")
    print()

    near_spot = sorted(snapshot.strikes, key=lambda item: abs(item.strike - snapshot.spot))[:5]
    print("Top strikes near spot:")
    for row in near_spot:
        print(
            f"  ${row.strike:>8,.0f}  net={_format_usd(row.net_gex):>10}  "
            f"call={_format_usd(row.call_gex):>10}  put={_format_usd(row.put_gex):>10}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="BTC GEX regime checker (Deribit source)")
    parser.add_argument("--currency", default="BTC", help="Deribit currency, default BTC")
    parser.add_argument(
        "--heatmap",
        action="store_true",
        help="Save strike x expiry GEX heatmap PNG",
    )
    parser.add_argument(
        "--output",
        default="output/btc_gex_heatmap.png",
        help="Heatmap output path (default: output/btc_gex_heatmap.png)",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Open heatmap window after saving",
    )
    args = parser.parse_args()

    chain = fetch_btc_option_chain(args.currency)
    spot = fetch_index_price("btc_usd")
    snapshot = compute_gex_snapshot(chain, spot=spot)
    print_snapshot(snapshot)

    if args.heatmap:
        path = render_gex_heatmap(snapshot, args.output, show=args.show)
        print(f"Heatmap saved: {path}")


if __name__ == "__main__":
    main()
