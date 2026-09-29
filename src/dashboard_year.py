"""Year in review: the report and slide-8 charts, interactive and switchable by crop, from the same data functions."""
from contextlib import closing
import sqlite3
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from config import DEVICE_COLOR, MODELLED_ZONES, OUTPUT_DIR, ZONE_COLORS, ZONE_PROFILES
from dashboard_repository import database_path
from visualize import SEASONS, calendar_days, daily_temperatures, load, period_summary, season_profiles

LABELS = {zone_id: ZONE_PROFILES[zone_id]['label'] for zone_id in MODELLED_ZONES}
ALL = 'All crops'
SEASON_NAMES = [s.split(' ')[0] for s in SEASONS]
# Sequential ramps (one hue, light to dark): blue for hours outside target, orange for temperature.
BLUES = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
ORANGES = ['#fde3d3', '#f9c2a3', '#f39b6f', '#eb6834', '#c7511f', '#9c3d16', '#6e2a0f']


def _ramp(colors, low, high):
    return alt.Scale(domain=list(np.linspace(low, high, len(colors))), range=colors)


def _pair_scale(zone_id):
    """Colour scale for one crop against outdoor air."""
    return alt.Scale(domain=[LABELS[zone_id], 'Outdoor'], range=[ZONE_COLORS[zone_id], DEVICE_COLOR])


@st.cache_data(ttl=600, show_spinner=False)
def year_data(path):
    with closing(sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True, timeout=5)) as conn:
        data, outdoor = load(conn, MODELLED_ZONES)
    zones = [z for z in MODELLED_ZONES if z in set(data.zone_id)]
    return dict(data=data, outdoor=outdoor, zones=zones, profiles=season_profiles(data, outdoor, zones),
                daily=daily_temperatures(data, outdoor), days=calendar_days(data),
                months=period_summary(data, outdoor, 'M'), quarters=period_summary(data, outdoor, 'Q'))


def _download_png(name, key, selected):
    """The document PNGs show Tomatoes, Lettuce and Seedlings; offer them only where they apply."""
    path = OUTPUT_DIR / name
    if path.exists() and (selected == ALL or selected in ('tomato-zone', 'lettuce-zone', 'seedling-zone')):
        st.download_button(f'Download the document image ({name})', path.read_bytes(), path.name, 'image/png', key=key)


def _days(y, zones, selected):
    profiles = y['profiles']
    outdoor = profiles[profiles.series == 'outdoor']
    frames = [pd.concat([profiles[profiles.series == z].assign(crop=LABELS[z], series=LABELS[z]),
                         outdoor.assign(crop=LABELS[z], series='Outdoor')]) for z in zones]
    data = pd.concat(frames).assign(season=lambda f: f.season.str.split(' ').str[0])
    single = len(zones) == 1
    color = (alt.Color('series:N', title=None, scale=_pair_scale(zones[0]), legend=alt.Legend(orient='top')) if single else
             alt.Color('series:N', scale=alt.Scale(domain=[*LABELS.values(), 'Outdoor'],
                                                   range=[*(ZONE_COLORS[z] for z in LABELS), DEVICE_COLOR]), legend=None))
    chart = alt.Chart(data).mark_line(strokeWidth=2 if single else 1.6).encode(
        x=alt.X('hour:Q', title='Hour of day' if single else None, scale=alt.Scale(domain=[0, 23]), axis=alt.Axis(values=[0, 6, 12, 18], format='02d')),
        y=alt.Y('temperature_c:Q', title='Mean °C'),
        color=color, detail='series:N',
        tooltip=[alt.Tooltip('season:N', title='Season'), alt.Tooltip('series:N', title='Series'),
                 alt.Tooltip('hour:Q', title='Hour'), alt.Tooltip('temperature_c:Q', title='Mean °C', format='.1f')],
    ).properties(width=170, height=230 if single else 95)
    facet = dict(column=alt.Column('season:N', title=None, sort=SEASON_NAMES))
    if not single:
        facet['row'] = alt.Row('crop:N', title=None, sort=[LABELS[z] for z in zones], header=alt.Header(labelAngle=0, labelAlign='left'))
    st.markdown('**Average day by season:** each crop against outdoor air (grey). Summer afternoons push every zone up.')
    st.altair_chart(chart.facet(**facet))
    st.caption('Report Figure 2 · slide 8 "Days". Mean of every hour of the day across each season, local time.')
    _download_png('02_daily_cycle_by_season.png', 'dl_days', selected)


def _every_day(y, zones, selected):
    daily, outdoor = y['daily']
    out = outdoor.rename('outdoor_c').rename_axis('time').reset_index()
    st.markdown('**Every day of the year:** winter is held at target; summer highs break through.')
    for zone_id in zones:
        p, zone = ZONE_PROFILES[zone_id], daily[daily.zone_id == zone_id].merge(out, on='time')
        color = ZONE_COLORS[zone_id]
        band = alt.Chart(pd.DataFrame({'low': [p['temp_min_c']], 'high': [p['temp_max_c']]})).mark_rect(color='#e1e0d9', opacity=0.6).encode(y='low:Q', y2='high:Q')
        base = alt.Chart(zone).encode(x=alt.X('time:T', title=None, axis=alt.Axis(format='%b %Y')))
        hover = alt.selection_point(on='pointerover', nearest=True, fields=['time'], empty=False)
        layers = alt.layer(
            band,
            base.mark_area(color=color, opacity=0.25).encode(y=alt.Y('min:Q', title='°C'), y2='max:Q'),
            base.mark_line(color=DEVICE_COLOR, strokeWidth=1).encode(y='outdoor_c:Q'),
            base.mark_line(color=color, strokeWidth=1.8).encode(y='mean:Q'),
            base.mark_circle(color=color, size=45).encode(
                y='mean:Q', opacity=alt.condition(hover, alt.value(1), alt.value(0)),
                tooltip=[alt.Tooltip('time:T', title='Date', format='%a %d %b %Y'), alt.Tooltip('min:Q', title='Low °C', format='.1f'),
                         alt.Tooltip('mean:Q', title='Mean °C', format='.1f'), alt.Tooltip('max:Q', title='High °C', format='.1f'),
                         alt.Tooltip('outdoor_c:Q', title='Outdoor mean °C', format='.1f')]).add_params(hover),
        ).properties(height=220 if len(zones) == 1 else 150,
                     title=f"{LABELS[zone_id]} · target {p['temp_min_c']:g}–{p['temp_max_c']:g} °C (grey band)")
        st.altair_chart(layers, width='stretch')
    st.caption('Report Figure 3. Line = daily mean, shading = daily low to high, grey line = outdoor daily mean.')
    _download_png('03_daily_temperature_year.png', 'dl_every_day', selected)


def _months(y, zones, selected):
    # Chart data must be JSON-serialisable, so the pandas Period column is replaced by a label and start date.
    months = (y['months'][y['months'].zone_id.isin(zones)]
              .assign(month=lambda f: f.period.dt.strftime('%b %Y'), start=lambda f: f.period.dt.start_time, crop=lambda f: f.zone_id.map(LABELS))
              .drop(columns='period'))
    order = list(months.drop_duplicates('month').sort_values('start').month)
    x = alt.X('month:N', title=None, sort=order, axis=alt.Axis(labelAngle=0))
    st.markdown('**Month by month:** hours outside target peak in summer heat; winter dry air hits the humidity-loving crops.')
    if len(zones) == 1:
        zone_id = zones[0]
        lines = pd.concat([months.assign(series=LABELS[zone_id], value=months.temperature_mean_c),
                           months.assign(series='Outdoor', value=months.outdoor_mean_c)])
        temp = alt.Chart(lines).mark_line(point=True, strokeWidth=2).encode(
            x=x, y=alt.Y('value:Q', title='Monthly mean °C'),
            color=alt.Color('series:N', title=None, scale=_pair_scale(zone_id), legend=alt.Legend(orient='top')),
            tooltip=[alt.Tooltip('month:N', title='Month'), alt.Tooltip('series:N', title='Series'), alt.Tooltip('value:Q', title='Mean °C', format='.1f')],
        ).properties(height=220)
        bars = alt.Chart(months).mark_bar(color=ZONE_COLORS[zone_id], cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=x, y=alt.Y('outside_target_pct:Q', title='% of hours outside any target', scale=alt.Scale(domain=[0, 100])),
            tooltip=[alt.Tooltip('month:N', title='Month'), alt.Tooltip('outside_target_pct:Q', title='Hours outside target %', format='.1f'),
                     alt.Tooltip('hours:Q', title='Hours')],
        ).properties(height=240)
        st.altair_chart(temp, width='stretch')
        st.altair_chart(bars, width='stretch')
    else:
        # Nine crops side by side read best as a crop × month grid.
        y_crop = alt.Y('crop:N', title=None, sort=[LABELS[z] for z in zones])

        def grid(field, title, scale, fmt, dark_at):
            base = alt.Chart(months).encode(x=x, y=y_crop)
            return alt.layer(
                base.mark_rect(stroke='#ffffff', strokeWidth=2).encode(
                    color=alt.Color(f'{field}:Q', title=title, scale=scale),
                    tooltip=[alt.Tooltip('crop:N', title='Crop'), alt.Tooltip('month:N', title='Month'), alt.Tooltip(f'{field}:Q', title=title, format='.1f')]),
                base.mark_text(fontSize=11).encode(text=alt.Text(f'{field}:Q', format=fmt),
                                                   color=alt.condition(f'datum.{field} >= {dark_at}', alt.value('#ffffff'), alt.value('#0b0b0b'))),
            ).properties(height=34 * len(zones))

        st.markdown('Share of hours outside any target (%), darker = worse')
        st.altair_chart(grid('outside_target_pct', '% of hours outside', _ramp(BLUES, 0, 100), '.0f', 45), width='stretch')
        st.markdown('Monthly mean temperature (°C)')
        st.altair_chart(grid('temperature_mean_c', 'Mean °C', _ramp(ORANGES, 10, 30), '.1f', 22), width='stretch')
    st.caption('Report Figure 4 · slide 8 "Months". A target means temperature, humidity and soil moisture together.')
    _download_png('04_monthly_summary.png', 'dl_months', selected)


def _quarters(y, zones, selected):
    rows = []
    for record in y['quarters'][y['quarters'].zone_id.isin(zones)].itertuples():
        quarter = f'Q{record.period.quarter} {record.period.year} ({record.hours / 24:.0f} days)'
        for column, name in [('temp_within_pct', 'temperature'), ('humidity_within_pct', 'humidity'),
                             ('soil_within_pct', 'soil moisture'), ('all_within_pct', 'any target')]:
            rows.append(dict(quarter=quarter, start=record.period.start_time, row=f'{LABELS[record.zone_id]} · {name}',
                             outside=100 - getattr(record, column)))
    grid = pd.DataFrame(rows)
    row_order = [f'{LABELS[z]} · {n}' for z in zones for n in ('temperature', 'humidity', 'soil moisture', 'any target')]
    quarter_order = list(grid.drop_duplicates('quarter').sort_values('start').quarter)
    base = alt.Chart(grid).encode(x=alt.X('quarter:N', title=None, sort=quarter_order, axis=alt.Axis(orient='top', labelAngle=0)),
                                  y=alt.Y('row:N', title=None, sort=row_order))
    heat = alt.layer(
        base.mark_rect(stroke='#ffffff', strokeWidth=2).encode(
            color=alt.Color('outside:Q', title='% of hours outside', scale=_ramp(BLUES, 0, 100)),
            tooltip=[alt.Tooltip('row:N', title='Crop · target'), alt.Tooltip('quarter:N', title='Quarter'),
                     alt.Tooltip('outside:Q', title='Hours outside %', format='.1f')]),
        base.mark_text(fontSize=12).encode(text=alt.Text('outside:Q', format='.0f'),
                                           color=alt.condition('datum.outside >= 45', alt.value('#ffffff'), alt.value('#0b0b0b'))),
    ).properties(height=max(160, 30 * len(row_order)))
    st.markdown('**Quarter by quarter:** share of hours outside each target (darker = worse). Numbers are percentages.')
    st.altair_chart(heat, width='stretch')
    data = y['data'][y['data'].zone_id.isin(zones)]
    st.caption(f'Report Figure 5 · slide 8 "Quarters". Soil moisture was outside target in {int((~data.soil_ok).sum())} of {len(data):,} hours.')
    _download_png('05_quarterly_summary.png', 'dl_quarters', selected)


def _year(y, zones, selected):
    days = y['days'][y['days'].zone_id.isin(zones)].assign(
        crop=lambda f: f.zone_id.map(LABELS), week_start=lambda f: f.time - pd.to_timedelta(f.weekday, unit='D'),
        weekday_name=lambda f: f.time.dt.strftime('%a'))
    days['week_end'] = days.week_start + pd.Timedelta(days=7)
    st.markdown('**The year at a glance:** each square is one day.')
    for start in range(0, len(zones), 3):
        columns = st.columns(3)
        for column, zone_id in zip(columns, zones[start:start + 3]):
            zone = days[days.zone_id == zone_id]
            column.metric(f'{LABELS[zone_id]}: days fully within target', f'{int((zone.hours_outside == 0).sum())} of {len(zone)}')
    chart = alt.Chart(days).mark_rect(stroke='#ffffff', strokeWidth=0.5).encode(
        x=alt.X('week_start:T', title=None, axis=alt.Axis(format='%b', tickCount='month')), x2='week_end:T',
        y=alt.Y('weekday_name:O', title=None, sort=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']),
        color=alt.Color('hours_outside:Q', title='Hours outside target', scale=_ramp(BLUES, 0, 24)),
        tooltip=[alt.Tooltip('time:T', title='Date', format='%a %d %b %Y'), alt.Tooltip('crop:N', title='Crop'),
                 alt.Tooltip('hours_outside:Q', title='Hours outside target')],
    ).properties(height=120, width=820).facet(row=alt.Row('crop:N', title=None, sort=[LABELS[z] for z in zones]))
    st.altair_chart(chart)
    st.caption('Report Figure 6 · slide 8 "Year". Darker squares had more hours outside any target that day.')
    _download_png('06_year_calendar.png', 'dl_year', selected)


def year_in_review():
    st.subheader('Year in review')
    try:
        y = year_data(database_path())
    except (sqlite3.Error, OSError):
        st.error('SQLite repository is unavailable.')
        return
    except SystemExit:
        st.info('No modelled history yet. Run python src/build_history.py, then reload this page.')
        return
    options = [ALL, *y['zones']]
    if st.session_state.get('year_crop') not in options:
        st.session_state.year_crop = ALL
    selected = st.selectbox('Crop', options, format_func=lambda z: LABELS.get(z, z), key='year_crop')
    zones = y['zones'] if selected == ALL else [selected]
    tabs = st.tabs(['Days', 'Every day', 'Months', 'Quarters', 'Year'])
    for tab, draw in zip(tabs, [_days, _every_day, _months, _quarters, _year]):
        with tab:
            draw(y, zones, selected)
    with st.expander('Table view'):
        for name, table in [('Monthly summary', y['months']), ('Quarterly summary', y['quarters'])]:
            shown = table[table.zone_id.isin(zones)].assign(period=lambda f: f.period.astype(str))
            st.markdown(f'**{name}**')
            st.dataframe(shown, hide_index=True, width='stretch')
            st.download_button(f'Export {name.lower()}', shown.to_csv(index=False), f"{name.lower().replace(' ', '_')}.csv", 'text/csv',
                               key=f"dl_{name.split()[0].lower()}")
