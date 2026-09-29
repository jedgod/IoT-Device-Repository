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
import os
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
from simulator import generate_reading, generate_zone_reading
from config import ZONE_PROFILES

def publish_with_retry(client, topic, body):
    """Publish one message, reconnecting and resending it if the connection drops."""
    while True:
        try:
            info = client.publish(topic, body, qos=0)
            info.wait_for_publish(timeout=5)
            return
        except (RuntimeError, OSError) as error:
            print(f'Publish connection lost ({error}); reconnecting...')
            while True:
                try:
                    client.reconnect()
                    print('Reconnected; resending message.')
                    break
                except OSError as reconnect_error:
                    print(f'Reconnect failed ({reconnect_error}); retrying in 5 seconds.')
                    time.sleep(5)


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT publisher for GreenHouseWatch")
    parser.add_argument("--count", type=int, default=0, help="0 = run forever")
    parser.add_argument("--interval", type=float, default=PUBLISH_INTERVAL_SEC)
    parser.add_argument("--broker", default=MQTT_BROKER)
    parser.add_argument("--topic", default=MQTT_TOPIC)
    parser.add_argument('--zone', nargs='+', choices=[*ZONE_PROFILES, 'all'],
                        help="Attach zone metadata; list several zones or use 'all' to publish one reading per zone each interval")
    args = parser.parse_args()
    zones = list(ZONE_PROFILES) if args.zone and 'all' in args.zone else args.zone

    # A per-process client ID lets several publishers share the broker without disconnecting each other.
    client = make_client(f"{MQTT_CLIENT_PUB}-{os.getpid()}")
    print(f"Connecting to {args.broker}:{MQTT_PORT} …")
    client.connect(args.broker, MQTT_PORT, MQTT_KEEPALIVE)
    client.loop_start()

    sent = 0
    try:
        while args.count == 0 or sent < args.count:
            payloads = [generate_zone_reading(zone_id=zone, sequence_number=sent+1) for zone in zones] if zones else [generate_reading()]
            for payload in payloads:
                body = json.dumps(payload)
                publish_with_retry(client, args.topic, body)
                print(f"[{sent + 1}] published → {args.topic}")
                print(f"       {body}")
            sent += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nPublisher stopped.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
