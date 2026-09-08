"""
Seed SQLite with a realistic historical series so Phase 4/5 work offline
(even before the live MQTT demo). Default: 80 records (>= 50 required).
"""

from __future__ import annotations

import argparse

from db import connect, init_db, insert_many, count_rows, print_schema
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
        conn.commit()
        print("Existing rows deleted.")

    rows = generate_series(n=args.n)
    inserted = insert_many(conn, rows)
    print(f"Inserted {inserted} readings.")
    print_schema()
    conn.close()


if __name__ == "__main__":
    main()
