"""
Phase 5 — visualizations from SQLite.

Produces four PNG files in ../outputs/
  01_temperature_over_time.png
  02_humidity_over_time.png
  03_soil_and_light.png
  04_alert_summary.png
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from config import OUTPUT_DIR, TEMP_MAX_C, TEMP_MIN_C, HUMIDITY_MIN, HUMIDITY_MAX, SOIL_MIN
from db import connect, fetch_all


def _style() -> None:
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "#f7faf7",
        "axes.grid": True,
        "grid.alpha": 0.35,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
    })


def _times(rows):
    return [datetime.fromtimestamp(r["timestamp"], tz=timezone.utc) for r in rows]


def save_all(out_dir: Path | None = None) -> list[Path]:
    out_dir = Path(out_dir or OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = fetch_all(connect())
    if len(rows) < 2:
        raise SystemExit("Need at least 2 stored records. Run seed_database.py first.")

    _style()
    times = _times(rows)
    temps = [r["temperature_c"] for r in rows]
    hums = [r["humidity_pct"] for r in rows]
    soils = [r["soil_moisture_pct"] for r in rows]
    lights = [r["light_lux"] for r in rows]
    alerts = [r["alert_flag"] for r in rows]
    saved: list[Path] = []

    # 1. Temperature
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.plot(times, temps, color="#c0392b", linewidth=2, label="Temperature (°C)")
    ax.axhline(TEMP_MAX_C, color="#c0392b", linestyle="--", alpha=0.5, label=f"High limit {TEMP_MAX_C}°C")
    ax.axhline(TEMP_MIN_C, color="#2980b9", linestyle="--", alpha=0.5, label=f"Low limit {TEMP_MIN_C}°C")
    ax.fill_between(times, TEMP_MIN_C, TEMP_MAX_C, color="#27ae60", alpha=0.08, label="Safe band")
    ax.set_title("Greenhouse Temperature Over Time")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Temperature (°C)")
    ax.legend(loc="upper right", frameon=False)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate()
    p = out_dir / "01_temperature_over_time.png"
    fig.tight_layout()
    fig.savefig(p, dpi=140)
    plt.close(fig)
    saved.append(p)

    # 2. Humidity
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.plot(times, hums, color="#1f6f8b", linewidth=2, label="Humidity (%)")
    ax.axhline(HUMIDITY_MIN, color="#d35400", linestyle="--", alpha=0.6, label=f"Low limit {HUMIDITY_MIN}%")
    ax.axhline(HUMIDITY_MAX, color="#8e44ad", linestyle="--", alpha=0.5, label=f"High limit {HUMIDITY_MAX}%")
    ax.set_title("Greenhouse Relative Humidity Over Time")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Humidity (%)")
    ax.legend(loc="upper right", frameon=False)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate()
    p = out_dir / "02_humidity_over_time.png"
    fig.tight_layout()
    fig.savefig(p, dpi=140)
    plt.close(fig)
    saved.append(p)

    # 3. Soil + light (twin axis)
    fig, ax1 = plt.subplots(figsize=(10, 4.8))
    ax1.plot(times, soils, color="#1e8449", linewidth=2, label="Soil moisture (%)")
    ax1.axhline(SOIL_MIN, color="#1e8449", linestyle="--", alpha=0.5, label=f"Dry-soil limit {SOIL_MIN}%")
    ax1.set_ylabel("Soil moisture (%)", color="#1e8449")
    ax1.set_xlabel("Time (UTC)")
    ax2 = ax1.twinx()
    ax2.plot(times, lights, color="#f1c40f", linewidth=2, alpha=0.85, label="Light (lux)")
    ax2.set_ylabel("Light (lux)", color="#b7950b")
    ax1.set_title("Soil Moisture and Light (Irrigation + Day/Night)")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right", frameon=False)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate()
    p = out_dir / "03_soil_and_light.png"
    fig.tight_layout()
    fig.savefig(p, dpi=140)
    plt.close(fig)
    saved.append(p)

    # 4. Alert summary + temp/humidity scatter
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    n_ok = alerts.count(0)
    n_alert = len(alerts) - n_ok
    axes[0].bar(["Normal", "Alert"], [n_ok, n_alert], color=["#27ae60", "#c0392b"])
    axes[0].set_title("Alert vs Normal Readings")
    axes[0].set_ylabel("Count")
    for i, v in enumerate([n_ok, n_alert]):
        axes[0].text(i, v + 0.4, str(v), ha="center", fontweight="bold")

    colors = ["#c0392b" if a else "#1f6f8b" for a in alerts]
    axes[1].scatter(temps, hums, c=colors, alpha=0.75, edgecolors="white", s=36)
    axes[1].set_xlabel("Temperature (°C)")
    axes[1].set_ylabel("Humidity (%)")
    axes[1].set_title("Temperature vs Humidity (red = alert)")
    fig.suptitle("GreenHouseWatch — Condition Summary", fontweight="bold")
    p = out_dir / "04_alert_summary.png"
    fig.tight_layout()
    fig.savefig(p, dpi=140)
    plt.close(fig)
    saved.append(p)

    print(f"Saved {len(saved)} visualizations to {out_dir}")
    for p in saved:
        print(" ", p.name)
    return saved


if __name__ == "__main__":
    save_all()
