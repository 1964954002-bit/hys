"""Render BTC GEX dashboard: static profile, dynamic gamma curve, heatmap."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from matplotlib.gridspec import GridSpec

from btc_gex.gex import STRIKE_GRID, GexSnapshot


def _format_expiry_label(expiry: datetime) -> str:
    return expiry.strftime("%d %b %y")


def _format_gex_m(value: float) -> str:
    return f"{value / 1e6:+.1f}M"


def _robust_color_limit(matrix: np.ndarray, percentile: float = 92.0) -> float:
    nonzero = np.abs(matrix[np.nonzero(matrix)])
    if nonzero.size == 0:
        return 1.0
    return float(max(np.percentile(nonzero, percentile), 1.0))


def _axis_edges(centers: np.ndarray) -> np.ndarray:
    """Build cell boundary edges from center coordinates."""
    if centers.size == 0:
        return np.array([])
    if centers.size == 1:
        half = max(float(centers[0]) * 0.005, 1.0)
        return np.array([centers[0] - half, centers[0] + half], dtype=float)

    mids = (centers[:-1] + centers[1:]) / 2.0
    edges = np.empty(centers.size + 1, dtype=float)
    edges[0] = centers[0] - (mids[0] - centers[0])
    edges[-1] = centers[-1] + (centers[-1] - mids[-1])
    edges[1:-1] = mids
    return edges


def _strike_edges(strikes: list[float]) -> np.ndarray:
    return _axis_edges(np.array(strikes, dtype=float))


def _draw_price_line(ax, price: float, *, color: str, label: str | None = None, linestyle: str = "--") -> None:
    ax.axhline(price, color=color, linewidth=1.5, linestyle=linestyle, alpha=0.95)
    if label:
        ax.text(
            0.02,
            price,
            label,
            color=color,
            fontsize=8,
            ha="left",
            va="bottom",
            fontweight="bold",
            clip_on=False,
        )


def _plot_dynamic_gamma_curve(ax, snapshot: GexSnapshot) -> None:
    profile = snapshot.dynamic_profile
    prices = np.array(profile.prices)
    values = np.array(profile.net_gex)
    if prices.size == 0:
        return

    x_limit = max(float(np.max(np.abs(values))) * 1.15, 1.0)
    ax.axvline(0.0, color="#888888", linewidth=1.0, alpha=0.8)
    ax.fill_betweenx(prices, 0, values, where=values >= 0, color="#1a9850", alpha=0.18)
    ax.fill_betweenx(prices, 0, values, where=values < 0, color="#d73027", alpha=0.18)
    ax.plot(values, prices, color="#b388ff", linewidth=2.2, label="Dynamic net GEX")

    current_index = int(np.argmin(np.abs(prices - snapshot.spot)))
    ax.scatter(
        [values[current_index]],
        [prices[current_index]],
        s=48,
        color="#ffffff",
        edgecolors="#111111",
        linewidths=0.8,
        zorder=5,
    )

    if snapshot.gamma_flip is not None:
        _draw_price_line(
            ax,
            snapshot.gamma_flip,
            color="#00bcd4",
            label=f"Flip ${snapshot.gamma_flip:,.0f}",
        )

    _draw_price_line(ax, snapshot.spot, color="#ffffff", label=f"Spot ${snapshot.spot:,.0f}")
    _draw_price_line(
        ax,
        snapshot.king_strike,
        color="#ffd700",
        label=f"King ${snapshot.king_strike:,.0f}",
        linestyle="-",
    )

    ax.set_xlim(-x_limit, x_limit)
    ax.set_xlabel("Dynamic Net GEX", color="#cccccc")
    ax.set_title("Dynamic Gamma Profile", color="#f2f2f2", fontsize=11, loc="left")
    ax.tick_params(axis="x", colors="#cccccc")
    ax.tick_params(axis="y", labelleft=False, colors="#cccccc")
    ax.grid(axis="x", color="#2a3142", alpha=0.45, linewidth=0.6)


def render_gex_heatmap(
    snapshot: GexSnapshot,
    output_path: str | Path,
    *,
    show: bool = False,
) -> Path:
    heatmap = snapshot.heatmap
    if not heatmap.strikes or not heatmap.expiries:
        raise ValueError("No heatmap data to render.")

    matrix = np.array(heatmap.values, dtype=float)
    strikes = heatmap.strikes
    y_edges = _strike_edges(strikes)
    y_min = float(y_edges[0])
    y_max = float(y_edges[-1])
    vmax = _robust_color_limit(matrix)

    strike_lookup = {row.strike: row for row in snapshot.strikes}
    profile_strikes = strikes
    profile_values = [strike_lookup[strike].net_gex if strike in strike_lookup else 0.0 for strike in strikes]
    bar_heights = [float(y_edges[index + 1] - y_edges[index]) * 0.88 for index in range(len(strikes))]

    fig = plt.figure(figsize=(15, 11), facecolor="#0f1117")
    gs = GridSpec(
        2,
        3,
        figure=fig,
        height_ratios=[1.0, 2.2],
        width_ratios=[3.2, 1.5, 0.16],
        hspace=0.08,
        wspace=0.06,
    )
    ax_profile = fig.add_subplot(gs[0, 0])
    ax_dynamic = fig.add_subplot(gs[:, 1], sharey=ax_profile)
    ax_map = fig.add_subplot(gs[1, 0], sharey=ax_profile)
    ax_cbar = fig.add_subplot(gs[1, 2])

    for axis in (ax_profile, ax_map, ax_dynamic, ax_cbar):
        axis.set_facecolor("#0f1117")

    colors = ["#d73027" if value < 0 else "#1a9850" for value in profile_values]
    ax_profile.barh(
        profile_strikes,
        profile_values,
        height=bar_heights,
        color=colors,
        alpha=0.92,
        align="center",
        edgecolor="#1b1f2a",
        linewidth=0.4,
    )
    ax_profile.axvline(0.0, color="#cccccc", linewidth=1.0, alpha=0.8)
    ax_profile.set_xlim(-vmax * 1.15, vmax * 1.15)
    ax_profile.set_ylim(y_min, y_max)
    ax_profile.tick_params(axis="x", colors="#cccccc")
    ax_profile.tick_params(axis="y", labelleft=False, colors="#cccccc")
    ax_profile.grid(axis="x", color="#2a3142", alpha=0.45, linewidth=0.6)
    ax_profile.set_title("BTC GEX Dashboard (Deribit)", color="#f2f2f2", fontsize=14, loc="left", pad=12)
    regime_label = "Mean-reversion" if snapshot.net_gex >= 0 else "Vol expansion"
    ax_profile.text(
        0.0,
        1.02,
        f"Spot ${snapshot.spot:,.0f}  |  Net GEX {_format_gex_m(snapshot.net_gex)}  |  {regime_label}",
        transform=ax_profile.transAxes,
        color="#b8bcc8",
        fontsize=10,
        ha="left",
        va="bottom",
    )
    ax_profile.text(
        0.0,
        1.12,
        "Static GEX by Strike",
        transform=ax_profile.transAxes,
        color="#888888",
        fontsize=9,
        ha="left",
    )

    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    x_edges = np.arange(len(heatmap.expiries) + 1, dtype=float)
    mesh = ax_map.pcolormesh(
        x_edges,
        y_edges,
        matrix,
        cmap="RdYlGn",
        norm=norm,
        shading="flat",
    )

    ax_map.set_xlim(0.0, float(len(heatmap.expiries)))
    ax_map.set_ylim(y_min, y_max)
    ax_map.set_xticks(np.arange(len(heatmap.expiries)) + 0.5)
    ax_map.set_xticklabels(
        [_format_expiry_label(expiry) for expiry in heatmap.expiries],
        rotation=45,
        ha="right",
        color="#cccccc",
    )
    ax_map.set_yticks(strikes[::2])
    ax_map.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"${value:,.0f}"))
    ax_map.tick_params(axis="x", colors="#cccccc")
    ax_map.tick_params(axis="y", colors="#cccccc")
    ax_map.set_xlabel("Expiration", color="#cccccc")
    ax_map.set_ylabel("Strike", color="#cccccc")

    _plot_dynamic_gamma_curve(ax_dynamic, snapshot)

    cbar = fig.colorbar(mesh, cax=ax_cbar)
    cbar.set_label("Static Net GEX", color="#cccccc")
    cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: _format_gex_m(value)))
    cbar.ax.tick_params(colors="#cccccc")

    legend_handles = [
        mpatches.Patch(color="#b388ff", label="Dynamic gamma curve"),
        mpatches.Patch(color="#1a9850", label="Positive GEX"),
        mpatches.Patch(color="#d73027", label="Negative GEX"),
        mpatches.Patch(facecolor="none", edgecolor="#00bcd4", label="Gamma Flip"),
        mpatches.Patch(facecolor="none", edgecolor="#ffd700", label="King Strike"),
    ]
    ax_dynamic.legend(
        handles=legend_handles,
        loc="lower right",
        frameon=False,
        fontsize=8,
        labelcolor="#cccccc",
    )

    fig.text(
        0.01,
        0.01,
        f"Updated UTC {snapshot.as_of.strftime('%Y-%m-%d %H:%M')}  |  "
        f"Strike grid = ${STRIKE_GRID:,.0f} uniform  |  "
        "X-axis = one column per expiry  |  "
        "Zero crossing on right curve = dynamic gamma flip",
        fontsize=8,
        color="#888888",
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=170, bbox_inches="tight", facecolor=fig.get_facecolor())
    if show:
        plt.show()
    plt.close(fig)
    return output_path
