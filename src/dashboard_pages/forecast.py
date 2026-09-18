import pandas as pd
import streamlit as st

st.title("Forecast")

month_selector = st.selectbox("Forecast month", ["September", "October", "November", "December"], index=0)

summary_cols = st.columns(3)
with summary_cols[0]:
    st.metric("Current temperature", "17.7°C")
with summary_cols[1]:
    st.metric("Forecast month ahead", "21.3°C")
with summary_cols[2]:
    st.metric("Confidence", "87%")

forecast = pd.DataFrame(
    {
        "Month": ["September", "October", "November", "December"],
        "Current temperature": [17.7, 18.1, 16.9, 15.6],
        "Forecast temperature": [21.3, 20.4, 19.6, 18.8],
        "Safe band min": [18.0, 16.0, 13.0, 10.0],
        "Safe band max": [30.0, 28.0, 24.0, 22.0],
    }
)

st.subheader("Forecast month ahead")
st.dataframe(forecast, hide_index=True, use_container_width=True)

st.subheader("Temperature outlook")
st.line_chart(forecast.set_index("Month")[["Current temperature", "Forecast temperature"]])

st.caption("Safe band range indicates expected operating conditions for the next month ahead.")

st.markdown("---")
side_a, side_b = st.columns([1.5, 1])
with side_a:
    st.subheader("Operational note")
    st.success("The next-month forecast stays inside the safe operating band for most crop zones. Irrigation should be adjusted by 10–15 minutes during warmer afternoons.")
with side_b:
    st.subheader("Recommendation")
    st.warning("Tomato zone may need one additional irrigation cycle before 15:00 to protect against late-day soil stress.")
