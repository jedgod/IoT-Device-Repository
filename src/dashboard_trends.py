"""Long-term trends: every stored reading rolled up by day, week, month, quarter or year."""
import sqlite3
import altair as alt
import pandas as pd
import streamlit as st
from config import DEVICE_COLOR, HISTORY_ZONES, SITE_TIMEZONE, ZONE_COLORS, ZONE_PROFILES
from dashboard_repository import PERIODS, read_hourly, summarise_periods

METRICS = {
    'Temperature (°C)': 'temperature_c',
    'Relative humidity (%)': 'humidity_pct',
    'Soil moisture (%)': 'soil_moisture_pct',
    'Light (lux)': 'light_lux',
    'Nutrient level (%)': 'nutrient_level',
    'pH': 'ph_scale',
    'Hours with an alert (%)': 'alert_hours_pct',
}
SOURCES = {
    'All sources': None,
    'Modelled history (real Bowie weather)': ['weather model'],
    'Live and simulated readings': ['simulator', 'unverified', 'physical sensor'],
}


@st.cache_data(ttl=60, show_spinner=False)
def hourly_history():
    return read_hourly()


def _color(zone_id):
    return ZONE_COLORS.get(zone_id, DEVICE_COLOR)


def long_term_trends():
    st.subheader('Long-term trends')
    st.caption(f'Every stored reading averaged per hour, then grouped by calendar period in local greenhouse time ({SITE_TIMEZONE}). '
               'Periods marked "(partial)" have less than 90% of their hours covered.')
    try:
        hourly = hourly_history()
    except (sqlite3.Error, OSError):
        st.error('SQLite repository is unavailable.')
        return
    if hourly.empty:
        st.info('No stored readings yet.')
        return

    zone_names = dict(zip(hourly.zone_id, hourly.zone))
    order = [z for z in [*HISTORY_ZONES, *ZONE_PROFILES] if z in zone_names] + sorted(z for z in zone_names if z not in ZONE_PROFILES)
    zone_ids = list(dict.fromkeys(order))
    st.session_state.setdefault('trend_period', 'Month')
    st.session_state.setdefault('trend_measure', 'Temperature (°C)')
    st.session_state.setdefault('trend_source', 'All sources')
    st.session_state.setdefault('trend_zones', [z for z in HISTORY_ZONES if z in zone_names] or zone_ids[:3])
    controls = st.columns([1, 1.3, 1.6, 2.6], vertical_alignment='bottom')
    with controls[0]:
        period = st.selectbox('Group by', list(PERIODS), key='trend_period')
    with controls[1]:
        measure = st.selectbox('Measure', list(METRICS), key='trend_measure')
    with controls[2]:
        source = st.selectbox('Source', list(SOURCES), key='trend_source')
    with controls[3]:
        # At most eight at once: the categorical palette has eight distinguishable colours.
        chosen = st.multiselect('Zones', zone_ids, format_func=zone_names.get, key='trend_zones', max_selections=8)

    selected = hourly[hourly.zone_id.isin(chosen)]
    if SOURCES[source]:
        selected = selected[selected.source.isin(SOURCES[source])]
    summary = summarise_periods(selected, period, SITE_TIMEZONE)
    field = METRICS[measure]
    if summary.empty or summary[field].isna().all():
        st.info('No readings match these choices. Choose other zones or sources.')
        return
    summary = summary.dropna(subset=[field])

    present = [z for z in chosen if z in set(summary.zone_id)]
    color = alt.Color('zone:N', title='Zone', scale=alt.Scale(domain=[zone_names[z] for z in present], range=[_color(z) for z in present]),
                      legend=alt.Legend(orient='top'))
    value_format = '.2f' if field == 'ph_scale' else '.1f' if field != 'light_lux' else ',.0f'
    tooltip = [alt.Tooltip('label:N', title='Period'), alt.Tooltip('zone:N', title='Zone'),
               alt.Tooltip(f'{field}:Q', title=measure, format=value_format),
               alt.Tooltip('hours:Q', title='Hours covered', format=',')]
    if field == 'temperature_c':
        tooltip[3:3] = [alt.Tooltip('temperature_min_c:Q', title='Lowest (°C)', format='.1f'),
                        alt.Tooltip('temperature_max_c:Q', title='Highest (°C)', format='.1f')]
    y = alt.Y(f'{field}:Q', title=measure, scale=alt.Scale(zero=field in ('alert_hours_pct', 'light_lux')))
    periods = summary.start.nunique()
    if periods <= 8:
        # Few periods: grouped bars, one per zone, read side by side.
        chart = alt.Chart(summary).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X('label:N', title=None, sort=alt.SortField('start'), axis=alt.Axis(labelAngle=0)),
            xOffset=alt.XOffset('zone:N', sort=[zone_names[z] for z in present]), y=y, color=color, tooltip=tooltip)
    else:
        x = alt.X('start:T', title=None, axis=alt.Axis(format='%b %Y' if period in ('Month', 'Quarter', 'Year') else '%d %b', labelAngle=0))
        base = alt.Chart(summary).encode(x=x, color=color)
        layers = []
        if field == 'temperature_c' and len(present) == 1:
            layers.append(base.mark_area(opacity=0.2).encode(y='temperature_min_c:Q', y2='temperature_max_c:Q'))
        hover = alt.selection_point(on='pointerover', nearest=True, fields=['start'], empty=False)
        layers += [base.mark_line(strokeWidth=2).encode(y=y),
                   base.mark_circle(size=60).encode(y=y, opacity=alt.condition(hover, alt.value(1), alt.value(0)), tooltip=tooltip).add_params(hover)]
        chart = alt.layer(*layers)
    st.altair_chart(chart.properties(height=320), width='stretch')
    if field == 'temperature_c' and len(present) == 1 and periods > 8:
        st.caption('Shaded band: lowest to highest hourly temperature in each period.')

    table = summary.assign(Zone=summary.zone)[['label', 'Zone', 'hours', 'coverage_pct', 'temperature_c', 'temperature_min_c',
                                               'temperature_max_c', 'humidity_pct', 'soil_moisture_pct', 'light_lux',
                                               'nutrient_level', 'ph_scale', 'alert_hours_pct']]
    table.columns = ['Period', 'Zone', 'Hours', 'Coverage %', 'Mean °C', 'Low °C', 'High °C', 'Humidity %',
                     'Soil moisture %', 'Light lux', 'Nutrient %', 'pH', 'Alert hours %']
    with st.expander('Table view'):
        st.dataframe(table.round(2), hide_index=True, width='stretch')
    st.download_button('Export trend summary', table.round(2).to_csv(index=False), f'trend_summary_{period.lower()}.csv',
                       'text/csv', key='trend_export')
