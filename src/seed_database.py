"""
Seed SQLite with a realistic historical series so Phase 4/5 work offline
(even before the live MQTT demo). Default: 80 records (>= 50 required).
"""

from __future__ import annotations

import argparse

from db import (
    connect,
    init_db,
    insert_many,
    print_schema,
    seed_default_zones,
    seed_zone_telemetry,
)
from simulator import generate_series


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed iot_data.db")
    parser.add_argument("--n", type=int, default=80)
    parser.add_argument("--reset", action="store_true", help="drop existing rows first")
    args = parser.parse_args()

    conn = connect()
    init_db(conn)
    if args.reset:
        conn.execute("DELETE FROM sensor_data")
        conn.execute("DELETE FROM zone_telemetry")
        conn.execute("DELETE FROM greenhouse_zones")
        conn.execute("DELETE FROM alert_events")
        conn.execute("DELETE FROM control_commands")
        conn.execute("DELETE FROM irrigation_events")
        conn.commit()
        print("Existing rows deleted.")

    zone_rows = seed_default_zones(conn)
    telemetry_rows = seed_zone_telemetry(conn, count=3)

    rows = generate_series(n=args.n)
    inserted = insert_many(conn, rows)
    print(f"Inserted {inserted} readings.")
    print(f"Inserted {len(zone_rows)} greenhouse zones and {len(telemetry_rows)} zone telemetry samples.")
    print_schema()
    conn.close()


if __name__ == "__main__":
    main()
