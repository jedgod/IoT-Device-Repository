"""Explicit reference/demo data, separate from the SQLite telemetry repository."""
import numpy as np
import pandas as pd
import altair as alt

ZONES = [
    dict(name='Tomato zone',image='tomato',temperature=18.4,humidity=82.,soil=32.,target=45.),
    dict(name='Lettuce zone',image='lettuce',temperature=16.8,humidity=76.,soil=71.,target=50.),
    dict(name='Seedling zone',image='seedling',temperature=17.9,humidity=78.,soil=63.,target=55.),
]
ACTIVITY = [
    ('14:12','Soil moisture low in Tomato zone (32%)','#e43e48','Tomato zone'),
    ('12:45','Irrigation completed in Lettuce zone (10 min, 12.5 L)','#0b8646','Lettuce zone'),
    ('09:18','Temperature back to normal range','#0b8646','Seedling zone'),
    ('06:32','Humidity peak detected (88%)','#387bd0','Tomato zone'),
    ('04:17','Routine sensor check completed','#0b8646','All zones'),
]

def reference_history():
    rng=np.random.default_rng(651)
    times=pd.date_range('2026-08-18',periods=30*96,freq='15min',tz='UTC')
    hour=np.arange(len(times))%96/4
    base_temp=14.2+3.8*np.exp(-((hour-12)/3.5)**2)-.65*np.sin(hour/3)
    base_hum=71+10*np.exp(-((hour-7)/4)**2)-6*np.exp(-((hour-14)/1.4)**2)+rng.normal(0,.7,len(times))
    frames=[]
    for z in ZONES:
        frame=pd.DataFrame(dict(time=times,zone=z['name'],temperature_c=base_temp+(z['temperature']-17.7),humidity_pct=base_hum+(z['humidity']-79),soil_moisture_pct=np.clip(z['soil']+2*np.sin(hour/5),0,100)))
        frames.append(frame)
    return pd.concat(frames,ignore_index=True)

def filter_history(frame,zone,window):
    days={'Last 24 hours':1,'Last 7 days':7,'Last 30 days':30}[window]
    end=frame.time.max()
    out=frame[frame.time> end-pd.Timedelta(days=days)]
    return out if zone=='All zones' else out[out.zone==zone]

def environmental_chart(frame,mode,window):
    data=frame.groupby('time',as_index=False)[['temperature_c','humidity_pct','soil_moisture_pct']].mean()
    if window!='Last 24 hours':
        data=data.set_index('time').resample('3h').mean().reset_index()
    x=alt.X('time:T',title=None,scale=alt.Scale(type='utc'),axis=alt.Axis(format='%H:%M' if window=='Last 24 hours' else '%b %d',tickCount=8,labelAngle=0,grid=True))
    layers=[]
    for field,title,color,domain,limits,orient in [
        ('temperature_c','Temperature (°C)','#08783c',[5,30],[13,19],'left'),
        ('humidity_pct','Humidity (%)','#1460d5',[0,100],[60,90],'right'),
    ] if mode=='Temperature & Humidity' else [('soil_moisture_pct','Soil moisture (%)','#08783c',[0,100],[45,75],'left')]:
        base=alt.Chart(data).encode(x=x)
        band=base.mark_area(opacity=.09,color=color).encode(y=alt.Y('low:Q',title=title,scale=alt.Scale(domain=domain),axis=alt.Axis(orient=orient)),y2='high:Q').transform_calculate(low=str(limits[0]),high=str(limits[1]))
        line=base.mark_line(color=color,strokeWidth=2,interpolate='monotone').encode(y=alt.Y(f'{field}:Q',title=title,scale=alt.Scale(domain=domain),axis=alt.Axis(orient=orient)),tooltip=[alt.Tooltip('time:T',title='Time (UTC)',format='%b %d, %H:%M'),alt.Tooltip(f'{field}:Q',title=title,format='.1f')])
        layers.append(alt.layer(band,line).resolve_scale(y='shared'))
    return alt.layer(*layers).resolve_scale(y='independent').properties(height=204).configure_view(stroke=None).configure_axis(gridColor='#e4e9ef',domainColor='#bec7d5',tickColor='#bec7d5',labelColor='#626f8c',titleColor='#626f8c',titleFontWeight='normal',labelFontSize=12,titleFontSize=13,labelFont='Arial',titleFont='Arial',titlePadding=12).configure(background='transparent')

