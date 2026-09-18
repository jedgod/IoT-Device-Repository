"""SQLite helpers for the GreenHouseWatch digital repository."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from config import DB_PATH, DATA_DIR

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sensor_data (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     REAL    NOT NULL,
    iso_time      TEXT    NOT NULL,
    device_id     TEXT    NOT NULL,
    temperature_c REAL    NOT NULL,
    humidity_pct  REAL    NOT NULL,
    soil_moisture_pct REAL NOT NULL,
    light_lux     REAL    NOT NULL,
    alert_flag    INTEGER NOT NULL DEFAULT 0,
    alert_reason  TEXT
);

CREATE TABLE IF NOT EXISTS greenhouse_zones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id TEXT NOT NULL UNIQUE,
    crop_name TEXT NOT NULL,
    description TEXT,
    temp_min_c REAL NOT NULL,
    temp_max_c REAL NOT NULL,
    humidity_min REAL NOT NULL,
    humidity_max REAL NOT NULL,
    soil_min REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS zone_telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL UNIQUE,
    zone_id TEXT NOT NULL,
    sensor_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    firmware_version TEXT,
    battery_pct REAL,
    signal_strength REAL,
    data_quality TEXT NOT NULL DEFAULT 'good',
    measured_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    temperature_c REAL NOT NULL,
    humidity_pct REAL NOT NULL,
    soil_moisture_pct REAL NOT NULL,
    light_lux REAL NOT NULL,
    alert_flag INTEGER NOT NULL DEFAULT 0,
    alert_state TEXT NOT NULL DEFAULT 'Normal',
    alert_severity TEXT NOT NULL DEFAULT 'info',
    alert_reason TEXT,
    FOREIGN KEY(zone_id) REFERENCES greenhouse_zones(zone_id)
);

CREATE TABLE IF NOT EXISTS alert_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    alert_state TEXT NOT NULL,
    alert_severity TEXT NOT NULL,
    rule_triggered TEXT NOT NULL,
    detection_time TEXT NOT NULL,
    acknowledgement_time TEXT,
    resolution_time TEXT,
    recommended_action TEXT,
    responsible_controller TEXT,
    FOREIGN KEY(message_id) REFERENCES zone_telemetry(message_id)
);

CREATE TABLE IF NOT EXISTS control_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id TEXT NOT NULL,
    command_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    started_at TEXT,
    completed_at TEXT,
    required_action TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS irrigation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone_id TEXT NOT NULL,
    triggered_by TEXT,
    started_at TEXT NOT NULL,
    stopped_at TEXT,
    duration_sec INTEGER,
    water_litres REAL,
    status TEXT NOT NULL DEFAULT 'planned'
);

CREATE INDEX IF NOT EXISTS idx_sensor_ts ON sensor_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_zone_telemetry_ts ON zone_telemetry(measured_at);
CREATE INDEX IF NOT EXISTS idx_alerts_zone ON alert_events(zone_id);
CREATE INDEX IF NOT EXISTS idx_cmd_zone ON control_commands(zone_id);
"""


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(db_path or DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: Optional[sqlite3.Connection] = None) -> None:
    own = conn is None
    if own:
        conn = connect()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    if own:
        conn.close()


def insert_zone(conn: sqlite3.Connection, zone: dict[str, Any]) -> int:
    cur = conn.execute(
        """
        INSERT OR REPLACE INTO greenhouse_zones (
            zone_id, crop_name, description, temp_min_c, temp_max_c,
            humidity_min, humidity_max, soil_min
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            zone["zone_id"],
            zone["crop_name"],
            zone.get("description"),
            float(zone["temp_min_c"]),
            float(zone["temp_max_c"]),
            float(zone["humidity_min"]),
            float(zone["humidity_max"]),
            float(zone["soil_min"]),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def insert_zone_telemetry(conn: sqlite3.Connection, reading: dict[str, Any]) -> int:
    cur = conn.execute(
        """
        INSERT OR REPLACE INTO zone_telemetry (
            message_id, zone_id, sensor_id, device_id, sequence_number,
            firmware_version, battery_pct, signal_strength, data_quality,
            measured_at, received_at, temperature_c, humidity_pct,
            soil_moisture_pct, light_lux, alert_flag, alert_state,
            alert_severity, alert_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reading["message_id"],
            reading["zone_id"],
            reading["sensor_id"],
            reading["device_id"],
            int(reading["sequence_number"]),
            reading.get("firmware_version"),
            reading.get("battery_pct"),
            reading.get("signal_strength"),
            reading.get("data_quality", "good"),
            reading["measured_at"],
            reading["received_at"],
            reading["temperature_c"],
            reading["humidity_pct"],
            reading["soil_moisture_pct"],
            reading["light_lux"],
            int(reading.get("alert_flag", 0)),
            reading.get("alert_state", "Normal"),
            reading.get("alert_severity", "info"),
            reading.get("alert_reason"),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def insert_alert_event(conn: sqlite3.Connection, alert: dict[str, Any]) -> int:
    cur = conn.execute(
        """
        INSERT INTO alert_events (
            message_id, zone_id, alert_state, alert_severity, rule_triggered,
            detection_time, acknowledgement_time, resolution_time,
            recommended_action, responsible_controller
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            alert["message_id"],
            alert["zone_id"],
            alert["alert_state"],
            alert["alert_severity"],
            alert["rule_triggered"],
            alert["detection_time"],
            alert.get("acknowledgement_time"),
            alert.get("resolution_time"),
            alert.get("recommended_action"),
            alert.get("responsible_controller"),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def seed_default_zones(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    default_zones = [
        {
            "zone_id": "tomato-zone",
            "crop_name": "Tomatoes",
            "description": "Heat tolerant zone focused on growth and moisture balance.",
            "temp_min_c": 20.0,
            "temp_max_c": 28.0,
            "humidity_min": 55.0,
            "humidity_max": 75.0,
            "soil_min": 45.0,
        },
        {
            "zone_id": "lettuce-zone",
            "crop_name": "Lettuce",
            "description": "Cool and stable growth zone for crisp leaf development.",
            "temp_min_c": 15.0,
            "temp_max_c": 22.0,
            "humidity_min": 60.0,
            "humidity_max": 80.0,
            "soil_min": 50.0,
        },
        {
            "zone_id": "cucumber-zone",
            "crop_name": "Cucumber",
            "description": "Warm, high-humidity fruiting zone for rapid vine growth.",
            "temp_min_c": 21.0,
            "temp_max_c": 29.0,
            "humidity_min": 65.0,
            "humidity_max": 85.0,
            "soil_min": 52.0,
        },
        {
            "zone_id": "carrot-zone",
            "crop_name": "Carrot",
            "description": "Cool-root zone focused on consistent soil moisture and moderate temperatures.",
            "temp_min_c": 12.0,
            "temp_max_c": 22.0,
            "humidity_min": 55.0,
            "humidity_max": 75.0,
            "soil_min": 48.0,
        },
        {
            "zone_id": "watermelon-zone",
            "crop_name": "Watermelon",
            "description": "Warm fruiting zone with strong irrigation demand and heat tolerance.",
            "temp_min_c": 24.0,
            "temp_max_c": 32.0,
            "humidity_min": 50.0,
            "humidity_max": 70.0,
            "soil_min": 46.0,
        },
        {
            "zone_id": "seedling-zone",
            "crop_name": "Seedlings",
            "description": "Sensitive propagation zone needing steady humidity and irrigation control.",
            "temp_min_c": 18.0,
            "temp_max_c": 24.0,
            "humidity_min": 65.0,
            "humidity_max": 82.0,
            "soil_min": 55.0,
        },
    ]
    rows = []
    for zone in default_zones:
        insert_zone(conn, zone)
        rows.append(zone)
    return rows


def seed_zone_telemetry(conn: sqlite3.Connection, count: int = 3) -> list[dict[str, Any]]:
    rows = []
    base_values = {
        "tomato-zone": {"temperature_c": 26.5, "humidity_pct": 62.0, "soil_moisture_pct": 52.0},
        "lettuce-zone": {"temperature_c": 19.0, "humidity_pct": 70.0, "soil_moisture_pct": 58.0},
        "cucumber-zone": {"temperature_c": 27.8, "humidity_pct": 78.0, "soil_moisture_pct": 61.0},
        "carrot-zone": {"temperature_c": 17.2, "humidity_pct": 68.0, "soil_moisture_pct": 56.0},
        "watermelon-zone": {"temperature_c": 29.4, "humidity_pct": 60.0, "soil_moisture_pct": 54.0},
        "seedling-zone": {"temperature_c": 21.5, "humidity_pct": 74.0, "soil_moisture_pct": 60.0},
    }
    for idx in range(count):
        for zone_id, values in base_values.items():
            msg_id = f"{zone_id}-seed-{idx + 1}"
            reading = {
                "message_id": msg_id,
                "zone_id": zone_id,
                "sensor_id": f"S-{idx + 1}",
                "device_id": f"GH-{zone_id.upper().replace('-', '')[:12]}-{idx + 1}",
                "sequence_number": idx + 1,
                "firmware_version": "1.4.0",
                "battery_pct": 90.0,
                "signal_strength": -35.0,
                "data_quality": "good",
                "measured_at": f"2026-09-16T00:{idx + 1:02d}:00Z",
                "received_at": f"2026-09-16T00:{idx + 1:02d}:05Z",
                "temperature_c": values["temperature_c"],
                "humidity_pct": values["humidity_pct"],
                "soil_moisture_pct": values["soil_moisture_pct"],
                "light_lux": 520.0 + idx * 50,
                "alert_flag": 0,
                "alert_state": "Normal",
                "alert_severity": "info",
                "alert_reason": "No active alert",
            }
            insert_zone_telemetry(conn, reading)
            rows.append(reading)
    return rows


def fetch_zone_summary(conn: Optional[sqlite3.Connection] = None) -> list[dict[str, Any]]:
    own = conn is None
    if own:
        conn = connect()
    cur = conn.execute(
        """
        SELECT
            z.zone_id,
            z.crop_name,
            t.temperature_c,
            t.humidity_pct,
            t.soil_moisture_pct,
            t.light_lux,
            COALESCE(t.alert_flag, 0) AS active_alert,
            COALESCE(t.alert_state, 'Normal') AS alert_state,
            COALESCE(t.alert_severity, 'info') AS alert_severity,
            COALESCE(t.alert_reason, 'No active alert') AS alert_reason
        FROM greenhouse_zones z
        LEFT JOIN (
            SELECT zone_id, MAX(id) AS latest_id
            FROM zone_telemetry
            GROUP BY zone_id
        ) latest ON latest.zone_id = z.zone_id
        LEFT JOIN zone_telemetry t ON t.id = latest.latest_id
        ORDER BY z.zone_id ASC
        """
    )
    rows = cur.fetchall()
    if own:
        conn.close()
    if not rows:
        return []
    columns = [col[0] for col in cur.description]
    return [dict(zip(columns, row)) for row in rows]


def acknowledge_alert(
    conn: sqlite3.Connection,
    zone_id: str,
    message_id: Optional[str] = None,
    controller: str = "system",
) -> dict[str, Any]:
    conn.row_factory = sqlite3.Row
    latest = conn.execute(
        """
        SELECT *
        FROM zone_telemetry
        WHERE zone_id = ?
        ORDER BY measured_at DESC, sequence_number DESC
        LIMIT 1
        """,
        (zone_id,),
    ).fetchone()

    if latest is None:
        raise ValueError(f"No telemetry found for zone {zone_id!r}")

    message_id = message_id or latest["message_id"]
    ack_time = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        UPDATE zone_telemetry
        SET alert_state = 'Acknowledged', alert_severity = 'info', alert_reason = 'Acknowledged by operator'
        WHERE message_id = ?
        """,
        (message_id,),
    )
    conn.execute(
        """
        INSERT INTO alert_events (
            message_id, zone_id, alert_state, alert_severity, rule_triggered,
            detection_time, acknowledgement_time, resolution_time,
            recommended_action, responsible_controller
        ) VALUES (?, ?, 'Acknowledged', ?, ?, ?, ?, NULL, 'Review crop response and continue monitoring', ?)
        """,
        (
            message_id,
            zone_id,
            latest["alert_severity"],
            latest["alert_reason"] or "manual_acknowledgement",
            latest["measured_at"],
            ack_time,
            controller,
        ),
    )
    conn.commit()
    row_cur = conn.execute(
        "SELECT * FROM zone_telemetry WHERE message_id = ?",
        (message_id,),
    )
    row = row_cur.fetchone()
    if row is None:
        return {}
    columns = [col[0] for col in row_cur.description]
    return dict(zip(columns, row))


def fetch_alert_history(conn: Optional[sqlite3.Connection] = None, zone_id: Optional[str] = None) -> list[dict[str, Any]]:
    own = conn is None
    if own:
        conn = connect()
    query = "SELECT * FROM alert_events"
    params: tuple[Any, ...] = ()
    if zone_id is not None:
        query += " WHERE zone_id = ?"
        params = (zone_id,)
    query += " ORDER BY detection_time DESC, id DESC"
    cur = conn.execute(query, params)
    rows = cur.fetchall()
    if own:
        conn.close()
    columns = [col[0] for col in cur.description]
    return [dict(zip(columns, row)) for row in rows]


def create_zone_command(
    conn: sqlite3.Connection,
    zone_id: str,
    command_type: str = "irrigation",
    status: str = "queued",
    required_action: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """
        INSERT INTO control_commands (
            zone_id, command_type, status, started_at, completed_at,
            required_action, notes
        ) VALUES (?, ?, ?, ?, NULL, ?, ?)
        """,
        (
            zone_id,
            command_type,
            status,
            started_at,
            required_action or "Monitor crop and continue irrigation decision process",
            notes,
        ),
    )
    conn.commit()
    row_cur = conn.execute("SELECT * FROM control_commands WHERE id = ?", (int(cur.lastrowid),))
    row = row_cur.fetchone()
    if row is None:
        return {}
    columns = [col[0] for col in row_cur.description]
    return dict(zip(columns, row))


def fetch_zone_commands(conn: Optional[sqlite3.Connection] = None, zone_id: Optional[str] = None) -> list[dict[str, Any]]:
    own = conn is None
    if own:
        conn = connect()
    query = "SELECT * FROM control_commands"
    params: tuple[Any, ...] = ()
    if zone_id is not None:
        query += " WHERE zone_id = ?"
        params = (zone_id,)
    query += " ORDER BY started_at DESC, id DESC"
    cur = conn.execute(query, params)
    rows = cur.fetchall()
    if own:
        conn.close()
    columns = [col[0] for col in cur.description]
    return [dict(zip(columns, row)) for row in rows]


def resolve_alert(
    conn: sqlite3.Connection,
    zone_id: str,
    message_id: Optional[str] = None,
    controller: str = "system",
) -> dict[str, Any]:
    latest = conn.execute(
        """
        SELECT *
        FROM zone_telemetry
        WHERE zone_id = ?
        ORDER BY measured_at DESC, sequence_number DESC
        LIMIT 1
        """,
        (zone_id,),
    ).fetchone()

    if latest is None:
        raise ValueError(f"No telemetry found for zone {zone_id!r}")

    message_id = message_id or latest["message_id"]
    resolution_time = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        UPDATE zone_telemetry
        SET alert_state = 'Resolved', alert_severity = 'info', alert_reason = 'Resolved by operator'
        WHERE message_id = ?
        """,
        (message_id,),
    )
    conn.execute(
        """
        INSERT INTO alert_events (
            message_id, zone_id, alert_state, alert_severity, rule_triggered,
            detection_time, acknowledgement_time, resolution_time,
            recommended_action, responsible_controller
        ) VALUES (?, ?, 'Resolved', ?, ?, ?, NULL, ?, 'Return zone to normal operating band', ?)
        """,
        (
            message_id,
            zone_id,
            latest["alert_severity"],
            latest["alert_reason"] or "manual_resolution",
            latest["measured_at"],
            resolution_time,
            controller,
        ),
    )
    conn.commit()
    row_cur = conn.execute(
        "SELECT * FROM zone_telemetry WHERE message_id = ?",
        (message_id,),
    )
    row = row_cur.fetchone()
    if row is None:
        return {}
    columns = [col[0] for col in row_cur.description]
    return dict(zip(columns, row))


def insert_reading(conn: sqlite3.Connection, reading: dict[str, Any]) -> int:
    cur = conn.execute(
        """
        INSERT INTO sensor_data (
            timestamp, iso_time, device_id,
            temperature_c, humidity_pct, soil_moisture_pct, light_lux,
            alert_flag, alert_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reading["timestamp"],
            reading["iso_time"],
            reading["device_id"],
            reading["temperature_c"],
            reading["humidity_pct"],
            reading["soil_moisture_pct"],
            reading["light_lux"],
            int(reading.get("alert_flag", 0)),
            reading.get("alert_reason"),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def insert_many(conn: sqlite3.Connection, readings: Iterable[dict[str, Any]]) -> int:
    rows = [
        (
            r["timestamp"],
            r["iso_time"],
            r["device_id"],
            r["temperature_c"],
            r["humidity_pct"],
            r["soil_moisture_pct"],
            r["light_lux"],
            int(r.get("alert_flag", 0)),
            r.get("alert_reason"),
        )
        for r in readings
    ]
    conn.executemany(
        """
        INSERT INTO sensor_data (
            timestamp, iso_time, device_id,
            temperature_c, humidity_pct, soil_moisture_pct, light_lux,
            alert_flag, alert_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def fetch_all(conn: Optional[sqlite3.Connection] = None) -> list[sqlite3.Row]:
    own = conn is None
    if own:
        conn = connect()
    rows = conn.execute(
        "SELECT * FROM sensor_data ORDER BY timestamp ASC"
    ).fetchall()
    if own:
        conn.close()
    return rows


def count_rows(conn: Optional[sqlite3.Connection] = None) -> int:
    own = conn is None
    if own:
        conn = connect()
    n = conn.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0]
    if own:
        conn.close()
    return int(n)


def print_schema() -> None:
    conn = connect()
    print("Database:", DB_PATH)
    print("\nTable schema (sensor_data):")
    for row in conn.execute("PRAGMA table_info(sensor_data)"):
        print(f"  {row['cid']:>2}  {row['name']:<22} {row['type']:<10} "
              f"{'NOT NULL' if row['notnull'] else ''} "
              f"{'PK' if row['pk'] else ''}")
    for table in ["greenhouse_zones", "zone_telemetry", "alert_events"]:
        print(f"\nTable schema ({table}):")
        for row in conn.execute(f"PRAGMA table_info({table})"):
            print(f"  {row['cid']:>2}  {row['name']:<22} {row['type']:<10} "
                  f"{'NOT NULL' if row['notnull'] else ''} "
                  f"{'PK' if row['pk'] else ''}")
    print(f"\nRow count: {count_rows(conn)}")
    conn.close()


if __name__ == "__main__":
    init_db()
    print_schema()
