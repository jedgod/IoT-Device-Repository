"""Export sensor_data to CSV for Google Sheets / Excel (Phase 5 Option B)."""

from __future__ import annotations

import csv

from config import CSV_PATH, DATA_DIR
from db import connect, fetch_all


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect()
    rows = fetch_all(conn)
    conn.close()
    if not rows:
        raise SystemExit("No rows in database. Run seed_database.py first.")

    fieldnames = list(rows[0].keys())
    with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
    print(f"Wrote {len(rows)} rows → {CSV_PATH}")


if __name__ == "__main__":
    main()
