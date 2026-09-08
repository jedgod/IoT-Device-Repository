"""SQLite helpers for the GreenHouseWatch digital repository."""

from __future__ import annotations

import sqlite3
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

CREATE INDEX IF NOT EXISTS idx_sensor_ts ON sensor_data(timestamp);
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
    print(f"\nRow count: {count_rows(conn)}")
    conn.close()


if __name__ == "__main__":
    init_db()
    print_schema()
