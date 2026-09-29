"""
Phase 3 + Phase 4 — MQTT subscriber that persists every message to SQLite.

Usage (from this folder):
    python subscriber.py

Leave this running in one terminal, then start publisher.py in another.
"""

from __future__ import annotations

import argparse
import json
import math

from config import (
    MQTT_BROKER,
    MQTT_CLIENT_SUB,
    MQTT_KEEPALIVE,
    MQTT_PORT,
    MQTT_TOPIC,
)
from db import connect, init_db, insert_reading, count_rows, insert_zone, insert_zone_telemetry
from config import ZONE_PROFILES
from mqtt_util import make_client


def on_connect_v2(client, userdata, flags, reason_code, properties=None):
    print(f"Connected (rc={reason_code}). Subscribing to {userdata['topic']}")
    client.subscribe(userdata["topic"])


def on_connect_v1(client, userdata, flags, rc):
    print(f"Connected (rc={rc}). Subscribing to {userdata['topic']}")
    client.subscribe(userdata["topic"])


def on_message(client, userdata, msg):
    raw = msg.payload.decode("utf-8", errors="replace")
    print(f"RECV  {msg.topic}")
    print(f"      {raw}")
    try:
        reading = json.loads(raw)
        # Accept the assignment's minimal payload as well as our full schema
        if "temperature_c" not in reading and "temperature" in reading:
            reading["temperature_c"] = float(reading["temperature"])
        required = ("timestamp", "iso_time", "device_id", "temperature_c",
                    "humidity_pct", "soil_moisture_pct", "light_lux")
        if not all(k in reading for k in required):
            print("      skipped — payload missing required fields")
            return
        for key in ('timestamp','temperature_c','humidity_pct','soil_moisture_pct','light_lux'):
            reading[key] = float(reading[key])
            if not math.isfinite(reading[key]):
                raise ValueError('Non-finite sensor measurement')
        if not (0 <= reading['humidity_pct'] <= 100 and 0 <= reading['soil_moisture_pct'] <= 100 and reading['light_lux'] >= 0):
            raise ValueError('Invalid sensor measurement range')
        if reading.get('zone_id'):
            zone_id = reading['zone_id']
            if not userdata['conn'].execute('SELECT 1 FROM greenhouse_zones WHERE zone_id=?', (zone_id,)).fetchone():
                if zone_id not in ZONE_PROFILES:
                    print('      skipped — unknown zone; configure its thresholds first')
                    return
                profile = ZONE_PROFILES[zone_id]
                insert_zone(userdata['conn'], dict(profile, zone_id=zone_id, crop_name=profile['label']))
            from datetime import datetime, timezone
            reading['received_at'] = datetime.now(timezone.utc).isoformat()
            reading.setdefault('measured_at', reading['iso_time'])
            reading.setdefault('message_id', f"{reading['device_id']}-{reading['timestamp']}")
            reading.setdefault('sensor_id', reading['device_id'])
            reading.setdefault('sequence_number', 0)
            if userdata['conn'].execute('SELECT 1 FROM zone_telemetry WHERE message_id=?', (reading['message_id'],)).fetchone():
                print(f"      skipped — duplicate message {reading['message_id']} already stored")
                return
            row_id = insert_zone_telemetry(userdata['conn'], reading)
        else:
            row_id = insert_reading(userdata["conn"], reading)
        n = count_rows(userdata["conn"])
        print(f"      stored as id={row_id}  (legacy sensor rows={n})")
    except json.JSONDecodeError:
        print("      skipped — not valid JSON")
    except Exception as exc:
        print(f"      store error: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT subscriber + SQLite store")
    parser.add_argument("--broker", default=MQTT_BROKER)
    parser.add_argument("--topic", default=MQTT_TOPIC)
    args = parser.parse_args()

    conn = connect()
    init_db(conn)

    client = make_client(MQTT_CLIENT_SUB)
    client.user_data_set({"topic": args.topic, "conn": conn})
    # Bind both callback signatures; paho uses whichever matches the API version
    client.on_connect = on_connect_v2
    try:
        # If VERSION1 client, override
        import paho.mqtt.client as mqtt
        if not hasattr(mqtt, "CallbackAPIVersion"):
            client.on_connect = on_connect_v1
    except Exception:
        pass
    client.on_message = on_message

    print(f"Connecting to {args.broker}:{MQTT_PORT} …")
    client.connect(args.broker, MQTT_PORT, MQTT_KEEPALIVE)
    print("Listening. Ctrl+C to stop.")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nSubscriber stopped.")
    finally:
        client.disconnect()
        conn.close()


if __name__ == "__main__":
    main()
