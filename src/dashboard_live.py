"""Live repository views, shared by the dashboard navigation pages."""
from datetime import datetime, timezone
from html import escape
import sqlite3
from types import SimpleNamespace
import pandas as pd
import streamlit as st
from zoneinfo import ZoneInfo
from config import ZONE_PROFILES
from dashboard_repository import read_snapshot, filter_readings, freshness, limits, reading_alert, METRICS
from dashboard_ui import crop_image, icon
from dashboard_charts import prepare_chart_data, metric_chart_data

WINDOWS = ['Last 24 hours','Last 7 days','Last 30 days','All stored data']

def snapshot_or_stop():
    try:
        return read_snapshot()
    except (sqlite3.Error, OSError):
        st.error('SQLite repository is unavailable. Start the subscriber or check the database path and permissions.')
        st.stop()

def filters(snapshot, prefix):
    names = {zone_id: profile['label'] for zone_id, profile in ZONE_PROFILES.items()}
    names.update(dict(zip(snapshot['latest'].zone_id, snapshot['latest'].zone)))
    options = ['All zones', *names]
    if st.session_state.get(prefix+'_zone') not in options:
        st.session_state[prefix+'_zone'] = 'All zones'
    zone = st.selectbox('Zone', options, format_func=lambda x:names.get(x,x), key=prefix+'_zone')
    window = st.selectbox('Time range', WINDOWS, key=prefix+'_window')
    return zone, window

def reset_analytics_filters():
    for key, value in [('zone', 'All zones'), ('window', 'Last 24 hours'),
                       ('metric', 'Temperature & Humidity'), ('view', 'Compare zones')]:
        st.session_state['analytics_'+key] = value


def analytics_filters(snapshot):
    names = {zone_id: profile['label'] for zone_id, profile in ZONE_PROFILES.items()}
    names.update(dict(zip(snapshot['latest'].zone_id, snapshot['latest'].zone)))
    options = ['All zones', *names]
    if st.session_state.get('analytics_zone') not in options:
        st.session_state.analytics_zone='All zones'
    st.session_state.setdefault('analytics_window','Last 24 hours')
    st.session_state.setdefault('analytics_metric','Temperature & Humidity')
    st.session_state.setdefault('analytics_view','Compare zones')
    controls=st.columns([1.25,1.25,1.55,1.25,.8,.8,1.1],vertical_alignment='bottom')
    with controls[0]: zone=st.selectbox('Zone',options,format_func=lambda x:names.get(x,x),key='analytics_zone')
    with controls[1]: window=st.selectbox('Period',WINDOWS,key='analytics_window')
    with controls[2]: mode=st.selectbox('Metric',['Temperature & Humidity','Soil moisture','Nutrient level','pH scale','Light'],key='analytics_metric')
    with controls[3]: view=st.selectbox('View',['Compare zones','Overall average'],key='analytics_view')
    with controls[4]: apply=st.button('Apply',key='analytics_apply',width='stretch')
    with controls[5]:
        st.button('Reset',key='analytics_reset',on_click=reset_analytics_filters,width='stretch')
    with controls[6]:
        data=filter_readings(snapshot['readings'],zone,window)
        st.download_button('Export filtered data',data.to_csv(index=False),'analytics_readings.csv','text/csv',width='stretch')
    return zone,window,mode,view

@st.fragment(run_every='1s')
def live_sidebar():
    now = datetime.now().astimezone()
    st.html(f'<div class="sidebar-footer"><div class="sidebar-motto">{icon("plant", "#74bf88")}<span>Healthy plants<br>brighter tomorrows</span></div><div class="sidebar-status"><span class="dot"></span>Dashboard online</div><div>Last refresh<br>{now:%I:%M:%S %p}</div></div>')

def chart(frame, mode, view='Compare zones'):
    if frame.empty:
        st.info('No measurements in this time window. Select a longer window to inspect stored readings.')
        return
    fields = {
        'Temperature & Humidity': ['temperature_c','humidity_pct'],
        'Soil moisture': ['soil_moisture_pct'],
        'Nutrient level': ['nutrient_level'],
        'pH scale': ['ph_scale'],
        'Light': ['light_lux'],
    }.get(mode, ['temperature_c','humidity_pct'])
    import altair as alt
    frame=prepare_chart_data(frame, fields, average=view == 'Overall average')
    if view == 'Overall average':
        st.caption('Five-minute means, equally weighted across reporting zones; absent zones are excluded. Time in UTC.')
    else:
        st.caption('Recorded measurements by zone; time in UTC. Gaps over 20 minutes are not connected.')
    if len(frame)>4000:
        st.caption('Chart sampled for readability; filtered tables, summaries and CSV retain the loaded measurements.')
    layers = []
    for field, color in zip(fields, ['#08783c','#1460d5']):
        title = {'temperature_c':'Temperature (°C)','humidity_pct':'Humidity (%)','soil_moisture_pct':'Soil moisture (%)','nutrient_level':'Nutrient level (%)','ph_scale':'pH scale','light_lux':'Light (lux)'}[field]
        tooltip=[alt.Tooltip('time_utc:N',title='Time (UTC)'),alt.Tooltip(field+':Q',title=title,format='.2f')]
        if view == 'Compare zones':
            tooltip.insert(0, alt.Tooltip('zone:N',title='Source'))
        chart_data=metric_chart_data(frame,field)
        if chart_data.empty:
            st.info(f'No {title} measurements are available in this time window.')
            continue
        encodings={
            'x':alt.X('time:T',title='Time (UTC)',scale=alt.Scale(type='utc'),axis=alt.Axis(format='%m-%d %H:%M',tickCount=5,labelAngle=0)),
            'y':alt.Y(field+':Q',title=title,scale=alt.Scale(zero=False),axis=alt.Axis(format='.1f',orient='right' if field=='humidity_pct' else 'left',titleColor=color)),
            'color':alt.value(color),
            'tooltip':tooltip,
            'detail':alt.Detail('series:N'),
        }
        if view == 'Compare zones':
            encodings['strokeDash']=alt.StrokeDash('zone:N',title='Zone',scale=alt.Scale(range=[[1,0],[6,3],[2,2],[10,3],[8,2,2,2],[4,2,4,6],[12,3,2,3],[1,3]]),legend=alt.Legend(orient='bottom',symbolType='stroke'))
        layers.append(alt.Chart(chart_data).mark_line(point=True,interpolate='linear').encode(**encodings))
    if not layers:
        return
    st.altair_chart(alt.layer(*layers).resolve_scale(y='independent').properties(height=220),width='stretch')

def _display_zone_name(zone):
    if not isinstance(zone, str):
        return str(zone)
    name = zone.strip()
    if name == 'Tomatoes':
        return 'Tomato zone'
    if name == 'Lettuce':
        return 'Lettuce zone'
    if name == 'Seedlings':
        return 'Seedling zone'
    if name == 'Cucumber':
        return 'Cucumber zone'
    if name == 'Carrot':
        return 'Carrot zone'
    if name == 'Corn':
        return 'Corn zone'
    if name == 'Onions':
        return 'Onion zone'
    if name == 'Watermelon':
        return 'Watermelon zone'
    return name


def _zone_image(zone):
    name = _display_zone_name(zone)
    image_map = {
        'Tomato zone': 'tomato',
        'Lettuce zone': 'lettuce',
        'Seedling zone': 'seedling-new',
        'Cucumber zone': 'cucumber',
        'Carrot zone': 'carrot',
        'Corn zone': 'corn',
        'Onion zone': 'onion',
        'Watermelon zone': 'watermelon',
    }
    return image_map.get(name, 'tomato')

def _zone_placeholder(zone_id):
    """Stand-in for a configured zone that has not reported; carries every field the views read."""
    profile = ZONE_PROFILES[zone_id]
    return SimpleNamespace(
        zone_id=zone_id, zone=profile['label'], time=pd.NaT, source='none', device_id='',
        temperature_c=None, humidity_pct=None, soil_moisture_pct=None, light_lux=None,
        nutrient_level=None, ph_scale=None, battery_pct=None, signal_strength=None,
        data_quality=None, alert_flag=0, alert_reason=None,
    )


def _zone_status(time, reason):
    if freshness(time) != 'Fresh':
        return 'Stale'
    if reason and len(reason.split(';')) > 1:
        return 'Critical'
    return 'Warning' if reason else 'Healthy'


def _age_text(time):
    if pd.isna(time):
        return 'Waiting for telemetry'
    age_seconds = max(0, int((datetime.now(timezone.utc) - time.to_pydatetime()).total_seconds()))
    if age_seconds < 60:
        return f'{age_seconds}s ago'
    if age_seconds < 3600:
        return f'{age_seconds // 60}m ago'
    if age_seconds < 86400:
        return f'{age_seconds // 3600}h ago'
    return f'{age_seconds // 86400}d ago'


def _live_zone_card(row, reason):
    name = _display_zone_name(row.zone)
    status = _zone_status(row.time, reason)
    status_class = {'Stale':'stale','Critical':'critical','Warning':'attention','Healthy':'healthy'}[status]
    last_seen = _age_text(row.time)
    battery = getattr(row, 'battery_pct', None)
    signal = getattr(row, 'signal_strength', None)
    quality = getattr(row, 'data_quality', None)
    battery_text = f'{battery:.0f}%' if pd.notna(battery) else 'n/a'
    signal_text = f'{signal:.0f} dBm' if pd.notna(signal) else 'n/a'
    quality_text = str(quality) if pd.notna(quality) else 'unverified'
    target_text = reason or ('Waiting for a sensor reading' if pd.isna(row.time) else 'Within configured targets')
    value = lambda field, suffix: f'{getattr(row, field):.0f}{suffix}' if pd.notna(getattr(row, field)) else '--'
    temperature = f'{row.temperature_c:.1f}°C' if pd.notna(row.temperature_c) else '--'
    return (
        f'<div class="zone-row reference-zone" title="{escape(reason or status, quote=True)}">'
        f'<img class="zone-photo" src="{crop_image(_zone_image(name))}" alt="{escape(name)} crop">'
        f'<div class="zone-identity"><div class="zone-name">{escape(name)}</div>'
        f'<div class="zone-status {status_class}"><span class="dot"></span>{status}</div>'
        f'<div class="zone-meta">Last seen {last_seen}</div></div>'
        f'<div class="zone-health-readings"><div class="zone-values"><span>{icon("temperature", "#7b879c")}{temperature}</span>'
        f'<span>{icon("water", "#719fde")}{value("humidity_pct", "%")}</span>'
        f'<span>{icon("plant", "#66a37e")}{value("soil_moisture_pct", "%")}</span></div>'
        f'<div class="zone-health-meta"><span>Battery {battery_text}</span><span>Signal {signal_text}</span><span>Quality {escape(quality_text)}</span></div>'
        f'<div class="zone-target {"attention" if reason else ""}">{escape(target_text)}</div></div>'
        f'<span class="zone-chevron">›</span></div>'
    )


@st.fragment(run_every='5s')
def repository_page(title):
    st.title(title)
    snap=snapshot_or_stop()
    analytics_mode=analytics_view=None
    if title=='Analytics':
        zone,window,analytics_mode,analytics_view=analytics_filters(snap)
    else:
        zone,window=filters(snap,title.lower())
    data=filter_readings(snap['readings'],zone,window)
    eastern_now=datetime.now(ZoneInfo('America/New_York'))
    st.caption(f'{len(data)} of {snap["total"]} records match the current filters · Last refreshed: {eastern_now:%I:%M:%S %p} Eastern · Auto-refresh: On')
    if title=='Zones':
        latest_by_zone={row.zone_id: row for row in snap['latest'].itertuples()}
        zone_ids=list(dict.fromkeys([*ZONE_PROFILES,*latest_by_zone]))
        if zone!='All zones': zone_ids=[zone]
        status_filter=st.selectbox('Status',['All','Healthy','Warning','Critical','Stale','Demo'],key='zones_status')
        search=st.text_input('Search crop or device',key='zones_search',placeholder='Search crop or device')
        cards=[]
        for zone_id in zone_ids:
            row=latest_by_zone.get(zone_id)
            waiting=row is None and zone_id in ZONE_PROFILES
            if waiting: row=_zone_placeholder(zone_id)
            if row is None: continue
            reason=reading_alert(row,limits(snap,zone_id)) if not waiting and freshness(row.time)=='Fresh' else ''
            status='Demo' if waiting else _zone_status(row.time,reason)
            haystack=f'{row.zone} {getattr(row,"device_id","")}'.lower()
            if status_filter!='All' and status_filter!=status: continue
            if search and search.lower() not in haystack: continue
            cards.append((zone_id,row,status,reason,waiting))
        st.subheader('Zone directory')
        for start in range(0,len(cards),3):
            columns=st.columns(3)
            for column,(zone_id,row,status,reason,waiting) in zip(columns,cards[start:start+3]):
                with column,st.container(border=True):
                    st.image(crop_image(_zone_image(_display_zone_name(row.zone))),width=75)
                    st.subheader(_display_zone_name(row.zone))
                    st.caption(f'{status} · {"Waiting for telemetry" if waiting else "Last seen "+_age_text(row.time)}')
                    st.write(f'Temperature: {row.temperature_c:.1f}°C' if pd.notna(row.temperature_c) else 'Temperature: --')
                    st.write(f'Humidity: {row.humidity_pct:.1f}% · Soil: {row.soil_moisture_pct:.1f}%' if pd.notna(row.humidity_pct) else 'Humidity: -- · Soil: --')
                    if st.button('View details',key=f'zone_details_{zone_id}',width='stretch'):
                        st.session_state.zones_selected=zone_id
        selected_zone=st.session_state.get('zones_selected',zone if zone!='All zones' and zone in zone_ids else (cards[0][0] if cards else None))
        selected_row=latest_by_zone.get(selected_zone) if selected_zone else None
        if selected_row is None and selected_zone in ZONE_PROFILES: selected_row=_zone_placeholder(selected_zone)
        if selected_row is not None:
            st.subheader(f'Selected zone: {_display_zone_name(selected_row.zone)}')
            bounds=limits(snap,selected_zone)
            stale=freshness(selected_row.time)!='Fresh'
            selected_reason=reading_alert(selected_row,bounds) if not stale and not pd.isna(selected_row.time) else ''
            status=_zone_status(selected_row.time,selected_reason)
            st.caption(f'Status: {status} · Source: {getattr(selected_row,"source","unverified")} · Last updated: {selected_row.time.tz_convert(ZoneInfo("America/New_York")):%b %d %I:%M:%S %p} Eastern' if not pd.isna(selected_row.time) else 'Status: Demo · No sensor has reported for this zone')
            detail_cols=st.columns(6)
            detail_values=[('Temperature (°C)',selected_row.temperature_c,bounds['temp_min_c'],bounds['temp_max_c'],'°C'),('Humidity (%)',selected_row.humidity_pct,bounds['humidity_min'],bounds['humidity_max'],'%'),('Soil moisture (%)',selected_row.soil_moisture_pct,bounds['soil_min'],100,'%'),('Light (lux)',selected_row.light_lux,None,None,' lux'),('Nutrient level (%)',getattr(selected_row,'nutrient_level',None),55,80,'%'),('Soil pH',getattr(selected_row,'ph_scale',None),5.8,6.8,'')]
            for column,(label,value,low,high,suffix) in zip(detail_cols,detail_values):
                with column:
                    st.metric(label,f'{value:,.1f}{suffix}' if pd.notna(value) else '--')
                    if low is not None:
                        verdict='No reading' if pd.isna(value) else 'Within target' if low<=value<=high else 'Outside target'
                        st.caption(f'Target: {low:g}–{high:g}{suffix} · {verdict}')
            if selected_zone and selected_zone in latest_by_zone:
                st.subheader('Historical conditions')
                chart(filter_readings(snap['readings'],selected_zone,window),'Temperature & Humidity','Overall average')
                recent=snap['readings'][snap['readings'].zone_id==selected_zone].tail(5).iloc[::-1]
                st.subheader('Recent readings')
                st.dataframe(recent[['time','temperature_c','humidity_pct','soil_moisture_pct','alert_flag']].rename(columns={'time':'Time','temperature_c':'Temperature °C','humidity_pct':'Humidity %','soil_moisture_pct':'Soil moisture %','alert_flag':'Alert'}),hide_index=True,width='stretch')
            if st.button('View complete data history',key='zone_view_data',width='stretch'):
                st.switch_page('dashboard_pages/data_explorer.py')
        if cards:
            st.download_button('Export zone data',data.to_csv(index=False),'zone_readings.csv',width='stretch')
        return
    if title in ('Zones','Analytics'):
        chart(data,analytics_mode or 'Temperature & Humidity',analytics_view or 'Compare zones')
    if title=='Analytics' and not data.empty:
        values=data[data.alert_flag.fillna(0).astype(bool)]
        average_temperature=data.temperature_c.mean()
        average_humidity=data.humidity_pct.mean()
        alert_rate=values.shape[0]/len(data)*100
        summary=st.columns(4)
        summary[0].metric('Records shown',f'{len(data):,}')
        summary[1].metric('Average temperature',f'{average_temperature:.1f}°C')
        summary[2].metric('Average humidity',f'{average_humidity:.1f}%')
        summary[3].metric('Alert rate',f'{alert_rate:.1f}%')
        if not data.empty:
            available_start=data.time.min().tz_convert(ZoneInfo('America/New_York'))
            available_end=data.time.max().tz_convert(ZoneInfo('America/New_York'))
            st.caption(f'Requested period: {window} · Available observations: {available_start:%b %d, %Y %I:%M %p}–{available_end:%b %d, %Y %I:%M %p} Eastern')
        comparison=data.groupby('zone',as_index=False).agg(temperature_c=('temperature_c','mean'),humidity_pct=('humidity_pct','mean'),soil_moisture_pct=('soil_moisture_pct','mean'),alerts=('alert_flag','sum'))
        comparison['zone']=comparison.zone.map(_display_zone_name)
        st.subheader('Zone comparison')
        st.dataframe(comparison.rename(columns={'zone':'Zone','temperature_c':'Avg temperature °C','humidity_pct':'Avg humidity %','soil_moisture_pct':'Avg soil moisture %','alerts':'Alerts'}),hide_index=True,width='stretch')
        st.subheader('Alert analysis')
        if values.empty:
            st.info('No recorded alerts match the current filters.')
        else:
            reasons=values.assign(reason=values.alert_reason.fillna('Unspecified').str.replace('_',' ',regex=False).str.title().str.split(',')).explode('reason')
            counts=reasons.groupby('reason').size().sort_values(ascending=True)
            import altair as alt
            alert_chart=alt.Chart(counts.rename('count').reset_index()).mark_bar().encode(x=alt.X('count:Q',title='Occurrences'),y=alt.Y('reason:N',sort='-x',title=None),tooltip=['reason:N','count:Q']).properties(height=max(120,28*len(counts)))
            st.altair_chart(alert_chart,width='stretch')
            latest_alert=values.sort_values('time').iloc[-1]
            st.caption(f'Most recent: {_display_zone_name(latest_alert.zone)} · {latest_alert.alert_reason or "Unspecified"} · {latest_alert.time:%Y-%m-%d %H:%M UTC}')
        st.subheader('Data quality')
        fresh_count=sum(freshness(t)=='Fresh' for t in data.time)
        invalid_count=int((data.get('data_quality',pd.Series(dtype=str))=='invalid').sum())
        st.caption(f'{fresh_count} fresh · {len(data)-fresh_count} stale or historical · {invalid_count} invalid')
    st.dataframe(data,hide_index=True,width='stretch')
    st.download_button('Export filtered data',data.to_csv(index=False),'greenhouse_readings.csv','text/csv')

def controls():
    st.title('Controls')
    snap=snapshot_or_stop()
    st.info('No physical controller is configured. Requests are saved to SQLite as pending_controller; saving does not run irrigation.')
    if snap['zones'].empty:
        st.warning('No configured greenhouse zones. Add zone configuration before requesting irrigation.')
        return
    with st.form('irrigation_request'):
        names=dict(zip(snap['zones'].zone_id,snap['zones'].crop_name))
        zone=st.selectbox('Zone',list(names),format_func=names.get)
        duration=st.slider('Duration (minutes)',1,30,10)
        submitted=st.form_submit_button('Save irrigation request')
    if submitted:
        from contextlib import closing
        from db import connect, create_zone_command
        from dashboard_repository import database_path
        try:
            with closing(connect(database_path())) as conn:
                request=create_zone_command(conn,zone,status='pending_controller',required_action=f'Irrigation requested for {duration} minutes',notes='Awaiting hardware controller and safety verification; no command sent.')
            st.success(f'Request #{request["id"]} saved. Awaiting controller; irrigation has not started.')
        except sqlite3.Error:
            st.error('Unable to save the request. Check database availability.')
    history=snapshot_or_stop()['commands']
    st.subheader('Stored requests')
    st.dataframe(history,hide_index=True,width='stretch')
