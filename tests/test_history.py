from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import random
import sqlite3
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from build_history import SOURCE, ZoneModel, build, default_period, history_readings, store_weather, weather_hours
from config import HISTORY_ZONES, SITE_TIMEZONE, ZONE_PROFILES
from db import init_db
from dashboard_repository import read_hourly, summarise_periods


def _hours(start, count, temp=10.0, humidity=60.0, radiation=0.0):
    return [dict(time=start + timedelta(hours=i), temperature_c=temp, humidity_pct=humidity,
                 radiation_wm2=radiation, cloud_cover_pct=50) for i in range(count)]


def _db(tmp_path, hours):
    conn = sqlite3.connect(tmp_path / 'history.db')
    conn.row_factory = sqlite3.Row
    init_db(conn)
    build(conn, hours, HISTORY_ZONES)
    return conn


def test_default_period_is_twelve_whole_months():
    assert default_period(date(2026, 9, 29)) == (date(2025, 10, 1), date(2026, 9, 27))
    assert default_period(date(2027, 1, 2)) == (date(2026, 1, 1), date(2026, 12, 31))


def test_archive_hours_with_missing_values_are_skipped():
    payload = {'hourly': {'time': ['2026-01-01T00:00', '2026-01-01T01:00'], 'temperature_2m': [1.5, None],
                          'relative_humidity_2m': [80, 81], 'shortwave_radiation': [0, 0], 'cloud_cover': [10, 20]}}
    hours = weather_hours(payload)
    assert len(hours) == 1 and hours[0]['time'] == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_heating_holds_zone_near_minimum_on_a_cold_night():
    model = ZoneModel('tomato-zone', random.Random(1))
    local = datetime(2026, 1, 10, 2, tzinfo=timezone.utc)
    for hour in _hours(local, 12, temp=-5.0, humidity=70.0):
        values = model.step(hour, local)
    assert abs(values['temperature_c'] - (ZONE_PROFILES['tomato-zone']['temp_min_c'] + 1.0)) < 1.5


def test_humid_heatwave_overheats_lettuce():
    model = ZoneModel('lettuce-zone', random.Random(1))
    local = datetime(2026, 7, 4, 15, tzinfo=timezone.utc)
    for hour in _hours(local, 12, temp=34.0, humidity=60.0, radiation=800):
        values = model.step(hour, local)
    assert values['temperature_c'] > ZONE_PROFILES['lettuce-zone']['temp_max_c']


def test_build_is_labelled_and_rebuilds_without_duplicates(tmp_path):
    hours = _hours(datetime(2026, 3, 1, tzinfo=timezone.utc), 48)
    conn = _db(tmp_path, hours)
    build(conn, hours, HISTORY_ZONES)
    rows = conn.execute('SELECT source, COUNT(*) FROM zone_telemetry GROUP BY source').fetchall()
    assert [tuple(r) for r in rows] == [(SOURCE, 48 * len(HISTORY_ZONES))]
    assert conn.execute('SELECT COUNT(*) FROM outdoor_weather').fetchone()[0] == 48
    conn.close()


def test_period_summary_marks_partial_periods_and_counts_each_hour_once(tmp_path):
    hours = _hours(datetime(2026, 3, 1, 5, tzinfo=timezone.utc), 24 * 3 + 6)  # 05:00 UTC = local midnight (EST)
    conn = _db(tmp_path, hours)
    # A live reading in the same hour as modelled history must not double-count that hour.
    conn.execute("INSERT INTO zone_telemetry (message_id, zone_id, sensor_id, device_id, sequence_number, measured_at, received_at,"
                 " temperature_c, humidity_pct, soil_moisture_pct, light_lux, source) VALUES"
                 " ('live-1','tomato-zone','s','d',1,'2026-03-01T05:30:00+00:00','2026-03-01T05:30:00+00:00',22,60,60,0,'simulator')")
    conn.commit()
    conn.close()
    hourly = read_hourly(tmp_path / 'history.db')
    days = summarise_periods(hourly[hourly.zone_id == 'tomato-zone'], 'Day', SITE_TIMEZONE)
    assert days.hours.sum() == 78
    assert days.label.str.contains('partial').tolist() == [False, False, False, True]  # 4 Mar has 6 of 24 hours
    month = summarise_periods(hourly, 'Month', SITE_TIMEZONE)
    assert month.label.str.endswith('(partial)').all()


def test_chart_loader_keeps_whole_local_days(tmp_path):
    from visualize import load, period_summary
    hours = _hours(datetime(2026, 3, 1, tzinfo=timezone.utc), 24 * 4)
    conn = _db(tmp_path, hours)
    data, outdoor = load(conn)
    local = data.time.dt.tz_convert(SITE_TIMEZONE)
    assert local.min().hour == 0 and local.max().hour == 23
    assert len(outdoor) == len(data) // len(HISTORY_ZONES)
    summary = period_summary(data, outdoor, 'M')
    assert set(summary.zone_id) == set(HISTORY_ZONES)
    assert summary.outside_target_pct.between(0, 100).all()
    conn.close()


VALUE_COLUMNS = 'message_id, zone_id, measured_at, temperature_c, humidity_pct, soil_moisture_pct, light_lux, nutrient_level, ph_scale, alert_flag, alert_reason, source'


def test_history_is_reproducible_from_its_seed():
    hours = _hours(datetime(2026, 5, 1, tzinfo=timezone.utc), 48, temp=18.0, radiation=400)
    first = list(history_readings(hours, HISTORY_ZONES, seed=651))
    assert first == list(history_readings(hours, HISTORY_ZONES, seed=651))
    assert first != list(history_readings(hours, HISTORY_ZONES, seed=652))


def test_replay_through_subscriber_stores_the_same_rows_as_a_direct_build(tmp_path):
    import json
    from types import SimpleNamespace
    from subscriber import on_message
    hours = _hours(datetime(2026, 5, 1, tzinfo=timezone.utc), 48, temp=18.0, radiation=400)
    direct = _db(tmp_path, hours)
    via_mqtt = sqlite3.connect(tmp_path / 'mqtt.db')
    via_mqtt.row_factory = sqlite3.Row
    init_db(via_mqtt)
    store_weather(via_mqtt, hours, HISTORY_ZONES)
    readings = list(history_readings(hours, HISTORY_ZONES))
    for reading in readings + readings[:5]:  # Redelivered messages must not change anything.
        on_message(None, {'conn': via_mqtt, 'quiet': True}, SimpleNamespace(topic='t', payload=json.dumps(reading).encode()))
    query = f'SELECT {VALUE_COLUMNS} FROM zone_telemetry ORDER BY message_id'
    assert [tuple(r) for r in via_mqtt.execute(query)] == [tuple(r) for r in direct.execute(query)]
    direct.close()
    via_mqtt.close()


def test_simulator_seed_controls_simulated_values():
    from simulator import generate_zone_reading
    values = lambda r: {k: r[k] for k in ('temperature_c', 'humidity_pct', 'soil_moisture_pct', 'light_lux', 'battery_pct', 'sensor_id')}
    random.seed(7)
    first = values(generate_zone_reading(ts=1790000000, zone_id='lettuce-zone', sequence_number=1))
    random.seed(7)
    assert values(generate_zone_reading(ts=1790000000, zone_id='lettuce-zone', sequence_number=1)) == first


def test_visualize_writes_report_and_slide_charts_from_one_database(tmp_path):
    from visualize import save_all
    hours = _hours(datetime(2026, 3, 1, 5, tzinfo=timezone.utc), 24 * 10, temp=12.0, radiation=300)
    _db(tmp_path, hours).close()
    saved = save_all(tmp_path / 'out', tmp_path / 'history.db')
    names = sorted(p.relative_to(tmp_path / 'out').as_posix() for p in saved)
    assert names == sorted([f'0{i}_{n}.png' for i, n in enumerate(['last_7_days_hourly', 'daily_cycle_by_season', 'daily_temperature_year',
                                                                    'monthly_summary', 'quarterly_summary', 'year_calendar', 'indoor_vs_outdoor'], 1)]
                           + ['slides/days.png', 'slides/months.png', 'slides/quarters.png', 'slides/year.png',
                              'monthly_summary.csv', 'quarterly_summary.csv'])
