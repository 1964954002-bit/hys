"""Compute BTC gamma exposure (GEX) from Deribit option chain data."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from btc_gex.deribit import OptionRow

STRIKE_GRID = 500.0


def snap_strike(strike: float, step: float = STRIKE_GRID) -> float:
    """Snap a strike onto the uniform display grid."""
    return round(strike / step) * step


def uniform_strikes(low: float, high: float, step: float = STRIKE_GRID) -> list[float]:
    start = math.floor(low / step) * step
    end = math.ceil(high / step) * step
    strikes: list[float] = []
    value = start
    while value <= end + 1e-9:
        strikes.append(value)
        value += step
    return strikes


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def bsm_gamma(spot: float, strike: float, t_years: float, rate: float, iv: float) -> float:
    if t_years <= 0 or iv <= 0 or spot <= 0 or strike <= 0:
        return 0.0
    d1 = (math.log(spot / strike) + (rate + 0.5 * iv * iv) * t_years) / (iv * math.sqrt(t_years))
    return _norm_pdf(d1) / (spot * iv * math.sqrt(t_years))


def contract_gex(
    spot: float,
    strike: float,
    t_years: float,
    rate: float,
    iv: float,
    open_interest: float,
    option_type: str,
) -> float:
    """
    Dollar GEX for one Deribit BTC option row.

    Deribit contracts are 1 BTC each, so the equity-style 100-share multiplier
    is replaced with 1. Sign convention matches SpotGamma:
      calls -> positive dealer GEX contribution
      puts  -> negative dealer GEX contribution
    """
    gamma = bsm_gamma(spot, strike, t_years, rate, iv)
    raw = gamma * open_interest * spot * spot * 0.01
    return raw if option_type.upper() == "C" else -raw


@dataclass(frozen=True)
class StrikeGex:
    strike: float
    call_gex: float
    put_gex: float
    net_gex: float


@dataclass(frozen=True)
class HeatmapData:
    expiries: list[datetime]
    strikes: list[float]
    values: list[list[float]]


@dataclass(frozen=True)
class DynamicGammaProfile:
    """Total net GEX if spot were at each hypothetical price level."""

    prices: list[float]
    net_gex: list[float]
    flip_price: float | None


@dataclass(frozen=True)
class GexSnapshot:
    as_of: datetime
    spot: float
    net_gex: float
    call_gex: float
    put_gex: float
    gamma_flip: float | None
    static_gamma_flip: float | None
    king_strike: float
    king_gex: float
    regime: str
    regime_cn: str
    strikes: list[StrikeGex]
    heatmap: HeatmapData
    dynamic_profile: DynamicGammaProfile
    contracts_used: int


def _years_to_expiry(now: datetime, expiry: datetime) -> float:
    seconds = max((expiry - now).total_seconds(), 60.0)
    return seconds / (365.0 * 24.0 * 3600.0)


def compute_gamma_flip(strikes: list[StrikeGex], spot: float) -> float | None:
    """
    Gamma flip = zero crossing of the per-strike net GEX profile
    (all expiries aggregated) closest to spot.
    """
    rows = sorted(strikes, key=lambda item: item.strike)
    flips: list[float] = []
    for index in range(1, len(rows)):
        left = rows[index - 1]
        right = rows[index]
        if left.net_gex * right.net_gex >= 0:
            continue
        weight = -left.net_gex / (right.net_gex - left.net_gex)
        flips.append(left.strike + (right.strike - left.strike) * weight)

    if not flips:
        return None
    return min(flips, key=lambda flip: abs(flip - spot))


def compute_dynamic_gamma_profile(
    chain: list[OptionRow],
    spot: float,
    now: datetime,
    *,
    window_pct: float = 0.12,
    step: float = 250.0,
) -> DynamicGammaProfile:
    """
    Recompute total net GEX at hypothetical spot levels.

    As price moves, each option's gamma changes, so total dealer GEX traces
    a smooth curve (often S-shaped). Its zero crossing is the dynamic
    gamma flip — the level where dealer hedging switches regime.
    """
    low = spot * (1.0 - window_pct)
    high = spot * (1.0 + window_pct)
    prices: list[float] = []
    values: list[float] = []

    price = low
    while price <= high + 1e-6:
        total = 0.0
        for row in chain:
            t_years = _years_to_expiry(now, row.expiry)
            iv = row.mark_iv / 100.0
            total += contract_gex(
                price,
                row.strike,
                t_years,
                row.interest_rate,
                iv,
                row.open_interest,
                row.option_type,
            )
        prices.append(price)
        values.append(total)
        price += step

    flips: list[float] = []
    for index in range(1, len(values)):
        left_value = values[index - 1]
        right_value = values[index]
        if left_value * right_value >= 0:
            continue
        left_price = prices[index - 1]
        right_price = prices[index]
        weight = -left_value / (right_value - left_value)
        flips.append(left_price + (right_price - left_price) * weight)

    flip_price = min(flips, key=lambda flip: abs(flip - spot)) if flips else None
    return DynamicGammaProfile(prices=prices, net_gex=values, flip_price=flip_price)


def _build_heatmap(
    by_cell: dict[tuple[float, datetime], float],
    spot: float,
    now: datetime,
    *,
    strike_window_pct: float = 0.10,
    max_expiries: int = 14,
) -> HeatmapData:
    if not by_cell:
        return HeatmapData(expiries=[], strikes=[], values=[])

    low = spot * (1.0 - strike_window_pct)
    high = spot * (1.0 + strike_window_pct)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    expiries = sorted({expiry for (_, expiry) in by_cell if expiry >= today})
    expiries = expiries[:max_expiries]

    strikes = uniform_strikes(low, high, STRIKE_GRID)
    values = [
        [by_cell.get((strike, expiry), 0.0) for expiry in expiries]
        for strike in strikes
    ]
    return HeatmapData(expiries=expiries, strikes=strikes, values=values)


def compute_gex_snapshot(
    chain: list[OptionRow],
    spot: float | None = None,
    now: datetime | None = None,
    *,
    strike_window_pct: float = 0.12,
    max_expiries: int = 12,
) -> GexSnapshot:
    now = now or datetime.now(timezone.utc)
    spot = spot or (chain[0].underlying_price if chain else 0.0)

    by_strike: dict[float, StrikeGex] = {}
    by_cell: dict[tuple[float, datetime], float] = {}
    total_call = 0.0
    total_put = 0.0

    for row in chain:
        t_years = _years_to_expiry(now, row.expiry)
        iv = row.mark_iv / 100.0
        rate = row.interest_rate
        gex = contract_gex(spot, row.strike, t_years, rate, iv, row.open_interest, row.option_type)
        binned_strike = snap_strike(row.strike)

        cell_key = (binned_strike, row.expiry)
        by_cell[cell_key] = by_cell.get(cell_key, 0.0) + gex

        current = by_strike.get(
            binned_strike,
            StrikeGex(strike=binned_strike, call_gex=0.0, put_gex=0.0, net_gex=0.0),
        )
        if row.option_type == "C":
            current = StrikeGex(
                strike=binned_strike,
                call_gex=current.call_gex + gex,
                put_gex=current.put_gex,
                net_gex=current.net_gex + gex,
            )
            total_call += gex
        else:
            current = StrikeGex(
                strike=binned_strike,
                call_gex=current.call_gex,
                put_gex=current.put_gex + gex,
                net_gex=current.net_gex + gex,
            )
            total_put += gex
        by_strike[binned_strike] = current

    strikes = sorted(by_strike.values(), key=lambda item: item.strike)
    net_gex = total_call + total_put

    static_gamma_flip = compute_gamma_flip(strikes, spot)
    dynamic_profile = compute_dynamic_gamma_profile(chain, spot, now)
    gamma_flip = dynamic_profile.flip_price or static_gamma_flip

    king = max(strikes, key=lambda item: abs(item.net_gex))
    if net_gex >= 0:
        regime = "POSITIVE_GEX"
        regime_cn = "震荡偏好：做市商偏 long gamma，倾向压波动、均值回归"
    else:
        regime = "NEGATIVE_GEX"
        regime_cn = "加速偏好：做市商偏 short gamma，波动易放大、趋势更易延续"

    heatmap = _build_heatmap(
        by_cell,
        spot,
        now,
        strike_window_pct=strike_window_pct,
        max_expiries=max_expiries,
    )

    return GexSnapshot(
        as_of=now,
        spot=spot,
        net_gex=net_gex,
        call_gex=total_call,
        put_gex=total_put,
        gamma_flip=gamma_flip,
        static_gamma_flip=static_gamma_flip,
        king_strike=king.strike,
        king_gex=king.net_gex,
        regime=regime,
        regime_cn=regime_cn,
        strikes=strikes,
        heatmap=heatmap,
        dynamic_profile=dynamic_profile,
        contracts_used=len(chain),
    )
