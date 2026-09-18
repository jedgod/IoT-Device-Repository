"""Reference-matched operations overview with interactive demo controls."""
from datetime import datetime
from html import escape
import streamlit as st
from dashboard_ui import icon, metric_card, zone_card
from dashboard_demo import ZONES, ACTIVITY, reference_history, filter_history, environmental_chart

@st.cache_data(ttl=3600, max_entries=1)
def load_demo_history():
    return reference_history()

for key, value in {'dismissed_soil_alert':False, 'demo_irrigations':[], 'show_all_activity':False}.items():
    if key not in st.session_state:
        st.session_state[key] = value

def focus_tomato():
    st.session_state['overview_zone'] = 'Tomato zone'

def start_irrigation():
    st.session_state.demo_irrigations.insert(0, {
        'time': datetime.now().strftime('%H:%M'),
        'zone': st.session_state.irrigation_zone,
        'minutes': st.session_state.irrigation_duration,
    })

with st.container(key='overview_header'):
    title_col, tools_col = st.columns([.45,.55], vertical_alignment='center')
    with title_col:
        st.html('<div class="overview-title"><h1>Operations overview</h1><p>Live monitoring and control for a smarter, more productive greenhouse.</p></div>')
    with tools_col:
        zone_col,time_col,status_col,export_col = st.columns([1.2,1.3,.9,1.05],gap='small')
        with zone_col:
            zone_filter = st.selectbox('Zone',['All zones']+[z['name'] for z in ZONES],key='overview_zone')
        with time_col:
            window = st.selectbox('Time range',['Last 24 hours','Last 7 days','Last 30 days'],key='overview_window')
        with status_col:
            st.html('<div class="live-status"><span class="dot"></span><strong>Demo</strong><small>Simulated sensors</small></div>')
        filtered = filter_history(load_demo_history(),zone_filter,window)
        with export_col, st.container(key='export'):
            st.download_button('Export data',filtered.to_csv(index=False).encode(),file_name='greenhouse_demo_export.csv',mime='text/csv',icon=':material/download:',width='stretch')

selected_zones = [z for z in ZONES if zone_filter in ('All zones',z['name'])]
if zone_filter in ('All zones','Tomato zone') and not st.session_state.dismissed_soil_alert:
    with st.container(key='alert_banner'):
        msg,action,close=st.columns([10,1.35,.35],vertical_alignment='center')
        with msg:
            st.html(f'<div class="alert-copy">{icon("warning")}<span>Soil moisture is below target in the Tomato zone (32%). Consider running irrigation.</span></div>')
        with action:
            st.button('View zone',icon=':material/arrow_forward:',icon_position='right',on_click=focus_tomato,width='stretch')
        with close:
            if st.button('',icon=':material/close:',key='dismiss_alert',help='Dismiss soil moisture notification'):
                st.session_state.dismissed_soil_alert=True
                st.rerun()

all_zones=zone_filter=='All zones'
z=selected_zones[0]
values = [17.7,79.,58.] if all_zones else [z['temperature'],z['humidity'],z['soil']]
alerts=sum(z['soil']<z['target'] for z in selected_zones)
metrics = [
    ('Temperature',f'{values[0]:.1f}°C','↓ -0.8°C','temperature',[15,14,13,9,7,6,7,9,13,16,15,12,11,13,16,17,18]),
    ('Humidity',f'{values[1]:.1f}%','↓ -2.4%','water',[5,8,17,23,21,22,18,16,17,16,19,16,14,13,17,19,17,16]),
    ('Soil moisture',f'{values[2]:.1f}%','↑ +6.1%','leaf',[10,11,13,12,7,6,10,15,14,10,7,8,12,11,15,19,18,19]),
    ('Active alerts',str(alerts),'0 resolved','bell',[2,2,1,0,0,1,1,0,0,1,1,1,1,1,1,3,6] if alerts else [0]*17),
]
with st.container(key='metrics_grid'):
    for col,metric in zip(st.columns(4),metrics):
        with col:
            st.html(metric_card(*metric))

with st.container(key='middle_grid'):
    trend_col,health_col=st.columns([1.63,1],gap='small')
    with trend_col,st.container(key='trend_panel'):
        heading,choice=st.columns([1.7,1])
        with heading:
            st.html('<h2 class="panel-heading">Environmental trend</h2><div class="panel-subtitle">Temperature and humidity with recommended ranges</div>')
        with choice:
            mode=st.selectbox('Trend metric',['Temperature & Humidity','Soil moisture'],label_visibility='collapsed',key='trend_metric')
        st.altair_chart(environmental_chart(filtered,mode,window),width='stretch',theme=None)
        if mode=='Temperature & Humidity':
            st.html('<div class="legend"><span><i></i>Temperature (°C)</span><span><i class="blue"></i>Humidity (%)</span><span><i class="band"></i>Temperature safe range</span><span><i class="band blue"></i>Humidity safe range</span></div>')
        else:
            st.html('<div class="legend"><span><i></i>Soil moisture (%)</span><span><i class="band"></i>Target range</span></div>')
    with health_col,st.container(key='zone_panel'):
        heading,link=st.columns([1.4,1])
        with heading: st.html('<h2 class="panel-heading">Zone health</h2>')
        with link:
            if st.button('View all zones',icon=':material/arrow_forward:',icon_position='right',width='stretch'):
                st.switch_page('dashboard_pages/zones.py')
        for z in selected_zones:
            st.html(zone_card(z))

with st.container(key='lower_grid'):
    activity_col,irrigation_col=st.columns([.94,1.06],gap='small')
    with activity_col,st.container(key='activity_panel'):
        head,link=st.columns([4,1])
        with head: st.html('<h2 class="panel-heading">Recent activity</h2>')
        with link:
            if st.button('Show less' if st.session_state.show_all_activity else 'View all',icon=':material/arrow_forward:',icon_position='right',width='stretch'):
                st.session_state.show_all_activity=not st.session_state.show_all_activity
                st.rerun()
        recent=[(x['time'],f"Demo irrigation queued in {x['zone']} ({x['minutes']} min)",'#0b8646',x['zone']) for x in st.session_state.demo_irrigations]+ACTIVITY
        recent=[r for r in recent if zone_filter=='All zones' or r[3] in (zone_filter,'All zones')]
        shown=recent if st.session_state.show_all_activity else recent[:5]
        for time,text,color,_ in shown:
            st.html(f'<div class="activity-row"><span class="dot" style="background:{color}"></span><span class="activity-time">{time}</span><span>{escape(text)}</span></div>')
        if st.session_state.show_all_activity:
            st.caption(f'{len(recent)} events in this demo session. Historical events are sample activity.')
    with irrigation_col,st.container(key='irrigation_panel'):
        st.html(f'<div class="irrigation-title"><div class="metric-icon">{icon("plant")}</div><div><h2 class="panel-heading">Quick irrigation</h2><div class="panel-subtitle">Run irrigation for a selected zone · simulation</div></div></div>')
        inputs,safety=st.columns([1.2,1],vertical_alignment='center')
        with inputs:
            zone_input,duration_input=st.columns(2)
            with zone_input:
                irrigation_zone=st.selectbox('Zone',[z['name'] for z in ZONES],key='irrigation_zone')
            with duration_input:
                duration=st.selectbox('Duration (minutes)',[5,10,15,20],index=1,key='irrigation_duration')
        soil=next(z['soil'] for z in ZONES if z['name']==irrigation_zone)
        target=next(z['target'] for z in ZONES if z['name']==irrigation_zone)
        with safety:
            st.html(f'<div class="safety"><strong><span class="check">●</span>Safety check</strong><br><span class="check">✓</span>Water supply: simulated<br><span class="check">✓</span>Zone valve: simulated<br><span class="check">✓</span>Soil moisture: <b>{soil:.0f}%</b> ({"below target" if soil<target else "within target"})</div>')
        st.button('Start irrigation',icon=':material/play_arrow:',type='primary',width='stretch',key='start_irrigation',on_click=start_irrigation,disabled=soil>=target,help='Queue a simulated irrigation event. No physical hardware is connected.')
        if st.session_state.demo_irrigations:
            last=st.session_state.demo_irrigations[0]
            st.caption(f"Demo queued: {last['zone']}, {last['minutes']} minutes. No hardware command sent.")

