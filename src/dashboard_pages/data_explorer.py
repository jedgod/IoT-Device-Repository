import pandas as pd
import streamlit as st

st.title("Data")

filter_col_1, filter_col_2, filter_col_3 = st.columns(3)
with filter_col_1:
    zone_filter = st.selectbox("Zone", ["All zones", "Tomato zone", "Lettuce zone", "Seedling zone", "Cucumber zone"])
with filter_col_2:
    metric_filter = st.selectbox("Metric", ["All metrics", "Temperature", "Humidity", "Soil moisture", "Light"])
with filter_col_3:
    time_filter = st.selectbox("Window", ["Last 24 hours", "Last 7 days", "Last 30 days"])

records = [
    {"time": "2026-09-16 14:12", "zone": "Tomato zone", "temperature": 17.7, "humidity": 79.0, "soil": 32.0, "light": 640, "alert": "low_soil_moisture"},
    {"time": "2026-09-16 12:45", "zone": "Lettuce zone", "temperature": 19.0, "humidity": 76.0, "soil": 71.0, "light": 510, "alert": "normal"},
    {"time": "2026-09-16 09:18", "zone": "Seedling zone", "temperature": 18.3, "humidity": 78.0, "soil": 63.0, "light": 560, "alert": "normal"},
    {"time": "2026-09-16 06:32", "zone": "Cucumber zone", "temperature": 22.1, "humidity": 73.0, "soil": 61.0, "light": 700, "alert": "humidity_peak"},
]

frame = pd.DataFrame(records)
if zone_filter != "All zones":
    frame = frame[frame["zone"] == zone_filter]

st.dataframe(frame, hide_index=True, use_container_width=True)

st.markdown("---")
export_col, status_col = st.columns([1, 2])
with export_col:
    st.download_button("Export data", data=frame.to_csv(index=False), file_name="greenhouse_export.csv", mime="text/csv")
with status_col:
    st.caption("Data source: Local SQLite database  •  Sensors connected  •  Last refresh: 1 minute ago")
