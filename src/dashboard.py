"""
Phase 6 (bonus) — Streamlit dashboard.

Usage (from the project root):
    streamlit run src/dashboard.py
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from config import DB_PATH, HUMIDITY_MIN, SOIL_MIN, TEMP_MAX_C, TEMP_MIN_C
from db import connect, count_rows, fetch_all, init_db


st.set_page_config(page_title="GreenHouseWatch", page_icon="🌿", layout="wide")


def load_rows():
    init_db()
    return fetch_all(connect())


rows = load_rows()
st.title("🌿 GreenHouseWatch")
st.caption("CTEC 651 — Local IoT Digital Repository  ·  SQLite + MQTT pipeline")

if not rows:
    st.warning("Database is empty. Run `python src/seed_database.py` first.")
    st.stop()

latest = rows[-1]
n = len(rows)
n_alert = sum(1 for r in rows if r["alert_flag"])

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Readings", n)
c2.metric("Temperature", f"{latest['temperature_c']:.1f} °C")
c3.metric("Humidity", f"{latest['humidity_pct']:.1f} %")
c4.metric("Soil moisture", f"{latest['soil_moisture_pct']:.1f} %")
c5.metric("Alerts", n_alert)

st.divider()
left, right = st.columns(2)

temps = [r["temperature_c"] for r in rows]
hums = [r["humidity_pct"] for r in rows]
soils = [r["soil_moisture_pct"] for r in rows]
lights = [r["light_lux"] for r in rows]
labels = [
    datetime.fromtimestamp(r["timestamp"], tz=timezone.utc).strftime("%H:%M")
    for r in rows
]

with left:
    st.subheader("Temperature")
    st.line_chart({"°C": temps})
    st.subheader("Humidity")
    st.line_chart({"%": hums})
with right:
    st.subheader("Soil moisture")
    st.line_chart({"%": soils})
    st.subheader("Light")
    st.line_chart({"lux": lights})

st.divider()
st.subheader("Latest 15 readings")
st.dataframe(
    [
        {
            "time": r["iso_time"],
            "device": r["device_id"],
            "temp_C": r["temperature_c"],
            "humidity": r["humidity_pct"],
            "soil": r["soil_moisture_pct"],
            "light": r["light_lux"],
            "alert": r["alert_reason"] or "",
        }
        for r in rows[-15:]
    ],
    use_container_width=True,
)

st.caption(f"Source database: {DB_PATH}  ·  safe temp {TEMP_MIN_C}–{TEMP_MAX_C}°C  ·  "
           f"humidity ≥ {HUMIDITY_MIN}%  ·  soil ≥ {SOIL_MIN}%")
