"""
Build a year of hourly greenhouse history driven by real Bowie, MD weather.

Outdoor weather is the Open-Meteo historical archive (free, no API key). Indoor
conditions are MODELLED from it: solar gain, a heating setpoint, ventilation and
evaporative cooling, misting, daily irrigation and weekly nutrient changes, using
each zone's crop targets. Rows are stored with source 'weather model' so they are
never mistaken for physical sensor readings.

Usage (from the project root):
    python src/build_history.py                 # 1 Oct last year to 2 days ago
    python src/build_history.py --start 2025-10-01 --end 2026-09-27
    python src/build_history.py --offline       # rebuild from the cached weather file
"""

from __future__ import annotations

import argparse
import json
import math
import random
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from config import (
    HISTORY_ZONES, SITE_LATITUDE, SITE_LONGITUDE, SITE_TIMEZONE,
    WEATHER_HISTORY_PATH, ZONE_PROFILES,
)
from db import connect, init_db, insert_zone, insert_zone_telemetry

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
SOURCE = "weather model"
WEATHER_SOURCE = "Open-Meteo archive"
HOURLY_FIELDS = "temperature_2m,relative_humidity_2m,shortwave_radiation,cloud_cover"


def default_period(today: date | None = None) -> tuple[date, date]:
    """Twelve whole months up to the archive's lag (about two days)."""
    today = today or date.today()
    end = today - timedelta(days=2)
    # Start on the first of the month after the same month last year: 2026-09-27 -> 2025-10-01.
    start = date(end.year, 1, 1) if end.month == 12 else date(end.year - 1, end.month + 1, 1)
    return start, end


def fetch_weather(start: date, end: date) -> dict:
    query = urlencode({
        "latitude": SITE_LATITUDE, "longitude": SITE_LONGITUDE,
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "hourly": HOURLY_FIELDS, "timezone": "UTC",
    })
    with urlopen(f"{ARCHIVE_URL}?{query}", timeout=60) as response:
        payload = json.load(response)
    if "hourly" not in payload:
        raise SystemExit(f"Weather archive returned no hourly data: {payload.get('reason', payload)}")
    return payload


def weather_hours(payload: dict) -> list[dict]:
    hourly = payload["hourly"]
    hours = []
    for i, stamp in enumerate(hourly["time"]):
        values = [hourly[k][i] for k in ("temperature_2m", "relative_humidity_2m", "shortwave_radiation")]
        if any(v is None for v in values):
            continue  # The archive leaves the most recent hours empty until they are processed.
        hours.append({
            "time": datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc),
            "temperature_c": float(values[0]),
            "humidity_pct": float(values[1]),
            "radiation_wm2": float(values[2]),
            "cloud_cover_pct": hourly["cloud_cover"][i],
        })
    return hours


def saturation_kpa(temp_c: float) -> float:
    return 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))


def wet_bulb_c(temp_c: float, humidity_pct: float) -> float:
    """Stull (2011) wet-bulb approximation; the floor for evaporative pad cooling."""
    rh = min(99.0, max(5.0, humidity_pct))
    return (temp_c * math.atan(0.151977 * math.sqrt(rh + 8.313659)) + math.atan(temp_c + rh)
            - math.atan(rh - 1.676331) + 0.00391838 * rh ** 1.5 * math.atan(0.023101 * rh) - 4.686035)


class ZoneModel:
    """Hour-by-hour indoor response of one zone to outdoor weather and its controls."""

    def __init__(self, zone_id: str, rng: random.Random):
        self.zone_id = zone_id
        self.profile = ZONE_PROFILES[zone_id]
        self.rng = rng
        self.temp = None
        self.soil = self.profile["soil_min"] + 20
        self.nutrient = 72.0
        self.ph = 6.3

    def step(self, hour: dict, local: datetime) -> dict:
        p, rng = self.profile, self.rng
        outdoor, radiation = hour["temperature_c"], hour["radiation_wm2"]
        daytime = radiation > 5

        # Temperature: solar gain (a 40% shade cloth is drawn on hot days), then heating to the
        # setpoint, or venting with evaporative pad cooling, which cannot go below the pad's
        # wet-bulb limit - so humid heatwaves still overheat the house.
        shade = 0.6 if outdoor > 22 else 1.0
        passive = outdoor + 2.0 + 0.018 * shade * radiation
        heat_setpoint = p["temp_min_c"] + (1.5 if daytime else 1.0)
        vent_setpoint = p["temp_max_c"] - 1.5
        venting = 0.0
        if passive < heat_setpoint:
            target = min(heat_setpoint, outdoor + 35.0)  # Heater capacity limits the lift in deep cold.
        elif passive > vent_setpoint:
            excess = passive - vent_setpoint
            pad_floor = outdoor - 0.8 * (outdoor - wet_bulb_c(outdoor, hour["humidity_pct"]))
            target = max(pad_floor + 1.0, vent_setpoint + 0.15 * excess)
            venting = min(1.0, excess / 10)
        else:
            target = passive
        self.temp = target if self.temp is None else 0.65 * target + 0.35 * self.temp
        temp = self.temp + rng.gauss(0, 0.3)

        # Humidity: outdoor vapour plus crop transpiration, then misting or dehumidifying.
        vapour = hour["humidity_pct"] / 100 * saturation_kpa(outdoor)
        vapour += (0.25 + 0.6 * radiation / 800) * (1 - 0.6 * venting)
        humidity = 100 * vapour / saturation_kpa(temp)
        if humidity < p["humidity_min"]:
            humidity = min(p["humidity_min"] + 3, humidity + 35)  # High-pressure fogging capacity
        elif humidity > p["humidity_max"]:
            humidity = max(p["humidity_max"] - 2, humidity - 18)  # Vent-and-heat dehumidifying
        humidity = min(99.0, max(20.0, humidity + rng.gauss(0, 1.0)))

        # Soil moisture: evapotranspiration, with morning irrigation and an afternoon top-up.
        self.soil -= 0.05 + 0.0009 * radiation + 0.02 * max(temp - 20, 0)
        missed = rng.random() < 0.03  # An occasional missed cycle (valve fault, empty tank)
        if local.hour == 6 and not missed:
            self.soil = p["soil_min"] + 22 + rng.gauss(0, 1.5)
        elif local.hour == 14 and self.soil < p["soil_min"] + 4 and not missed:
            self.soil = p["soil_min"] + 15 + rng.gauss(0, 1.5)
        self.soil = min(95.0, max(10.0, self.soil))

        # Nutrient solution: slow depletion and pH drift, replaced every Monday at 09:00.
        if local.weekday() == 0 and local.hour == 9:
            self.nutrient, self.ph = 72.0 + rng.gauss(0, 1), 6.3 + rng.gauss(0, 0.05)
        self.nutrient -= 0.05 + rng.gauss(0, 0.02)
        self.ph += 0.0025 + rng.gauss(0, 0.004)

        return {
            "temperature_c": round(temp, 2),
            "humidity_pct": round(humidity, 2),
            "soil_moisture_pct": round(self.soil, 2),
            "light_lux": round(radiation * 0.7 * 110, 1),  # 70% glazing transmission, ~110 lux per W/m²
            "nutrient_level": round(self.nutrient, 1),
            "ph_scale": round(self.ph, 2),
        }


def build(conn, hours: list[dict], zones: list[str], seed: int = 651) -> int:
    rng = random.Random(seed)
    local_tz = ZoneInfo(SITE_TIMEZONE)
    for zone_id in zones:
        if not conn.execute("SELECT 1 FROM greenhouse_zones WHERE zone_id=?", (zone_id,)).fetchone():
            profile = ZONE_PROFILES[zone_id]
            insert_zone(conn, dict(profile, zone_id=zone_id, crop_name=profile["label"]))
    conn.executemany(
        "INSERT OR REPLACE INTO outdoor_weather VALUES (?, ?, ?, ?, ?, ?)",
        [(h["time"].isoformat(), h["temperature_c"], h["humidity_pct"], h["radiation_wm2"],
          h["cloud_cover_pct"], WEATHER_SOURCE) for h in hours],
    )
    # Rebuilding replaces the previous model run rather than duplicating it.
    conn.execute("DELETE FROM zone_telemetry WHERE source = ?", (SOURCE,))
    models = {zone_id: ZoneModel(zone_id, rng) for zone_id in zones}
    stored = 0
    for sequence, hour in enumerate(hours, start=1):
        local = hour["time"].astimezone(local_tz)
        for zone_id, model in models.items():
            values = model.step(hour, local)
            stamp = hour["time"].isoformat()
            insert_zone_telemetry(conn, {
                "message_id": f"hist-{zone_id}-{hour['time']:%Y%m%d%H}",
                "zone_id": zone_id,
                "sensor_id": f"MODEL-{zone_id}",
                "device_id": "WEATHER-MODEL",
                "sequence_number": sequence,
                "firmware_version": None,
                "data_quality": "modelled",
                "measured_at": stamp,
                "received_at": stamp,
                "source": SOURCE,
                **values,
            }, commit=False)
            stored += 1
    conn.commit()
    return stored


def main() -> None:
    default_start, default_end = default_period()
    parser = argparse.ArgumentParser(description="Build weather-driven greenhouse history")
    parser.add_argument("--start", type=date.fromisoformat, default=default_start)
    parser.add_argument("--end", type=date.fromisoformat, default=default_end)
    parser.add_argument("--offline", action="store_true", help="use the cached weather file only")
    args = parser.parse_args()

    if args.offline:
        payload = json.loads(WEATHER_HISTORY_PATH.read_text(encoding="utf-8"))
        print(f"Using cached weather: {WEATHER_HISTORY_PATH.name}")
    else:
        print(f"Downloading hourly weather for Bowie, MD, {args.start} to {args.end} …")
        payload = fetch_weather(args.start, args.end)
        WEATHER_HISTORY_PATH.write_text(json.dumps(payload), encoding="utf-8")
    hours = weather_hours(payload)
    if not hours:
        raise SystemExit("No complete weather hours available.")

    conn = connect()
    init_db(conn)
    stored = build(conn, hours, HISTORY_ZONES)
    conn.close()
    print(f"Stored {len(hours):,} weather hours ({hours[0]['time']:%Y-%m-%d} to {hours[-1]['time']:%Y-%m-%d} UTC)")
    print(f"Stored {stored:,} modelled readings for {', '.join(HISTORY_ZONES)} (source '{SOURCE}')")


if __name__ == "__main__":
    main()
