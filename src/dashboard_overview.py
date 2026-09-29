"""Reference-layout overview using current repository values."""
from contextlib import closing
from html import escape
import sqlite3
import pandas as pd
import streamlit as st
from config import ZONE_PROFILES
from dashboard_live import snapshot_or_stop, chart as repository_chart, _display_zone_name, _live_zone_card, _zone_placeholder, WINDOWS
from dashboard_repository import filter_readings, freshness, limits, reading_alert, database_path
from dashboard_ui import icon, metric_card
from dashboard_charts import prepare_chart_data, metric_chart_data

def select_history():
    st.session_state.overview_window='All stored data'

def troubleshoot_connection():
    st.session_state.connection_help=True

def reference_chart(data,mode,snap,latest):
    if data.empty:
        repository_chart(data,mode)
        return
    import altair as alt
    fields={
        'Temperature & Humidity': [('temperature_c','Temperature (°C)','#08783c','temp_min_c','temp_max_c',[5,30]),('humidity_pct','Humidity (%)','#1460d5','humidity_min','humidity_max',[0,100])],
        'Soil moisture': [('soil_moisture_pct','Soil moisture (%)','#08783c','soil_min',None,[0,100])],
        'Nutrient level': [('nutrient_level','Nutrient level (%)','#c47b19',None,None,[0,100])],
        'pH scale': [('ph_scale','pH scale','#7a57b5',None,None,[4,9])],
    }[mode]
    values=prepare_chart_data(data, [field[0] for field in fields], average=True)
    st.caption('Five-minute means, equally weighted across reporting zones; time in UTC. Gaps over 20 minutes are not connected.')
    if len(values)>4000:
        st.caption('Chart sampled for readability; exports retain the loaded measurements.')
    bounds=[limits(snap,z) for z in latest.zone_id]
    hover=alt.selection_point(on='pointerover',nearest=True,fields=['time'],empty=False)
    zoom=alt.selection_interval(encodings=['x'],bind='scales')
    layers=[]
    for index,(field,title,color,minimum,maximum,domain) in enumerate(fields):
        metric_values=metric_chart_data(values,field)
        if metric_values.empty:
            st.info(f'No {title} measurements are available in this time window.')
            continue
        target_ranges={'nutrient_level':(55,80),'ph_scale':(5.8,6.8)}
        low=max(b[minimum] for b in bounds) if minimum else target_ranges.get(field,(domain[0],domain[1]))[0]
        high=min(b[maximum] for b in bounds) if maximum else target_ranges.get(field,(domain[0],domain[1]))[1]
        domain=[min(domain[0],metric_values[field].min()-1),max(domain[1],metric_values[field].max()+1)]
        axis=alt.Axis(orient='right' if field=='humidity_pct' else 'left',format='.1f' if field=='ph_scale' else '.0f')
        y=alt.Y(field+':Q',title=title,scale=alt.Scale(domain=domain),axis=axis)
        base=alt.Chart(metric_values).encode(x=alt.X('time:T',title='Time (UTC)',scale=alt.Scale(type='utc'),axis=alt.Axis(format='%H:%M' if values.time.max()-values.time.min()<pd.Timedelta(days=1) else '%b %d',tickCount=8,labelAngle=0)))
        tooltip=[alt.Tooltip('time_utc:N',title='Time (UTC)'),alt.Tooltip(field+':Q',title=title,format='.1f')]
        line=base.mark_line(strokeWidth=2,point=True).encode(
            detail=alt.Detail('series:N'),
            y=y,
            color=alt.value(color),
            opacity=alt.value(1),
            tooltip=tooltip)
        points=base.mark_circle(size=38).encode(
            y=y,
            color=alt.value(color),
            opacity=alt.condition(hover,alt.value(1),alt.value(0)),
            tooltip=tooltip)
        alerts=base.transform_filter('datum.alert_flag > 0').mark_point(shape='triangle-up',size=85,color='#d64545').encode(y=y,tooltip=tooltip+[alt.Tooltip('alert_flag:Q',title='Any recorded alert')])
        if low<=high:
            band=base.mark_area(color=color,opacity=.09).transform_calculate(low=str(low),high=str(high)).encode(y=alt.Y('low:Q',title=title,scale=alt.Scale(domain=domain),axis=axis),y2='high:Q')
            layers.append(alt.layer(band,line,points,alerts))
        else:
            layers.append(alt.layer(line,points,alerts))
    if not layers:
        return
    figure=alt.layer(*layers).resolve_scale(y='independent').add_params(zoom,hover).properties(height=250).configure_view(stroke=None).configure_axis(gridColor='#e4e9ef',domainColor='#bec7d5',labelColor='#626f8c',titleColor='#626f8c',titleFontWeight='normal',labelFontSize=12,titleFontSize=13,titlePadding=12).configure(background='transparent')
    st.altair_chart(figure,width='stretch',theme=None)

@st.fragment(run_every='5s')
def overview():
    snap=snapshot_or_stop()
    configured={zone.zone_id: zone.crop_name for zone in snap['zones'].itertuples()} if not snap['zones'].empty else {}
    configured.update({zone_id: profile['label'] for zone_id, profile in ZONE_PROFILES.items()})
    names=dict(configured)
    names.update(dict(zip(snap['latest'].zone_id,snap['latest'].zone)))
    options=['All zones',*names]
    if st.session_state.get('overview_zone') not in options:
        st.session_state.overview_zone='All zones'
    selected=st.session_state.overview_zone
    latest=snap['latest'] if selected=='All zones' else snap['latest'][snap['latest'].zone_id==selected]
    required_total=len(names) if selected=='All zones' else 1
    fresh=sum(freshness(t)=='Fresh' for t in latest.time)
    stale_count=max(0,required_total-fresh)
    source_names=set(latest.source.dropna()) if not latest.empty else set()
    if not fresh:
        system_status='Offline'
    elif stale_count:
        system_status='Degraded'
    elif source_names and source_names <= {'simulator','seeded sample'}:
        system_status='Demo data'
    else:
        system_status='Online'
    with st.container(key='overview_header'):
        title,tools=st.columns([.45,.55],vertical_alignment='center')
        with title:
            st.html('<div class="overview-title"><h1>Operations overview</h1><p>Live monitoring and control for a smarter, more productive greenhouse.</p></div>')
        with tools:
            a,b,c,d=st.columns([1.2,1.3,.9,1.05])
            with a:
                zone=st.selectbox('Zone',options,format_func=lambda x:_display_zone_name(names.get(x,x)),key='overview_zone')
            with b:
                window=st.selectbox('Time range',WINDOWS,key='overview_window')
            with c:
                status_color={'Online':'#0b8646','Demo data':'#387bd0','Degraded':'#eaa008','Offline':'#626f78'}[system_status]
                st.html(f'<div class="live-status"><span class="dot" style="background:{status_color}"></span><strong>{system_status}</strong><small>{fresh} of {required_total} sources reporting</small></div>')
            data=filter_readings(snap['readings'],zone,window)
            with d,st.container(key='export'):
                st.download_button('Export data',data.to_csv(index=False),'greenhouse_readings.csv','text/csv',icon=':material/download:',width='stretch')
    if latest.empty:
        st.info('Waiting for measurements. Start the MQTT subscriber and connect a sensor publisher.')
        return
    alerts=[(r,reading_alert(r,limits(snap,r.zone_id))) for r in latest.itertuples()]
    active=[(r,reason) for r,reason in alerts if reason]
    stale_names=', '.join(_display_zone_name(names.get(zone_id, zone_id)) for zone_id in names if zone_id not in set(latest.zone_id) or freshness(latest[latest.zone_id==zone_id].iloc[0].time)!='Fresh')
    message=(f'{stale_count} of {required_total} sensor sources are stale. Last recorded values are displayed.' if stale_count else
             f'{_display_zone_name(active[0][0].zone)}: {active[0][1]}.' if active else 'All monitored zones are within their configured targets.')
    with st.container(key='alert_banner'):
        text,action=st.columns([10,1.5],vertical_alignment='center')
        with text:
            st.html(f'<div class="alert-copy">{icon("warning" if stale_count or active else "leaf")}<span>{escape(message)}</span></div>')
        with action:
            if stale_count:
                st.button('View affected zones',on_click=lambda: st.switch_page('dashboard_pages/zones.py'),width='stretch')
            elif st.button('View zones',icon=':material/arrow_forward:',width='stretch'):
                st.switch_page('dashboard_pages/zones.py')
    if stale_count:
        with st.expander('Affected sources and connection checks'):
            st.write(stale_names)
            st.caption('Check the MQTT subscriber, zone publishers, broker, and topic before treating last-known values as live readings.')
            st.button('Troubleshoot connection',on_click=troubleshoot_connection,key='troubleshoot_connection')
    if st.session_state.get('connection_help'):
        st.info('Run the subscriber first, then start one publisher per zone. Confirm the broker and topic in src/config.py and watch the subscriber terminal for RECV messages.')
    with st.container(key='metrics_grid'):
        cols=st.columns(4)
        fresh_latest=latest[latest.time.map(freshness)=='Fresh']
        kpi_source=fresh_latest if not fresh_latest.empty else latest
        for col,(label,field,unit,kind) in zip(cols,[('Average temperature','temperature_c','°C','temperature'),('Average humidity','humidity_pct','%','water'),('Average soil moisture','soil_moisture_pct','%','leaf')]):
            series=data.groupby('time')[field].mean().tail(25).tolist()
            if len(series)<2: series=[latest[field].mean()]*2
            delta='Latest reading'
            if window!='All stored data':
                days={'Last 24 hours':1,'Last 7 days':7,'Last 30 days':30}[window]
                end=pd.Timestamp.now(tz='UTC')-pd.Timedelta(days=days)
                previous=snap['readings']
                if zone!='All zones': previous=previous[previous.zone_id==zone]
                previous=previous[(previous.time>end-pd.Timedelta(days=days))&(previous.time<=end)]
                if not previous.empty and not data.empty:
                    change=data[field].mean()-previous[field].mean()
                    delta=f'{"↑" if change>=0 else "↓"} {change:+.1f}{unit}'
            with col:
                html=metric_card(label,f'{kpi_source[field].mean():.1f}{unit}',f'Across {len(fresh_latest)} fresh zones',kind,series,note='Latest average')
                if delta=='Latest reading': html=html.replace('vs. previous period','No period comparison')
                st.html(html)
        with cols[3]:
            st.html(metric_card('Condition alerts',str(len(active)),f'{len(active)} environmental','bell',[len(active)]*2,note=f'{stale_count} offline/stale sources'))
    with st.container(key='middle_grid'):
        left,right=st.columns([1.63,1])
        with left,st.container(key='trend_panel'):
            heading,choice=st.columns([1.7,1])
            with heading:
                st.html('<h2 class="panel-heading">Environmental trend</h2><div class="panel-subtitle">Five-minute zone averages with common configured target ranges</div>')
            with choice:
                mode=st.selectbox('Trend metric',['Temperature & Humidity','Soil moisture','Nutrient level','pH scale'],key='trend_metric',label_visibility='collapsed')
                fresh_only=st.checkbox('Fresh data only',value=False,key='trend_fresh_only')
            chart_data=data[data.time.map(freshness)=='Fresh'] if fresh_only else data
            reference_chart(chart_data,mode,snap,latest)
            st.caption('Red triangles indicate a recorded alert in any core metric; they do not identify which metric triggered it.')
            if mode=='Temperature & Humidity':
                st.html('<div class="legend"><span><i></i>Temperature (°C)</span><span><i class="blue"></i>Humidity (%)</span><span><i class="band"></i>Temperature target</span><span><i class="band blue"></i>Humidity target</span></div>')
        with right,st.container(key='zone_panel'):
            heading,link=st.columns([1.4,1])
            with heading: st.html('<h2 class="panel-heading">Zone health</h2>')
            with link:
                if st.button('View all zones',icon=':material/arrow_forward:',icon_position='right',width='stretch'):
                    st.switch_page('dashboard_pages/zones.py')
            order={'tomato-zone':0,'lettuce-zone':1,'cucumber-zone':2,'carrot-zone':3,'corn-zone':4,'onion-zone':5,'watermelon-zone':6,'seedling-zone':7}
            latest_by_zone={row.zone_id: row for row in snap['latest'].itertuples()}
            primary_zone_ids=['tomato-zone','lettuce-zone','seedling-zone']
            health_ids=[zone_id for zone_id in primary_zone_ids if zone_id in names] if selected=='All zones' else [selected]
            health_rows=[]
            for zone_id in health_ids:
                row=latest_by_zone.get(zone_id)
                if row is None and zone_id in ZONE_PROFILES:
                    row=_zone_placeholder(zone_id)
                reason=reading_alert(row,limits(snap,zone_id)) if row is not None and not pd.isna(row.time) and freshness(row.time)=='Fresh' else ''
                health_rows.append((zone_id,row,reason))
            for zone_id,row,reason in sorted(health_rows,key=lambda item:order.get(item[0],99)):
                if row is not None:
                    st.html(_live_zone_card(row,reason))
    with st.container(key='lower_grid'):
        left,right=st.columns([.94,1.06])
        with left,st.container(key='activity_panel'):
            heading,link=st.columns([3,1])
            with heading: st.html('<h2 class="panel-heading">Recent activity</h2>')
            with link:
                if st.button('View all',icon=':material/arrow_forward:',icon_position='right',width='stretch'):
                    st.switch_page('dashboard_pages/data_explorer.py')
            activity_filter=st.selectbox('Activity filter',['All','Alerts','Devices','Irrigation'],key='activity_filter',label_visibility='collapsed')
            events=[]
            for row,reason in alerts:
                if reason and activity_filter in ('All','Alerts'):
                    events.append((row.time,f'Condition alert — {_display_zone_name(row.zone)}: {reason}','#d64545'))
                elif freshness(row.time)!='Fresh' and activity_filter in ('All','Devices'):
                    events.append((row.time,f'Sensor stale — {_display_zone_name(row.zone)}','#8a969e'))
            if activity_filter in ('All','Irrigation') and not snap['irrigation'].empty:
                for row in snap['irrigation'].head(5).itertuples():
                    events.append((pd.to_datetime(row.started_at,utc=True),f'Irrigation {row.status} — {_display_zone_name(row.zone_id)}','#387bd0'))
            if not events:
                st.caption('No significant events in this window.')
            for event_time,event_text,event_color in sorted(events,key=lambda item:item[0],reverse=True)[:5]:
                st.html(f'<div class="activity-row"><span class="dot" style="background:{event_color}"></span><span class="activity-time">{event_time:%H:%M}</span><span>{escape(event_text)}</span></div>')
        with right,st.container(key='irrigation_panel'):
            st.html(f'<div class="irrigation-title"><div class="metric-icon">{icon("plant")}</div><div><h2 class="panel-heading">Quick irrigation</h2><div class="panel-subtitle">Request irrigation for a selected zone</div></div></div>')
            inputs,safety=st.columns([1.2,1],vertical_alignment='center')
            zone_names=dict(zip(snap['zones'].zone_id,snap['zones'].crop_name)) if not snap['zones'].empty else {}
            zone_names=dict(sorted(zone_names.items(),key=lambda item: {'tomato-zone':0,'lettuce-zone':1,'seedling-zone':2}.get(item[0],3)))
            with inputs:
                a,b=st.columns(2)
                with a: request_zone=st.selectbox('Zone',list(zone_names),format_func=lambda x:_display_zone_name(zone_names[x]),key='quick_zone',disabled=not zone_names)
                with b: duration=st.selectbox('Duration (minutes)',[5,10,15,20],index=1,key='quick_duration')
            with safety:
                st.html('<div class="safety"><strong>SIMULATION MODE</strong><br>Water supply: unverified<br>Zone valve: not connected<br>Controller: unavailable</div>')
            irrigation_allowed=False
            if st.button('Save simulated request',icon=':material/save:',type='secondary',width='stretch',key='start_irrigation',disabled=not irrigation_allowed):
                from db import connect,create_zone_command
                try:
                    with closing(connect(database_path())) as conn:
                        request=create_zone_command(conn,request_zone,status='pending_controller',required_action=f'Irrigation requested for {duration} minutes',notes='Awaiting controller and safety verification; no command sent.')
                    st.session_state.quick_request_id=request['id']
                except sqlite3.Error:
                    st.error('Unable to save request. Check database availability.')
            if st.session_state.get('quick_request_id'):
                st.caption(f'Request #{st.session_state.quick_request_id} saved; irrigation has not started.')
    with st.expander('Connection and measurement details'):
        invalid=int((latest.get('data_quality',pd.Series(dtype=str))=='invalid').sum())
        st.caption(f'Data quality · {fresh} fresh · {stale_count} stale · {invalid} invalid')
        st.caption(f'SQLite connected · Latest measurement {latest.time.max():%Y-%m-%d %H:%M:%S UTC} · Refresh every 5 seconds')
        st.caption('Data provenance: '+', '.join(sorted(latest.source.unique()))+'. Legacy records without provenance remain unverified.')
        st.caption('Metric cards show the latest reading per source, averaged across the selection. Changes compare window averages. Historical measurements and requests do not confirm hardware operation.')
