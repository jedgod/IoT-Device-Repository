import pandas as pd
import streamlit as st

st.title("Zones")
selected_zone = st.segmented_control("Zone", ["Tomato zone", "Lettuce zone", "Seedling zone", "Cucumber zone"], default="Tomato zone")

zone_metrics = {
    "Tomato zone": {"Temperature": "18.4°C", "Humidity": "82%", "Soil moisture": "32%", "Light": "640 lux"},
    "Lettuce zone": {"Temperature": "16.8°C", "Humidity": "76%", "Soil moisture": "71%", "Light": "510 lux"},
    "Seedling zone": {"Temperature": "17.9°C", "Humidity": "78%", "Soil moisture": "63%", "Light": "560 lux"},
    "Cucumber zone": {"Temperature": "23.1°C", "Humidity": "74%", "Soil moisture": "61%", "Light": "700 lux"},
}

zone_detail = zone_metrics[selected_zone]

status_col, action_col = st.columns([2, 1])
with status_col:
    st.subheader(f"{selected_zone} status")
    st.info("Attention needed: soil moisture below target range for tomato crop.")
with action_col:
    st.subheader("Actions")
    st.button("Review zone", use_container_width=True)
    st.button("Trigger irrigation", use_container_width=True)

metric_cols = st.columns(4)
for col, (label, value) in zip(metric_cols, zone_detail.items()):
    with col:
        st.metric(label, value)

st.markdown("---")
left, right = st.columns([2, 1])
with left:
    st.subheader("Operating ranges")
    ranges = pd.DataFrame(
        [
            {"Metric": "Temperature", "Current": 18.4, "Target min": 20, "Target max": 28},
            {"Metric": "Humidity", "Current": 82.0, "Target min": 55, "Target max": 75},
            {"Metric": "Soil moisture", "Current": 32.0, "Target min": 45, "Target max": 70},
        ]
    )
    st.dataframe(ranges, hide_index=True, use_container_width=True)
with right:
    st.subheader("Recommended action")
    st.warning("Increase irrigation duration by 10 minutes and check valve response before noon.")
    st.success("Water supply is healthy and flow pressure is stable.")

st.markdown("---")
recent = pd.DataFrame(
    [
        {"Timestamp": "14:12", "Reading": "Soil moisture low", "Value": "32%", "Status": "Attention"},
        {"Timestamp": "12:45", "Reading": "Irrigation completed", "Value": "10 min", "Status": "Resolved"},
        {"Timestamp": "09:18", "Reading": "Temperature normalised", "Value": "19.4°C", "Status": "Resolved"},
    ]
)
st.subheader("Recent readings")
st.dataframe(recent, hide_index=True, use_container_width=True)
