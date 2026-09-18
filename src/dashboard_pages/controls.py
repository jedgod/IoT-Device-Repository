import streamlit as st

st.title("Controls")

with st.form("irrigation_control"):
    zone = st.selectbox("Zone", ["Tomato zone", "Lettuce zone", "Seedling zone", "Cucumber zone"])
    mode = st.selectbox("Mode", ["Manual", "Automatic", "Scheduled"])
    duration = st.slider("Duration (minutes)", 5, 30, 10)
    st.caption("Safety checks")
    check_supply = st.checkbox("Water supply: OK")
    check_valve = st.checkbox("Valve ready")
    check_soil = st.checkbox("Soil moisture below target")
    submitted = st.form_submit_button("Start irrigation", use_container_width=True)

if submitted:
    if check_supply and check_valve and check_soil:
        st.success(f"Irrigation queued for {zone} for {duration} minutes in {mode.lower()} mode.")
    else:
        st.warning("Complete all safety checks before scheduling irrigation.")

st.markdown("---")
manual_actions = st.columns(2)
with manual_actions[0]:
    st.subheader("Quick actions")
    st.button("Ventilation boost", use_container_width=True)
    st.button("Nutrient cycle", use_container_width=True)
with manual_actions[1]:
    st.subheader("Auto policy")
    st.checkbox("Auto-apply irrigation below 35% soil moisture")
    st.checkbox("Open vents when humidity exceeds 80%")
    st.checkbox("Pause nutrient dosing above 28°C")
