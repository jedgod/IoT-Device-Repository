"""GreenHouseWatch dashboard control center."""
from __future__ import annotations

import streamlit as st
from config import HUMIDITY_MIN, SOIL_MIN, TEMP_MAX_C, TEMP_MIN_C


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


def set_dashboard_style():
    from dashboard_ui import ASSETS
    st.html(ASSETS / "dashboard.css")
    st.html(ASSETS / "overview-reference.css")


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
        from dashboard_live import live_sidebar
        live_sidebar()
    page.run()


if __name__ == "__main__":
    run_dashboard()
