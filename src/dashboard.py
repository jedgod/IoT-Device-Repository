"""GreenHouseWatch dashboard control center."""
from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from config import HUMIDITY_MIN, SOIL_MIN, TEMP_MAX_C, TEMP_MIN_C, TEMP_MONTHLY_RANGE_C


def calculate_forecast_metrics(rows):
    temps = [float(r["temperature_c"]) for r in rows]
    if len(temps) < 4:
        return {"forecast_horizon": 0, "mae_c": 0.0, "rmse_c": 0.0, "baseline_model": "insufficient data"}
    errors = []
    for idx in range(3, len(temps)):
        history = temps[idx - 3:idx]
        prediction = sum(history) / len(history)
        errors.append(temps[idx] - prediction)
    mae = sum(abs(e) for e in errors) / len(errors)
    rmse = (sum(e * e for e in errors) / len(errors)) ** 0.5
    return {"forecast_horizon": len(errors), "mae_c": round(mae, 2), "rmse_c": round(rmse, 2), "baseline_model": "rolling average (3-step)"}


def build_irrigation_recommendation(rows):
    if not rows:
        return "No sensor data available"
    latest = rows[-1]
    soil = float(latest["soil_moisture_pct"])
    temperature = float(latest["temperature_c"])
    humidity = float(latest["humidity_pct"])
    if soil < SOIL_MIN and temperature > TEMP_MAX_C:
        return "Irrigate now: soil low and temperature high"
    if soil < SOIL_MIN:
        return "Irrigate now: soil moisture below safe minimum"
    if humidity > HUMIDITY_MIN and temperature > TEMP_MIN_C:
        return "Monitor: conditions are within a safe band"
    return "No irrigation needed"


def build_monthly_temperature_table(rows):
    months = ["September", "October", "November", "December"]
    monthly = {month: [] for month in months}
    for row in rows:
        month_name = datetime.fromtimestamp(row["timestamp"], tz=timezone.utc).strftime("%B")
        if month_name in monthly:
            monthly[month_name].append(float(row["temperature_c"]))
    records = []
    for month in months:
        values = monthly.get(month, [])
        avg_temp = sum(values) / len(values) if values else 0.0
        min_temp = min(values) if values else 0.0
        max_temp = max(values) if values else 0.0
        target = TEMP_MONTHLY_RANGE_C.get(month, {"min_c": 0.0, "max_c": 0.0})
        records.append({"month": month, "avg_temp": round(avg_temp, 2), "min_temp": round(min_temp, 2), "max_temp": round(max_temp, 2), "target_min": target["min_c"], "target_max": target["max_c"]})
    return pd.DataFrame(records)


def build_forecast_table(month_temp_df):
    months = list(month_temp_df["month"])
    forecast_rows = []
    for idx, month in enumerate(months):
        current = float(month_temp_df.loc[month_temp_df["month"] == month, "avg_temp"].iloc[0]) if not month_temp_df.empty else 0.0
        next_month = months[idx + 1] if idx + 1 < len(months) else "January"
        next_target = TEMP_MONTHLY_RANGE_C.get(next_month, {"min_c": current - 2.0, "max_c": current + 2.0})
        expected_temp = round((next_target["min_c"] + next_target["max_c"]) / 2, 2)
        forecast_rows.append({"month": month, "current_temp_c": round(current, 2), "expected_temp_c": expected_temp, "next_month": next_month, "delta_c": round(expected_temp - current, 2), "target_min": next_target["min_c"], "target_max": next_target["max_c"]})
    return pd.DataFrame(forecast_rows)


def set_dashboard_style():
    from dashboard_ui import ASSETS
    st.html(ASSETS / "dashboard.css")


def run_dashboard():
    from dashboard_ui import icon
    st.set_page_config(page_title="GreenHouseWatch", page_icon=":material/eco:", layout="wide", initial_sidebar_state="expanded")
    set_dashboard_style()
    pages = [
        st.Page("dashboard_pages/overview.py", title="Overview", icon=":material/home:", default=True),
        st.Page("dashboard_pages/zones.py", title="Zones", icon=":material/eco:"),
        st.Page("dashboard_pages/analytics.py", title="Analytics", icon=":material/bar_chart:"),
        st.Page("dashboard_pages/forecast.py", title="Forecast", icon=":material/cloud:"),
        st.Page("dashboard_pages/controls.py", title="Controls", icon=":material/settings:"),
        st.Page("dashboard_pages/data_explorer.py", title="Data", icon=":material/database:"),
    ]
    page = st.navigation(pages, position="hidden")
    with st.sidebar:
        st.html(f'<div class="brand">{icon("leaf", "#a4d78e")}<div><strong>GreenHouseWatch</strong><p>Smarter greenhouses<br>healthier harvests</p></div></div>')
        for item in pages:
            st.page_link(item, label=item.title, icon=item.icon, width="stretch")
        st.html(f'<div class="sidebar-footer"><div class="sidebar-motto">{icon("plant", "#74bf88")}<span>Healthy plants<br>brighter tomorrows</span></div><div class="sidebar-status"><span class="dot"></span>System online</div><div>Reference snapshot<br>Sep 16, 2026 &nbsp; 14:32</div><div class="demo-note">SIMULATED GREENHOUSE · DEMO</div></div>')
    page.run()


if __name__ == "__main__":
    run_dashboard()
