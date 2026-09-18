from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import TEMP_MONTHLY_RANGE_C
from dashboard import build_irrigation_recommendation, calculate_forecast_metrics


def test_monthly_temperature_ranges_cover_september_to_december():
    expected_months = [
        "September",
        "October",
        "November",
        "December",
    ]

    for month in expected_months:
        assert month in TEMP_MONTHLY_RANGE_C
        assert "min_c" in TEMP_MONTHLY_RANGE_C[month]
        assert "max_c" in TEMP_MONTHLY_RANGE_C[month]
        assert TEMP_MONTHLY_RANGE_C[month]["min_c"] < TEMP_MONTHLY_RANGE_C[month]["max_c"]


def test_forecast_metrics_and_irrigation_logic():
    rows = [
        {"temperature_c": 20.0, "humidity_pct": 60.0, "soil_moisture_pct": 50.0},
        {"temperature_c": 21.0, "humidity_pct": 58.0, "soil_moisture_pct": 48.0},
        {"temperature_c": 22.0, "humidity_pct": 56.0, "soil_moisture_pct": 46.0},
        {"temperature_c": 24.0, "humidity_pct": 54.0, "soil_moisture_pct": 28.0},
        {"temperature_c": 25.0, "humidity_pct": 52.0, "soil_moisture_pct": 24.0},
    ]

    metrics = calculate_forecast_metrics(rows)
    assert metrics["forecast_horizon"] > 0
    assert metrics["mae_c"] >= 0
    assert metrics["rmse_c"] >= 0

    irrigation = build_irrigation_recommendation(rows)
    assert "Irrigate" in irrigation


def test_zone_simulation_generates_zone_telemetry_and_alert_lifecycle():
    from simulator import generate_zone_reading, evaluate_zone_alert

    reading = generate_zone_reading(zone_id="tomato-zone", anomaly="heat_spike")

    assert reading["zone_id"] == "tomato-zone"
    assert reading["device_id"].startswith("GH-")
    assert reading["sensor_id"].startswith("SENSOR-")
    assert reading["sequence_number"] >= 1
    assert "message_id" in reading
    assert "data_quality" in reading

    alert_state, severity, reason = evaluate_zone_alert(reading)
    assert alert_state in {"Normal", "Warning", "Critical", "Acknowledged", "Resolved"}
    assert severity in {"info", "warning", "critical"}
    assert reason


def test_zone_summary_and_alert_acknowledgement_helpers():
    from pathlib import Path
    import sqlite3

    from db import acknowledge_alert, fetch_zone_summary, init_db, insert_zone, insert_zone_telemetry

    db_path = Path("tmp/test_zone_summary.db")
    db_path.parent.mkdir(exist_ok=True, parents=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    init_db(conn)
    insert_zone(conn, {"zone_id": "tomato-zone", "crop_name": "Tomatoes", "description": "demo", "temp_min_c": 20, "temp_max_c": 28, "humidity_min": 55, "humidity_max": 75, "soil_min": 45})
    insert_zone_telemetry(conn, {
        "message_id": "msg-001",
        "zone_id": "tomato-zone",
        "sensor_id": "S-1",
        "device_id": "GH-TOMATO-01",
        "sequence_number": 1,
        "firmware_version": "1.0",
        "battery_pct": 90,
        "signal_strength": -40,
        "data_quality": "good",
        "measured_at": "2025-01-01T00:00:00Z",
        "received_at": "2025-01-01T00:00:05Z",
        "temperature_c": 29,
        "humidity_pct": 50,
        "soil_moisture_pct": 42,
        "light_lux": 500,
        "alert_flag": 1,
        "alert_state": "Warning",
        "alert_severity": "warning",
        "alert_reason": "high_temperature",
    })

    summary = fetch_zone_summary(conn)
    assert summary[0]["zone_id"] == "tomato-zone"
    assert summary[0]["active_alert"] == 1

    ack = acknowledge_alert(conn, zone_id="tomato-zone", message_id="msg-001", controller="operator-a")
    assert ack["alert_state"] == "Acknowledged"
    conn.close()
    db_path.unlink(missing_ok=True)


def test_alert_lifecycle_history_and_resolution():
    from pathlib import Path
    import sqlite3

    from db import acknowledge_alert, fetch_alert_history, init_db, insert_zone, insert_zone_telemetry, resolve_alert

    db_path = Path("tmp/test_alert_history.db")
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    init_db(conn)
    insert_zone(conn, {"zone_id": "lettuce-zone", "crop_name": "Lettuce", "description": "demo", "temp_min_c": 15, "temp_max_c": 22, "humidity_min": 60, "humidity_max": 80, "soil_min": 50})
    insert_zone_telemetry(conn, {
        "message_id": "msg-100",
        "zone_id": "lettuce-zone",
        "sensor_id": "S-2",
        "device_id": "GH-LETTUCE-01",
        "sequence_number": 7,
        "firmware_version": "1.0",
        "battery_pct": 82,
        "signal_strength": -36,
        "data_quality": "monitoring",
        "measured_at": "2025-02-01T00:00:00Z",
        "received_at": "2025-02-01T00:00:04Z",
        "temperature_c": 25,
        "humidity_pct": 52,
        "soil_moisture_pct": 48,
        "light_lux": 600,
        "alert_flag": 1,
        "alert_state": "Critical",
        "alert_severity": "critical",
        "alert_reason": "high_temperature,dry_soil",
    })

    ack = acknowledge_alert(conn, zone_id="lettuce-zone", message_id="msg-100", controller="operator-b")
    assert ack["alert_state"] == "Acknowledged"

    resolved = resolve_alert(conn, zone_id="lettuce-zone", message_id="msg-100", controller="operator-b")
    assert resolved["alert_state"] == "Resolved"
    history = fetch_alert_history(conn, zone_id="lettuce-zone")
    assert len(history) >= 2
    assert any(row["alert_state"] == "Acknowledged" for row in history)
    assert any(row["alert_state"] == "Resolved" for row in history)
    conn.close()
    db_path.unlink(missing_ok=True)


def test_irrigation_command_panel_logic():
    from pathlib import Path
    import sqlite3

    from db import create_zone_command, fetch_zone_commands, init_db, insert_zone

    db_path = Path("tmp/test_irrigation_commands.db")
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    init_db(conn)
    insert_zone(conn, {"zone_id": "seedling-zone", "crop_name": "Seedlings", "description": "demo", "temp_min_c": 18, "temp_max_c": 24, "humidity_min": 65, "humidity_max": 82, "soil_min": 55})

    command = create_zone_command(conn, zone_id="seedling-zone", command_type="irrigation", status="queued", required_action="Irrigate for 120s")
    assert command["command_type"] == "irrigation"
    assert command["status"] == "queued"

    history = fetch_zone_commands(conn, zone_id="seedling-zone")
    assert len(history) >= 1
    assert any(row["command_type"] == "irrigation" for row in history)
    conn.close()
    db_path.unlink(missing_ok=True)


def test_seed_default_zones_and_telemetry():
    from pathlib import Path
    import sqlite3

    from db import init_db, seed_default_zones, seed_zone_telemetry

    db_path = Path("tmp/test_default_zones.db")
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    init_db(conn)
    seed_default_zones(conn)
    seed_zone_telemetry(conn, count=3)

    zone_rows = conn.execute("SELECT zone_id FROM greenhouse_zones ORDER BY zone_id").fetchall()
    telem_rows = conn.execute("SELECT zone_id FROM zone_telemetry").fetchall()
    zone_ids = {row[0] for row in zone_rows}

    assert len(zone_rows) >= 6
    assert {"tomato-zone", "lettuce-zone", "cucumber-zone", "carrot-zone", "watermelon-zone"}.issubset(zone_ids)
    assert len(telem_rows) >= 3
    conn.close()
    db_path.unlink(missing_ok=True)
