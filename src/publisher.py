"""
Phase 3 — MQTT publisher.

Simulates a greenhouse sensor node and publishes JSON payloads
to the HiveMQ public broker.

Usage (from this folder):
    python publisher.py
    python publisher.py --count 30 --interval 2
"""

from __future__ import annotations

import argparse
import json
import time

from config import (
    MQTT_BROKER,
    MQTT_CLIENT_PUB,
    MQTT_KEEPALIVE,
    MQTT_PORT,
    MQTT_TOPIC,
    PUBLISH_INTERVAL_SEC,
)
from mqtt_util import make_client
from simulator import generate_reading


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT publisher for GreenHouseWatch")
    parser.add_argument("--count", type=int, default=0, help="0 = run forever")
    parser.add_argument("--interval", type=float, default=PUBLISH_INTERVAL_SEC)
    parser.add_argument("--broker", default=MQTT_BROKER)
    parser.add_argument("--topic", default=MQTT_TOPIC)
    args = parser.parse_args()

    client = make_client(MQTT_CLIENT_PUB)
    print(f"Connecting to {args.broker}:{MQTT_PORT} …")
    client.connect(args.broker, MQTT_PORT, MQTT_KEEPALIVE)
    client.loop_start()

    sent = 0
    try:
        while args.count == 0 or sent < args.count:
            payload = generate_reading()
            body = json.dumps(payload)
            info = client.publish(args.topic, body, qos=0)
            info.wait_for_publish(timeout=5)
            sent += 1
            print(f"[{sent}] published → {args.topic}")
            print(f"       {body}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nPublisher stopped.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
