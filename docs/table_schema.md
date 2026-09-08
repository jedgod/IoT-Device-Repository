# Phase 4 — SQLite table schema

**Database file:** `data/iot_data.db`  
**Engine:** SQLite 3 (bundled with Python)  
**Table:** `sensor_data`

```sql
CREATE TABLE IF NOT EXISTS sensor_data (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp          REAL    NOT NULL,
    iso_time           TEXT    NOT NULL,
    device_id          TEXT    NOT NULL,
    temperature_c      REAL    NOT NULL,
    humidity_pct       REAL    NOT NULL,
    soil_moisture_pct  REAL    NOT NULL,
    light_lux          REAL    NOT NULL,
    alert_flag         INTEGER NOT NULL DEFAULT 0,
    alert_reason       TEXT
);

CREATE INDEX IF NOT EXISTS idx_sensor_ts ON sensor_data(timestamp);
```

## Column notes

| Column | SQLite type | Notes |
|---|---|---|
| `id` | INTEGER PK | Surrogate key |
| `timestamp` | REAL | Unix seconds; used for `ORDER BY` and charts |
| `iso_time` | TEXT | UTC ISO-8601 companion to `timestamp` |
| `device_id` | TEXT | Ready for a second sensor later (bonus) |
| `temperature_c` | REAL | °C |
| `humidity_pct` | REAL | 0–100 |
| `soil_moisture_pct` | REAL | 0–100 |
| `light_lux` | REAL | Ambient light |
| `alert_flag` | INTEGER | 0 = normal, 1 = threshold broken |
| `alert_reason` | TEXT | Comma-separated reason codes |

## Stored volume

The copy of `iot_data.db` shipped in this folder contains **80 readings** (assignment minimum is 50). Confirm any time with:

```bash
cd src
python db.py
```
