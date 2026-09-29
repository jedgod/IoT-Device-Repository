"""
Phase 5 — visualizations from SQLite across real time scales.

Reads the weather-driven zone history (see build_history.py) and the matching
Open-Meteo outdoor weather, in local Bowie, MD time, and writes to ../outputs/:

  01_last_7_days_hourly.png        days     — hour-by-hour detail for the latest week
  02_daily_cycle_by_season.png     days     — the average 24-hour cycle in each season
  03_daily_temperature_year.png    days     — every day's low / mean / high over the year
  04_monthly_summary.png           months   — monthly means and hours outside target
  05_quarterly_summary.png         quarters — share of hours outside each target
  06_year_calendar.png             year     — calendar of daily hours outside target
  07_indoor_vs_outdoor.png         year     — how far the controls hold against the weather

It also writes the table view behind the charts: monthly_summary.csv and
quarterly_summary.csv.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from config import HISTORY_ZONES, OUTPUT_DIR, SITE_TIMEZONE, ZONE_COLORS, ZONE_PROFILES
from db import connect

HISTORY_SOURCE = "weather model"

OUTDOOR = "#898781"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
BLUES = LinearSegmentedColormap.from_list(
    "blues", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
SEASONS = {"Winter (Dec–Feb)": (12, 1, 2), "Spring (Mar–May)": (3, 4, 5),
           "Summer (Jun–Aug)": (6, 7, 8), "Autumn (Sep–Nov)": (9, 10, 11)}


def _style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
        "text.color": INK, "axes.labelcolor": INK_2, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.grid": True, "grid.color": GRID,
        "grid.linewidth": 0.6, "axes.axisbelow": True, "axes.spines.top": False,
        "axes.spines.right": False, "axes.titlesize": 11, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "legend.frameon": False,
    })


def _label(zone_id: str) -> str:
    return ZONE_PROFILES[zone_id]["label"]


def load(conn) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hourly zone history with target checks, and hourly outdoor weather, in local time."""
    zones = pd.read_sql_query("SELECT * FROM greenhouse_zones", conn).set_index("zone_id")
    marks = ",".join("?" * len(HISTORY_ZONES))
    data = pd.read_sql_query(
        f"SELECT zone_id, measured_at, temperature_c, humidity_pct, soil_moisture_pct, light_lux, "
        f"nutrient_level, ph_scale FROM zone_telemetry WHERE source = ? AND zone_id IN ({marks})",
        conn, params=[HISTORY_SOURCE, *HISTORY_ZONES])
    if data.empty:
        raise SystemExit("No weather-driven history found. Run: python src/build_history.py")
    data["time"] = pd.to_datetime(data.measured_at, utc=True).dt.tz_convert(SITE_TIMEZONE)
    bounds = zones.loc[data.zone_id]
    data["temp_ok"] = data.temperature_c.between(bounds.temp_min_c.values, bounds.temp_max_c.values)
    data["humidity_ok"] = data.humidity_pct.between(bounds.humidity_min.values, bounds.humidity_max.values)
    data["soil_ok"] = data.soil_moisture_pct.values >= bounds.soil_min.values
    data["all_ok"] = data.temp_ok & data.humidity_ok & data.soil_ok
    # Keep whole local days only: UTC-aligned data would otherwise leave a stub evening/month.
    first, last = data.time.min(), data.time.max()
    start = first.normalize() if first.hour == 0 else first.normalize() + pd.Timedelta(days=1)
    end = last.normalize() + pd.Timedelta(days=1) if last.hour == 23 else last.normalize()
    data = data[(data.time >= start) & (data.time < end)]
    outdoor = pd.read_sql_query("SELECT * FROM outdoor_weather", conn)
    outdoor["time"] = pd.to_datetime(outdoor.measured_at, utc=True).dt.tz_convert(SITE_TIMEZONE)
    outdoor = outdoor[(outdoor.time >= start) & (outdoor.time < end)]
    return data.sort_values("time"), outdoor.sort_values("time")


def _subtitle(fig, data: pd.DataFrame, extra: str = "") -> None:
    span = f"{data.time.min():%d %b %Y} – {data.time.max():%d %b %Y}"
    text = (f"Indoor values modelled from real hourly Bowie, MD weather (Open-Meteo archive), {span}. "
            f"Local time. {extra}").strip()
    fig.text(0.012, 1 - 0.42 / fig.get_figheight(), text, ha="left", va="top", fontsize=9, color=INK_2)


def _title(fig, text: str) -> None:
    fig.text(0.012, 1 - 0.1 / fig.get_figheight(), text, ha="left", va="top", fontsize=14, fontweight="bold", color=INK)


def _zone_legend(fig, outdoor: bool = True) -> None:
    y = 1 - 0.68 / fig.get_figheight()
    handles = [plt.Line2D([], [], color=ZONE_COLORS[z], linewidth=2, label=_label(z)) for z in HISTORY_ZONES]
    if outdoor:
        handles.append(plt.Line2D([], [], color=OUTDOOR, linewidth=1.4, label="Outdoor"))
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.008, y), ncol=len(handles),
               fontsize=9, handlelength=1.8, columnspacing=1.4)


def _end_labels(ax, points: list[tuple[str, float, str]], x) -> None:
    """Direct-label line ends, nudged apart so labels never collide."""
    low, high = ax.get_ylim()
    gap = (high - low) * 0.07
    points = sorted(points, key=lambda p: p[1])
    placed: list[float] = []
    for _, y, _ in points:
        placed.append(max(y, placed[-1] + gap) if placed else y)
    # Pushing labels apart only moves them up; re-centre the stack on the true values.
    shift = sum(p[1] for p in points) / len(points) - sum(placed) / len(placed)
    for (text, _, _), y in zip(points, placed):
        ax.annotate(text, (x, y + shift), xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=8.5, color=INK_2, annotation_clip=False)


def _save(fig, out_dir: Path, name: str, saved: list[Path]) -> None:
    path = out_dir / name
    fig.savefig(path, dpi=140)
    plt.close(fig)
    saved.append(path)


def week_hourly(data, outdoor, out_dir, saved):
    end = data.time.max().normalize() + pd.Timedelta(days=1)
    start = end - pd.Timedelta(days=7)
    week = data[(data.time >= start) & (data.time < end)]
    out = outdoor[(outdoor.time >= start) & (outdoor.time < end)]
    panels = [("temperature_c", "Temperature (°C)", "temperature_c"),
              ("humidity_pct", "Relative humidity (%)", "humidity_pct"),
              ("soil_moisture_pct", "Soil moisture (%)", None)]
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    fig.subplots_adjust(top=0.86, bottom=0.07, left=0.07, right=0.9, hspace=0.28)
    for ax, (field, title, outdoor_field) in zip(axes, panels):
        if outdoor_field:
            ax.plot(out.time, out[outdoor_field], color=OUTDOOR, linewidth=1.2)
        ends = []
        for zone_id in HISTORY_ZONES:
            series = week[week.zone_id == zone_id]
            ax.plot(series.time, series[field], color=ZONE_COLORS[zone_id], linewidth=1.6)
            ends.append((_label(zone_id), series[field].iloc[-1], ZONE_COLORS[zone_id]))
        if outdoor_field:
            ends.append(("Outdoor", out[outdoor_field].iloc[-1], OUTDOOR))
        ax.set_title(title)
        _end_labels(ax, ends, week.time.max())
    axes[-1].xaxis.set_major_locator(mdates.DayLocator(tz=week.time.dt.tz))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b", tz=week.time.dt.tz))
    _title(fig, "Last 7 days, hour by hour: heating and venting hold the air; irrigation resets the soil each morning")
    _subtitle(fig, data, "Soil drops through each day and is refilled at 06:00.")
    _zone_legend(fig)
    _save(fig, out_dir, "01_last_7_days_hourly.png", saved)


def daily_cycle(data, outdoor, out_dir, saved):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True)
    fig.subplots_adjust(top=0.84, bottom=0.08, left=0.07, right=0.97, hspace=0.3, wspace=0.08)
    for ax, (season, months) in zip(axes.flat, SEASONS.items()):
        subset = data[data.time.dt.month.isin(months)]
        out = outdoor[outdoor.time.dt.month.isin(months)]
        profile = out.groupby(out.time.dt.hour).temperature_c.mean()
        ax.plot(profile.index, profile.values, color=OUTDOOR, linewidth=1.4)
        for zone_id in HISTORY_ZONES:
            zone = subset[subset.zone_id == zone_id]
            curve = zone.groupby(zone.time.dt.hour).temperature_c.mean()
            ax.plot(curve.index, curve.values, color=ZONE_COLORS[zone_id], linewidth=2)
        ax.set_title(season)
        ax.set_xticks(range(0, 24, 3))
        ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)])
        ax.set_xlim(0, 23)
    for ax in axes[:, 0]:
        ax.set_ylabel("Mean temperature (°C)")
    _title(fig, "Average day by season: the house stays near crop targets while outdoor air swings")
    _subtitle(fig, data, "Hourly means for each hour of the day.")
    _zone_legend(fig)
    _save(fig, out_dir, "02_daily_cycle_by_season.png", saved)


def daily_year(data, outdoor, out_dir, saved):
    daily = data.groupby(["zone_id", data.time.dt.date]).temperature_c.agg(["min", "mean", "max"]).reset_index()
    daily["time"] = pd.to_datetime(daily.time)
    out = outdoor.groupby(outdoor.time.dt.date).temperature_c.mean()
    out.index = pd.to_datetime(out.index)
    fig, axes = plt.subplots(3, 1, figsize=(12, 9.5), sharex=True, sharey=True)
    fig.subplots_adjust(top=0.86, bottom=0.06, left=0.07, right=0.97, hspace=0.32)
    for ax, zone_id in zip(axes, HISTORY_ZONES):
        p, zone = ZONE_PROFILES[zone_id], daily[daily.zone_id == zone_id]
        ax.axhspan(p["temp_min_c"], p["temp_max_c"], color=GRID, alpha=0.55, linewidth=0)
        ax.plot(out.index, out.values, color=OUTDOOR, linewidth=1)
        ax.fill_between(zone.time, zone["min"], zone["max"], color=ZONE_COLORS[zone_id], alpha=0.22, linewidth=0)
        ax.plot(zone.time, zone["mean"], color=ZONE_COLORS[zone_id], linewidth=1.6)
        ax.set_title(f"{_label(zone_id)} · target {p['temp_min_c']:g}–{p['temp_max_c']:g} °C (grey band)")
        ax.set_ylabel("°C")
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    _title(fig, "Every day of the year: winter is held at target; summer highs break through")
    _subtitle(fig, data, "Line = daily mean, shading = daily low to high, grey line = outdoor daily mean.")
    _zone_legend(fig)
    _save(fig, out_dir, "03_daily_temperature_year.png", saved)


def period_summary(data, outdoor, freq: str) -> pd.DataFrame:
    naive = data.time.dt.tz_localize(None)
    period = naive.dt.to_period(freq)
    summary = data.assign(period=period).groupby(["period", "zone_id"]).agg(
        hours=("temperature_c", "size"),
        temperature_mean_c=("temperature_c", "mean"), temperature_min_c=("temperature_c", "min"),
        temperature_max_c=("temperature_c", "max"), humidity_mean_pct=("humidity_pct", "mean"),
        soil_moisture_mean_pct=("soil_moisture_pct", "mean"), light_mean_lux=("light_lux", "mean"),
        temp_within_pct=("temp_ok", "mean"), humidity_within_pct=("humidity_ok", "mean"),
        soil_within_pct=("soil_ok", "mean"), all_within_pct=("all_ok", "mean"),
    ).reset_index()
    for column in [c for c in summary if c.endswith("_within_pct")]:
        summary[column] *= 100
    summary["outside_target_pct"] = 100 - summary.all_within_pct
    out_period = outdoor.time.dt.tz_localize(None).dt.to_period(freq)
    outdoor_mean = outdoor.groupby(out_period).temperature_c.mean().rename("outdoor_mean_c")
    summary = summary.join(outdoor_mean, on="period")
    summary["zone"] = summary.zone_id.map(_label)
    numeric = summary.select_dtypes("number").columns
    summary[numeric] = summary[numeric].round(2)
    return summary


def monthly(summary, data, out_dir, saved):
    periods = list(summary.period.unique())
    x = np.arange(len(periods))
    labels = [p.strftime("%b\n%Y") if i == 0 or p.month == 1 else p.strftime("%b") for i, p in enumerate(periods)]
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(12, 8.5), sharex=True)
    fig.subplots_adjust(top=0.85, bottom=0.08, left=0.07, right=0.9, hspace=0.3)
    outdoor = summary.drop_duplicates("period").outdoor_mean_c.values
    top.plot(x, outdoor, color=OUTDOOR, linewidth=1.4, marker="o", markersize=4)
    ends = [("Outdoor", outdoor[-1], OUTDOOR)]
    width = 0.26
    for i, zone_id in enumerate(HISTORY_ZONES):
        zone = summary[summary.zone_id == zone_id]
        top.plot(x, zone.temperature_mean_c, color=ZONE_COLORS[zone_id], linewidth=2, marker="o", markersize=5)
        ends.append((_label(zone_id), zone.temperature_mean_c.iloc[-1], ZONE_COLORS[zone_id]))
        bars = bottom.bar(x + (i - 1) * width, zone.outside_target_pct, width=width - 0.03,
                          color=ZONE_COLORS[zone_id])
        worst = zone.outside_target_pct.idxmax()
        bottom.annotate(f"{zone.outside_target_pct[worst]:.0f}%", (x[periods.index(zone.period[worst])] + (i - 1) * width,
                        zone.outside_target_pct[worst]), xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=8, color=INK_2)
    top.set_title("Monthly mean temperature (°C)")
    _end_labels(top, ends, x[-1])
    bottom.set_title("Hours outside any target (%) · largest value per zone labelled")
    bottom.set_ylim(0, 100)
    bottom.set_xticks(x)
    bottom.set_xticklabels(labels)
    _title(fig, "Month by month: out-of-target hours peak in summer heat and in the driest winter weeks")
    _subtitle(fig, data, "A target is temperature, humidity and soil moisture together.")
    _zone_legend(fig)
    _save(fig, out_dir, "04_monthly_summary.png", saved)


def quarterly(summary, data, out_dir, saved):
    rows, labels = [], []
    for zone_id in HISTORY_ZONES:
        zone = summary[summary.zone_id == zone_id]
        for column, name in [("temp_within_pct", "temperature"), ("humidity_within_pct", "humidity"),
                             ("soil_within_pct", "soil moisture"), ("all_within_pct", "any target")]:
            rows.append(100 - zone[column].values)
            labels.append(f"{_label(zone_id)} · {name}")
    grid = np.array(rows)
    periods = list(summary.period.unique())
    hours = summary.drop_duplicates("period").hours.values
    fig, ax = plt.subplots(figsize=(11, 8.5))
    fig.subplots_adjust(top=0.84, bottom=0.06, left=0.24, right=0.97)
    ax.imshow(grid, cmap=BLUES, vmin=0, vmax=100, aspect="auto")
    ax.grid(False)
    for (r, c), value in np.ndenumerate(grid):
        ax.text(c, r, f"{value:.0f}%", ha="center", va="center", fontsize=9,
                color="#ffffff" if value >= 45 else INK)
    ax.set_xticks(range(len(periods)))
    ax.set_xticklabels([f"Q{p.quarter} {p.year}\n{h / 24:.0f} days" for p, h in zip(periods, hours)])
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    for boundary in range(4, len(labels), 4):
        ax.axhline(boundary - 0.5, color=SURFACE, linewidth=4)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    _title(fig, "Quarter by quarter: share of hours outside each target (darker = worse)")
    _subtitle(fig, data, "Calendar quarters; day counts show coverage.")
    _save(fig, out_dir, "05_quarterly_summary.png", saved)


def calendar(data, out_dir, saved):
    days = data.groupby(["zone_id", data.time.dt.date]).all_ok.agg(lambda s: int((~s).sum())).reset_index()
    days["time"] = pd.to_datetime(days.time)
    first = days.time.min() - pd.Timedelta(days=days.time.min().weekday())
    days["week"] = (days.time - first).dt.days // 7
    days["weekday"] = days.time.dt.weekday
    weeks = days.week.max() + 1
    fig, axes = plt.subplots(3, 1, figsize=(13, 7.2))
    fig.subplots_adjust(top=0.83, bottom=0.12, left=0.06, right=0.98, hspace=0.55)
    for ax, zone_id in zip(axes, HISTORY_ZONES):
        grid = np.full((7, weeks), np.nan)
        zone = days[days.zone_id == zone_id]
        grid[zone.weekday, zone.week] = zone.all_ok
        image = ax.imshow(grid, cmap=BLUES, vmin=0, vmax=24, aspect="auto")
        ax.grid(False)
        ax.set_yticks([0, 2, 4, 6])
        ax.set_yticklabels(["Mon", "Wed", "Fri", "Sun"], fontsize=8)
        starts = zone[~zone.time.dt.to_period("M").duplicated()].set_index("week").time
        ax.set_xticks(starts.index)
        ax.set_xticklabels([f"{t:%b}" for t in starts], fontsize=8)
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_title(f"{_label(zone_id)} · {int((zone.all_ok == 0).sum())} of {len(zone)} days fully within target")
    bar = fig.colorbar(image, ax=axes, orientation="horizontal", fraction=0.03, pad=0.1, aspect=60)
    bar.set_label("Hours outside any target that day (0–24)", color=INK_2)
    bar.outline.set_visible(False)
    _title(fig, "The year at a glance: each square is one day")
    _subtitle(fig, data)
    _save(fig, out_dir, "06_year_calendar.png", saved)


def indoor_outdoor(data, outdoor, out_dir, saved):
    out = outdoor.groupby(outdoor.time.dt.date).temperature_c.mean()
    fig, axes = plt.subplots(1, 3, figsize=(13, 5.2), sharex=True, sharey=True)
    fig.subplots_adjust(top=0.78, bottom=0.12, left=0.06, right=0.98, wspace=0.08)
    for ax, zone_id in zip(axes, HISTORY_ZONES):
        p = ZONE_PROFILES[zone_id]
        zone = data[data.zone_id == zone_id].groupby(data.time.dt.date).temperature_c.mean()
        joined = pd.concat([out.rename("outdoor"), zone.rename("indoor")], axis=1).dropna()
        ax.axhspan(p["temp_min_c"], p["temp_max_c"], color=GRID, alpha=0.55, linewidth=0)
        ax.plot([-15, 35], [-15, 35], color=AXIS, linewidth=1)
        ax.scatter(joined.outdoor, joined.indoor, s=16, color=ZONE_COLORS[zone_id], alpha=0.75,
                   edgecolors=SURFACE, linewidths=0.6)
        ax.set_title(f"{_label(zone_id)} · target {p['temp_min_c']:g}–{p['temp_max_c']:g} °C")
        ax.set_xlabel("Outdoor daily mean (°C)")
        ax.set_xlim(joined.outdoor.min() - 2, joined.outdoor.max() + 2)
        ax.set_ylim(min(8, joined.indoor.min() - 1), max(32, joined.indoor.max() + 1))
    axes[0].set_ylabel("Indoor daily mean (°C)")
    axes[-1].annotate("indoor = outdoor", (30, 30), xytext=(-4, 4), textcoords="offset points",
                      ha="right", fontsize=8, color=MUTED)
    _title(fig, "Indoor vs outdoor: flat inside the grey band means the controls are coping")
    _subtitle(fig, data, "One dot per day. Dots rising above the band are days hot enough to beat the cooling.")
    _save(fig, out_dir, "07_indoor_vs_outdoor.png", saved)


def save_all(out_dir: Path | None = None) -> list[Path]:
    out_dir = Path(out_dir or OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = connect()
    data, outdoor = load(conn)
    conn.close()
    _style()
    saved: list[Path] = []
    week_hourly(data, outdoor, out_dir, saved)
    daily_cycle(data, outdoor, out_dir, saved)
    daily_year(data, outdoor, out_dir, saved)
    month_summary = period_summary(data, outdoor, "M")
    quarter_summary = period_summary(data, outdoor, "Q")
    monthly(month_summary, data, out_dir, saved)
    quarterly(quarter_summary, data, out_dir, saved)
    calendar(data, out_dir, saved)
    indoor_outdoor(data, outdoor, out_dir, saved)
    for name, table in [("monthly_summary.csv", month_summary), ("quarterly_summary.csv", quarter_summary)]:
        table.assign(period=table.period.astype(str)).to_csv(out_dir / name, index=False)
        saved.append(out_dir / name)

    print(f"Saved {len(saved)} files to {out_dir}")
    for path in saved:
        print(" ", path.name)
    return saved


if __name__ == "__main__":
    save_all()
