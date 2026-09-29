"""Configured outdoor forecast with greenhouse planning context."""
import hashlib
import os
import pandas as pd
import streamlit as st
from config import DEFAULT_CITY, DEFAULT_COUNTRY
from dashboard_repository import read_snapshot, freshness
from weather_service import WeatherError, cold_risk_label, forecast_records, local_time, location_label, risk_label, search_locations, weather_at

@st.cache_data(ttl=86400, max_entries=64, show_spinner=False)
def find_places(query, credential_id, _api_key):
    return search_locations(query, _api_key)

@st.cache_data(ttl=600, max_entries=64, show_spinner=False)
def get_weather(lat, lon, credential_id, forecast, _api_key):
    return weather_at(lat, lon, _api_key, forecast=forecast)

def reset_location():
    st.session_state.weather_places=[]
    st.session_state.weather_place_index=None

st.title('Weather & forecast')
st.caption('Outdoor weather supplied by OpenWeatherMap. Indoor greenhouse readings remain separate.')
api_key=os.environ.get('OPENWEATHER_API_KEY','').strip()
if not api_key:
    try:
        api_key=str(st.secrets.get('openweather',{}).get('api_key','')).strip()
    except (FileNotFoundError,KeyError):
        api_key=''
if not api_key:
    st.info('The API key is not configured. Add OPENWEATHER_API_KEY and restart the dashboard.')
    st.stop()
credential_id=hashlib.sha256(api_key.encode()).hexdigest()
st.session_state.setdefault('weather_query',f'{DEFAULT_CITY}, {DEFAULT_COUNTRY}')
st.session_state.setdefault('weather_places',None)
if st.session_state.weather_places is None:
    try:
        st.session_state.weather_places=find_places(st.session_state.weather_query,credential_id,api_key)
    except WeatherError:
        st.session_state.weather_places=[]
with st.form('weather_location_search'):
    controls=st.columns([5,1])
    with controls[0]:
        query=st.text_input('Location',placeholder=f'{DEFAULT_CITY}, {DEFAULT_COUNTRY}',key='weather_query')
    with controls[1]: search=st.form_submit_button('Find location',icon=':material/search:',width='stretch')
st.caption(f'Enter a city and two-letter country code, such as {DEFAULT_CITY}, {DEFAULT_COUNTRY}.')
if search:
    reset_location()
    if not query.strip():
        st.warning('Enter a city and country to search.')
    else:
        try:
            with st.spinner(f'Loading locations for {query.strip()}...'):
                st.session_state.weather_places=find_places(query.strip(),credential_id,api_key)
            if not st.session_state.weather_places: st.warning('Location not found. Check the city name and country code.')
        except WeatherError as exc:
            st.error(str(exc))
places=st.session_state.get('weather_places') or []
if not places:
    st.info('Outdoor Weather Forecast\n\nSearch for the greenhouse location to view current outdoor conditions, a five-day forecast, rain probability, wind conditions, and greenhouse risk recommendations.')
    st.stop()
selected=st.selectbox('Choose a location',range(len(places)),format_func=lambda i:location_label(places[i]),key='weather_place_index')
if selected is None: selected=0
place=places[selected]
if st.button('Use default greenhouse location',key='default_weather_location'):
    st.session_state.weather_query=f'{DEFAULT_CITY}, {DEFAULT_COUNTRY}'
    st.session_state.weather_places=find_places(st.session_state.weather_query,credential_id,api_key)
    st.rerun()
if st.button('Refresh weather',icon=':material/refresh:',key='refresh_weather'):
    get_weather.clear(place['lat'],place['lon'],credential_id,False,api_key)
    get_weather.clear(place['lat'],place['lon'],credential_id,True,api_key)

@st.fragment(run_every='10m')
def show_weather():
    try:
        current=get_weather(place['lat'],place['lon'],credential_id,False,api_key)
    except WeatherError as exc:
        st.error(f'Weather service is temporarily unavailable. Greenhouse monitoring is still operating. ({exc})')
        return
    try:
        forecast=get_weather(place['lat'],place['lon'],credential_id,True,api_key)
    except WeatherError as exc:
        forecast=None
        st.warning(f'Forecast: {exc}')
    current_weather=(current.get('weather') or [{}])[0]
    st.subheader(location_label(place))
    st.caption(f'Updated {pd.Timestamp.now(tz="America/New_York"):%I:%M %p Eastern} · Outdoor observations only')
    cards=st.columns(6)
    card_values=[('Outdoor temperature',f'{current["main"]["temp"]:.1f} °C'),('Feels like',f'{current["main"].get("feels_like",current["main"]["temp"]):.1f} °C'),('Outdoor humidity',f'{current["main"]["humidity"]:.0f}%'),('Rain probability','See forecast'),('Wind',f'{current.get("wind",{}).get("speed",0)*3.6:.0f} km/h'),('Conditions',current_weather.get('description','Unavailable').title())]
    for card,(label,value) in zip(cards,card_values): card.metric(label,value,border=True)
    sunrise=current.get('sys',{}).get('sunrise'); sunset=current.get('sys',{}).get('sunset')
    offset=current.get('timezone',0)
    if sunrise and sunset: st.caption(f'Sunrise {local_time(sunrise,offset):%I:%M %p} · Sunset {local_time(sunset,offset):%I:%M %p} (location local time)')
    if forecast is None:
        st.info('Current conditions are available. The five-day forecast is temporarily unavailable.')
        return
    frame=pd.DataFrame(forecast_records(forecast))
    if frame.empty:
        st.warning('No forecast intervals are currently available for this location.')
        return
    frame['Day']=frame['Time'].dt.strftime('%a')
    daily=frame.groupby('Day',sort=False).agg(low=('Temperature (°C)','min'),high=('Temperature (°C)','max'),rain=('Rain probability (%)','max'),conditions=('Conditions','first')).reset_index().head(5)
    st.subheader('Five-day forecast')
    daily_cols=st.columns(min(5,len(daily)))
    for col,row in zip(daily_cols,daily.itertuples()):
        with col,st.container(border=True):
            st.markdown(f'**{row.Day}**')
            st.write(row.conditions.title())
            st.metric('High / low',f'{row.high:.0f}° / {row.low:.0f}°')
            st.caption(f'Rain {row.rain:.0f}%')
    st.subheader('Greenhouse impact recommendations')
    recommendations=[]
    humidity=current['main']['humidity']; wind=current.get('wind',{}).get('speed',0)*3.6; rain=float(frame['Rain probability (%)'].max()); low=float(daily.low.min())
    if rain>=50: recommendations.append(('Rain expected','Outdoor irrigation demand may decrease.'))
    if low<=12: recommendations.append(('Cool night forecast','Monitor the Seedling zone for low-temperature risk.'))
    if humidity>=75: recommendations.append(('High outdoor humidity','Ventilation may be less effective during the next six hours.'))
    if wind>=30: recommendations.append(('Strong wind','Keep greenhouse vents secured.'))
    if not recommendations: recommendations.append(('Conditions stable','No immediate outdoor weather risks detected.'))
    for label,text in recommendations: st.info(f'**{label}** · {text}')
    st.subheader('Indoor versus outdoor')
    try:
        snap=read_snapshot(); latest=snap['latest']; fresh=latest[latest.time.map(freshness)=='Fresh']
        if not fresh.empty:
            indoor_temp=fresh.temperature_c.mean(); indoor_humidity=fresh.humidity_pct.mean()
            comparison=pd.DataFrame({'Measurement':['Temperature','Humidity'],'Greenhouse':[f'{indoor_temp:.1f}°C',f'{indoor_humidity:.0f}%'],'Outdoor':[f'{current["main"]["temp"]:.1f}°C',f'{humidity:.0f}%'],'Difference':[f'{indoor_temp-current["main"]["temp"]:+.1f}°C',f'{indoor_humidity-humidity:+.0f}%']})
            st.table(comparison)
            st.caption('Indoor readings are measured by greenhouse sensors. Outdoor values are supplied by OpenWeather.')
    except Exception:
        pass
    with st.expander('Detailed three-hour forecast'):
        st.line_chart(frame.set_index('Time')[['Temperature (°C)','Feels like (°C)']],height=280)
        st.bar_chart(frame.set_index('Time')['Rain probability (%)'],height=180)
        st.dataframe(frame,hide_index=True,width='stretch')
        st.download_button('Export forecast CSV',frame.to_csv(index=False).encode('utf-8-sig'),'openweather_forecast.csv','text/csv')
    st.subheader('Forecast risks')
    risks=pd.DataFrame({'Risk':['Low-temperature risk','High-humidity risk','Heavy-rain probability','Strong-wind risk'],'Status':[cold_risk_label(low,15,10),risk_label(humidity,75,85),risk_label(rain,40,70),risk_label(wind,20,35)]})
    st.dataframe(risks,hide_index=True,width='stretch')

show_weather()
