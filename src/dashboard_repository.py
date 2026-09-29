"""Read-only dashboard queries; every refresh opens and closes its connection."""
from contextlib import closing
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import pandas as pd
from config import DB_PATH, TEMP_MIN_C, TEMP_MAX_C, HUMIDITY_MIN, HUMIDITY_MAX, SOIL_MIN

METRICS = ['temperature_c', 'humidity_pct', 'soil_moisture_pct', 'light_lux']
EXTRA_METRICS = ['nutrient_level', 'ph_scale']
FRESH_SECONDS = 120

def database_path():
    return Path(os.environ.get('GREENHOUSE_DB_PATH', str(DB_PATH))).resolve()

def read_snapshot(path=None):
    path = Path(path or database_path())
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)) as conn:
        conn.execute('BEGIN')
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        def table(name, order='id'):
            if name not in tables:
                return pd.DataFrame()
            return pd.read_sql_query(f'SELECT * FROM {name} ORDER BY {order} DESC LIMIT 50000', conn)
        zones = table('greenhouse_zones')
        frames = []
        sensor = table('sensor_data', 'timestamp')
        zoned = table('zone_telemetry', 'julianday(measured_at)')
        for frame, kind in [(sensor, 'device'), (zoned, 'zone')]:
            if frame.empty:
                continue
            if kind == 'device':
                frame['time'] = pd.to_datetime(frame.timestamp, unit='s', utc=True, errors='coerce').dt.round('us')
                frame['zone_id'] = 'device:' + frame.device_id.astype(str)
                frame['zone'] = 'Device ' + frame.device_id.astype(str)
            else:
                frame['time'] = pd.to_datetime(frame.measured_at, utc=True, errors='coerce', format='mixed')
                if 'iso_time' not in frame:
                    frame['iso_time'] = frame.measured_at
                else:
                    frame['iso_time'] = frame.iso_time.fillna(frame.measured_at)
                if 'timestamp' not in frame:
                    frame['timestamp'] = frame.time.astype('int64').where(frame.time.notna()) / 1_000_000_000
                else:
                    frame['timestamp'] = pd.to_numeric(frame.timestamp, errors='coerce').fillna(frame.time.astype('int64').where(frame.time.notna()) / 1_000_000_000)
                names = dict(zip(zones.zone_id, zones.crop_name)) if not zones.empty else {}
                frame['zone'] = frame.zone_id.map(lambda z: names.get(z, z.replace('-', ' ').title()))
            if 'source' not in frame:
                frame['source'] = 'unverified'
            frame['source'] = frame.source.fillna('unverified')
            if kind == 'zone':
                frame.loc[frame.message_id.str.contains('-seed-', na=False), 'source'] = 'seeded sample'
            for metric in [*METRICS, *EXTRA_METRICS]:
                if metric not in frame:
                    frame[metric] = pd.NA
                frame[metric] = pd.to_numeric(frame[metric], errors='coerce')
            frames.append(frame)
        readings = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=['time','zone_id','zone','source','alert_flag','alert_reason',*METRICS,*EXTRA_METRICS])
        readings = readings.dropna(subset=['time', *METRICS]).sort_values('time')
        latest = readings.groupby('zone_id', sort=False).tail(1)
        total = sum(conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ['sensor_data','zone_telemetry'] if t in tables)
        return dict(readings=readings, latest=latest, zones=zones, total=total,
                    commands=table('control_commands'), irrigation=table('irrigation_events'))

def freshness(timestamp, now=None):
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    if pd.isna(timestamp):
        return 'No readings'
    age = (now - pd.Timestamp(timestamp)).total_seconds()
    return 'Clock mismatch' if age < -60 else 'Fresh' if age <= FRESH_SECONDS else 'Stale'

def filter_readings(frame, zone='All zones', window='Last 24 hours', now=None):
    result = frame if zone == 'All zones' else frame[frame.zone_id == zone]
    if window != 'All stored data':
        days = {'Last 24 hours':1, 'Last 7 days':7, 'Last 30 days':30}[window]
        end = pd.Timestamp(now or datetime.now(timezone.utc))
        result = result[(result.time > end-pd.Timedelta(days=days)) & (result.time <= end)]
    return result

def limits(snapshot, zone_id):
    zones = snapshot['zones']
    if not zones.empty:
        match = zones[zones.zone_id == zone_id]
        if not match.empty:
            return match.iloc[0].to_dict()
    return dict(temp_min_c=TEMP_MIN_C,temp_max_c=TEMP_MAX_C,humidity_min=HUMIDITY_MIN,humidity_max=HUMIDITY_MAX,soil_min=SOIL_MIN)

def reading_alert(row, bounds):
    reasons = []
    if not bounds['temp_min_c'] <= row.temperature_c <= bounds['temp_max_c']:
        reasons.append('Temperature outside target')
    if not bounds['humidity_min'] <= row.humidity_pct <= bounds['humidity_max']:
        reasons.append('Humidity outside target')
    if row.soil_moisture_pct < bounds['soil_min']:
        reasons.append('Soil moisture below target')
    return '; '.join(reasons)
