import pandas as pd
import streamlit as st

st.title("Analytics")

summary_tabs = st.tabs(["Environmental trend", "Alert analysis", "Irrigation impact"])

with summary_tabs[0]:
    data = pd.DataFrame(
        {
            "time": ["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00"],
            "temperature_c": [25.5, 24.0, 23.4, 22.1, 20.9, 19.8, 21.4, 22.0],
            "humidity_pct": [70, 74, 76, 78, 77, 73, 69, 67],
            "temp_range_min": [18, 18, 18, 18, 18, 18, 18, 18],
            "temp_range_max": [30, 30, 30, 30, 30, 30, 30, 30],
            "humidity_range_min": [50, 50, 50, 50, 50, 50, 50, 50],
            "humidity_range_max": [80, 80, 80, 80, 80, 80, 80, 80],
        }
    ).set_index("time")
    st.line_chart(data[["temperature_c", "humidity_pct"]])
    st.caption("Temperature and humidity trend during the current operating window.")

with summary_tabs[1]:
    alert_data = pd.DataFrame(
        {
            "alert_type": ["Low soil", "High humidity", "High temperature", "Low soil"],
            "count": [12, 7, 4, 3],
        }
    )
    st.bar_chart(alert_data.set_index("alert_type"))
    st.caption("Alert frequency across the last 30 days.")

with summary_tabs[2]:
    irrigation = pd.DataFrame(
        {
            "time": ["00:00", "06:00", "12:00", "18:00"],
            "soil_moisture_pct": [58, 55, 60, 62],
            "water_applied_l": [0, 110, 0, 90],
        }
    ).set_index("time")
    st.line_chart(irrigation)
    st.caption("Irrigation and moisture recovery following scheduled commands.")

st.markdown("---")
summary_cols = st.columns(3)
with summary_cols[0]:
    st.metric("Average temperature", "21.4°C")
with summary_cols[1]:
    st.metric("Average humidity", "72.8%")
with summary_cols[2]:
    st.metric("Alert resolution rate", "91%")
