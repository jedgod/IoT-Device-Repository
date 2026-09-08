"""
Phase 2 — IoT sensor simulation.

Generates realistic greenhouse readings:
  temperature (°C), humidity (%), soil moisture (%), light (lux)

Readings follow a simple day/night cycle so charts look like real time-series
instead of pure noise. A few injected anomalies support later interpretation.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from datetime import datetime, timezone
from typing import Optional

from config import (
    DEVICE_ID,
    HUMIDITY_MAX,
    HUMIDITY_MIN,
    PUBLISH_INTERVAL_SEC,
    SOIL_MIN,
    TEMP_MAX_C,
    TEMP_MIN_C,
)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def evaluate_alerts(reading: dict) -> tuple[int, Optional[str]]:
    reasons = []
    if reading["temperature_c"] > TEMP_MAX_C:
        reasons.append("high_temperature")
    if reading["temperature_c"] < TEMP_MIN_C:
        reasons.append("low_temperature")
    if reading["humidity_pct"] < HUMIDITY_MIN:
        reasons.append("low_humidity")
    if reading["humidity_pct"] > HUMIDITY_MAX:
        reasons.append("high_humidity")
    if reading["soil_moisture_pct"] < SOIL_MIN:
        reasons.append("dry_soil")
    if reasons:
        return 1, ",".join(reasons)
    return 0, None


def generate_reading(
    ts: Optional[float] = None,
    device_id: str = DEVICE_ID,
    anomaly: Optional[str] = None,
    soil_base: float = 55.0,
) -> dict:
    """
    Produce one sensor record.

    Day/night model uses the hour of day derived from `ts`:
      - Light peaks around 13:00 local-equivalent (UTC hour used for simplicity)
      - Temperature lags light by ~2 hours
      - Humidity is inverse to temperature
      - Soil moisture slowly decays; irrigation bumps are applied by the caller
    """
    ts = time.time() if ts is None else ts
    hour = datetime.fromtimestamp(ts, tz=timezone.utc).hour + (
        datetime.fromtimestamp(ts, tz=timezone.utc).minute / 60.0
    )

    # Smooth solar curve: 0 at night, 1 at midday
    solar = max(0.0, math.sin((hour - 6.0) / 12.0 * math.pi))
    solar = solar ** 1.2

    temp = 17.5 + 11.0 * solar + random.gauss(0, 0.45)
    humidity = 78.0 - 22.0 * solar + random.gauss(0, 1.4)
    light = 20.0 + 7800.0 * solar + random.gauss(0, 40.0)
    soil = soil_base + random.gauss(0, 0.6)

    if anomaly == "heat_spike":
        temp += random.uniform(8.0, 12.0)
        humidity -= random.uniform(10.0, 18.0)
    elif anomaly == "dry_soil":
        soil = random.uniform(16.0, 26.0)
    elif anomaly == "night_cold":
        temp = random.uniform(12.0, 15.5)
        light = random.uniform(0.0, 15.0)

    reading = {
        "timestamp": round(ts, 3),
        "iso_time": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
        "device_id": device_id,
        "temperature_c": round(_clamp(temp, 8.0, 45.0), 2),
        "humidity_pct": round(_clamp(humidity, 20.0, 98.0), 2),
        "soil_moisture_pct": round(_clamp(soil, 10.0, 95.0), 2),
        "light_lux": round(_clamp(light, 0.0, 12000.0), 1),
    }
    flag, reason = evaluate_alerts(reading)
    reading["alert_flag"] = flag
    reading["alert_reason"] = reason
    return reading


def generate_series(n: int = 80, start_ts: Optional[float] = None, step_sec: int = 900) -> list[dict]:
    """
    Historical series for the database / charts.
    Default: 80 points, 15 minutes apart ≈ 20 hours of greenhouse activity.
    """
    start_ts = start_ts if start_ts is not None else time.time() - n * step_sec
    soil = 62.0
    rows = []
    anomaly_at = {int(n * 0.28): "heat_spike", int(n * 0.62): "dry_soil", int(n * 0.85): "night_cold"}
    for i in range(n):
        if i > 0:
            soil -= random.uniform(0.15, 0.45)
        # Irrigation event mid-series
        if i == int(n * 0.65):
            soil = random.uniform(68.0, 75.0)
        reading = generate_reading(
            ts=start_ts + i * step_sec,
            anomaly=anomaly_at.get(i),
            soil_base=soil,
        )
        soil = reading["soil_moisture_pct"]
        rows.append(reading)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 — simulate greenhouse sensors")
    parser.add_argument("--count", type=int, default=20, help="number of live samples to print")
    parser.add_argument("--interval", type=float, default=PUBLISH_INTERVAL_SEC)
    parser.add_argument("--once", action="store_true", help="print a single JSON record and exit")
    args = parser.parse_args()

    if args.once:
        print(json.dumps(generate_reading(), indent=2))
        return

    print(f"# GreenHouseWatch simulator — {args.count} records, interval={args.interval}s")
    print("# Fields: timestamp, iso_time, device_id, temperature_c, humidity_pct, "
          "soil_moisture_pct, light_lux, alert_flag, alert_reason")
    for i in range(args.count):
        rec = generate_reading()
        print(json.dumps(rec))
        if i < args.count - 1:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
