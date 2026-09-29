from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import sqlite3
import sys
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from db import init_db, insert_reading, insert_zone_telemetry, seed_zone_telemetry
from dashboard_repository import read_snapshot, filter_readings, freshness
from dashboard_live import _display_zone_name, _zone_image
from subscriber import on_message
from simulator import generate_zone_reading
from streamlit.testing.v1 import AppTest

def test_subscriber_zone_ingestion_and_fresh_read(tmp_path):
    path=tmp_path/'telemetry.db'
    conn=sqlite3.connect(path)
    init_db(conn)
    reading=generate_zone_reading(zone_id='tomato-zone')
    msg=SimpleNamespace(topic='test',payload=json.dumps(reading).encode())
    on_message(None,{'conn':conn},msg)
    on_message(None,{'conn':conn},msg)
    snap=read_snapshot(path)
    assert snap['total']==1  # MQTT redelivery must not duplicate a zone message.
    assert snap['latest'].iloc[0].source=='simulator'
    assert snap['latest'].iloc[0].zone_id=='tomato-zone'
    assert snap['latest'].iloc[0].nutrient_level is not None
    assert snap['latest'].iloc[0].ph_scale is not None
    assert freshness(snap['latest'].iloc[0].time)=='Fresh'
    assert len(filter_readings(snap['readings'],'tomato-zone'))==1
    assert len(filter_readings(snap['readings'],'lettuce-zone'))==0
    conn.close()

def test_zone_alerts_are_normalized_to_crop_targets(tmp_path):
    path=tmp_path/'telemetry.db';conn=sqlite3.connect(path);init_db(conn)
    from db import insert_zone
    insert_zone(conn,dict(zone_id='lettuce-zone',crop_name='Lettuce',description='',temp_min_c=15,temp_max_c=22,humidity_min=60,humidity_max=80,soil_min=50))
    reading=generate_zone_reading(zone_id='lettuce-zone')
    reading.update(temperature_c=23.0, humidity_pct=70.0, soil_moisture_pct=60.0, alert_flag=0, alert_reason='dry_soil')
    insert_zone_telemetry(conn,reading)
    stored=conn.execute('SELECT alert_flag, alert_reason FROM zone_telemetry').fetchone()
    assert stored[0]==1
    assert stored[1]=='temperature_outside_target'
    conn.close()

def test_latest_by_measurement_time_and_staleness(tmp_path):
    path=tmp_path/'telemetry.db';conn=sqlite3.connect(path);init_db(conn)
    now=datetime.now(timezone.utc)
    def insert(at,temp):
        insert_reading(conn,dict(timestamp=at.timestamp(),iso_time=at.isoformat(),device_id='physical-1',temperature_c=temp,humidity_pct=70,soil_moisture_pct=50,light_lux=300,source='physical sensor'))
    insert(now,24)
    insert(now-timedelta(days=3),12)  # Late arrival of an older sample.
    snap=read_snapshot(path)
    assert snap['latest'].iloc[0].temperature_c==24
    assert len(filter_readings(snap['readings'],now=now))==1
    assert freshness(now-timedelta(minutes=3),now)=='Stale'
    assert freshness(now+timedelta(minutes=3),now)=='Clock mismatch'
    conn.close()

def test_seeded_zone_telemetry_starts_fresh(tmp_path):
    path=tmp_path/'telemetry.db';conn=sqlite3.connect(path);init_db(conn)
    seed_zone_telemetry(conn)
    snap=read_snapshot(path)
    assert len(snap['latest'])==6
    assert all(freshness(timestamp)=='Fresh' for timestamp in snap['latest'].time)
    conn.close()

def test_zone_health_crop_labels_and_images():
    assert _display_zone_name('Carrot') == 'Carrot zone'
    assert _display_zone_name('Corn') == 'Corn zone'
    assert _display_zone_name('Onions') == 'Onion zone'
    assert _zone_image('Corn zone') == 'corn'
    assert _zone_image('Carrot zone') == 'carrot'
    assert _zone_image('Onion zone') == 'onion'

def test_dashboard_refreshes_from_external_writer_and_persists_request(tmp_path,monkeypatch):
    path=tmp_path/'telemetry.db';conn=sqlite3.connect(path);init_db(conn)
    monkeypatch.setenv('GREENHOUSE_DB_PATH',str(path))
    reading=generate_zone_reading(zone_id='tomato-zone')
    reading['temperature_c']=23.4
    on_message(None,{'conn':conn},SimpleNamespace(topic='test',payload=json.dumps(reading).encode()))
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'src/dashboard.py',default_timeout=30).run()
    assert not app.exception
    assert any('23.4°C' in element.proto.body for element in app.get('html'))
    reading['message_id']='new-reading';reading['timestamp']+=1
    reading['measured_at']=datetime.fromtimestamp(reading['timestamp'],timezone.utc).isoformat()
    reading['temperature_c']=26.8
    on_message(None,{'conn':conn},SimpleNamespace(topic='test',payload=json.dumps(reading).encode()))
    app.run()
    assert not app.exception
    assert any('26.8°C' in element.proto.body for element in app.get('html'))
    irrigation_button=app.button(key='start_irrigation')
    assert irrigation_button.disabled
    assert conn.execute('SELECT COUNT(*) FROM control_commands').fetchone()[0]==0
    app.switch_page('dashboard_pages/controls.py').run()
    next(b for b in app.button if b.label=='Save irrigation request').click().run()
    assert not app.exception
    assert conn.execute('SELECT status FROM control_commands').fetchone()[0]=='pending_controller'
    conn.close()

def test_empty_database_and_missing_database(tmp_path,monkeypatch):
    path=tmp_path/'empty.db';conn=sqlite3.connect(path);init_db(conn);conn.close()
    assert read_snapshot(path)['latest'].empty
    monkeypatch.setenv('GREENHOUSE_DB_PATH',str(tmp_path/'missing.db'))
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'src/dashboard.py',default_timeout=30).run()
    assert not app.exception
    assert any('unavailable' in e.value for e in app.error)

def test_device_readings_shown_alongside_zone_telemetry(tmp_path):
    path=tmp_path/'telemetry.db';conn=sqlite3.connect(path);init_db(conn)
    seed_zone_telemetry(conn)
    from simulator import generate_reading
    insert_reading(conn,generate_reading())
    snap=read_snapshot(path)
    assert 'device:GH-SENSOR-01' in set(snap['latest'].zone_id)
    assert _display_zone_name('Device GH-SENSOR-01')=='Device GH-SENSOR-01'
    conn.close()

def test_redelivered_zone_message_keeps_original_row_and_alert_state(tmp_path):
    path=tmp_path/'telemetry.db';conn=sqlite3.connect(path);init_db(conn)
    from db import seed_default_zones
    seed_default_zones(conn)
    reading=generate_zone_reading(zone_id='lettuce-zone')
    reading.update(temperature_c=30.0,humidity_pct=40.0,soil_moisture_pct=60.0)
    first=insert_zone_telemetry(conn,dict(reading))
    again=insert_zone_telemetry(conn,dict(reading,temperature_c=18.0))
    assert first==again
    row=conn.execute('SELECT temperature_c, alert_flag, alert_state, alert_severity FROM zone_telemetry').fetchall()
    assert row==[(30.0,1,'Critical','critical')]
    conn.close()

def test_default_zones_match_configured_profiles(tmp_path):
    from config import ZONE_PROFILES
    from db import seed_default_zones
    conn=sqlite3.connect(tmp_path/'zones.db');init_db(conn)
    seed_default_zones(conn)
    assert {r[0] for r in conn.execute('SELECT zone_id FROM greenhouse_zones')}==set(ZONE_PROFILES)
    conn.close()

def test_zone_details_for_zone_without_telemetry(tmp_path,monkeypatch):
    path=tmp_path/'telemetry.db';conn=sqlite3.connect(path);init_db(conn)
    seed_zone_telemetry(conn);conn.close()
    monkeypatch.setenv('GREENHOUSE_DB_PATH',str(path))
    app=AppTest.from_string("from dashboard_live import repository_page\nrepository_page('Zones')",default_timeout=30)
    app.session_state['zones_zone']='corn-zone'
    app.run()
    assert not app.exception
    assert any('No sensor has reported' in c.value for c in app.caption)
    assert any('No reading' in c.value for c in app.caption)

def test_low_temperature_risk_rises_as_temperature_falls():
    from weather_service import cold_risk_label
    assert cold_risk_label(20,15,10)=='Low'
    assert cold_risk_label(12,15,10)=='Moderate'
    assert cold_risk_label(5,15,10)=='High'

def _overview_status(path,monkeypatch):
    monkeypatch.setenv('GREENHOUSE_DB_PATH',str(path))
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'src/dashboard.py',default_timeout=30).run()
    assert not app.exception
    return ' '.join(e.proto.body for e in app.get('html') if 'live-status' in e.proto.body)

def test_long_silent_zones_do_not_degrade_overview_status(tmp_path,monkeypatch):
    path=tmp_path/'telemetry.db';conn=sqlite3.connect(path);init_db(conn)
    from db import seed_default_zones
    seed_default_zones(conn);seed_zone_telemetry(conn)
    old=generate_zone_reading(ts=(datetime.now(timezone.utc)-timedelta(days=3)).timestamp(),zone_id='corn-zone')
    insert_zone_telemetry(conn,old);conn.close()
    status=_overview_status(path,monkeypatch)
    assert 'Demo data' in status and '6 of 6 active sources' in status

def test_overview_reports_sensors_offline_without_recent_readings(tmp_path,monkeypatch):
    path=tmp_path/'telemetry.db';conn=sqlite3.connect(path);init_db(conn)
    old=generate_zone_reading(ts=(datetime.now(timezone.utc)-timedelta(days=3)).timestamp(),zone_id='tomato-zone')
    on_message(None,{'conn':conn},SimpleNamespace(topic='test',payload=json.dumps(old).encode()));conn.close()
    status=_overview_status(path,monkeypatch)
    assert 'Sensors offline' in status and 'No readings in 24 h' in status
