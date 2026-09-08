"""
Offline end-to-end demo (no internet / no MQTT broker required).

Simulates sensors, writes them to SQLite, exports CSV, and builds charts.
Useful when HiveMQ is unreachable or for a recorded demo fallback.
"""

from __future__ import annotations

from db import connect, init_db, insert_many, print_schema
from export_csv import main as export_csv
from simulator import generate_series
from visualize import save_all


def main() -> None:
    conn = connect()
    init_db(conn)
    existing = conn.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0]
    if existing < 50:
        rows = generate_series(n=80)
        insert_many(conn, rows)
        print(f"Seeded {len(rows)} readings (db previously had {existing}).")
    else:
        print(f"Database already has {existing} readings — leaving them in place.")
    conn.close()
    print_schema()
    export_csv()
    save_all()
    print("\nOffline pipeline complete.")


if __name__ == "__main__":
    main()
