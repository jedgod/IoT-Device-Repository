"""
Phase 3 — MQTT publisher.

Simulates a greenhouse sensor node and publishes JSON payloads
to the HiveMQ public broker.

Usage (from this folder):
    python publisher.py
    python publisher.py --count 30 --interval 2
    python publisher.py --zone all --seed 651          # reproducible simulated values
    python publisher.py --replay-history --days 7      # send the modelled history the charts use
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from datetime import timedelta

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
from config import MODELLED_ZONES, ZONE_PROFILES

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


def replay_history(client, topic: str, days: int, seed: int, rate: float = 25.0) -> int:
    """Send the modelled year (or its last `days`) exactly as build_history.py stores it.

    QoS 1 with per-batch confirmation; re-sending a batch is safe because the
    subscriber skips message IDs it already stored. Sending is paced to `rate`
    messages per second: the broker confirms receipt, not delivery, and the
    public broker drops messages a slower subscriber cannot keep up with.
    """
    from build_history import history_readings, load_cached_hours
    hours = load_cached_hours()
    readings = list(history_readings(hours, MODELLED_ZONES, seed))
    if days:
        cutoff = (hours[-1]["time"] - timedelta(days=days)).timestamp()
        readings = [r for r in readings if r["timestamp"] > cutoff]
    print(f"Replaying {len(readings):,} modelled readings ({readings[0]['iso_time'][:10]} to {readings[-1]['iso_time'][:10]}, seed {seed}) …")
    batch_size = 300
    for start in range(0, len(readings), batch_size):
        batch = readings[start:start + batch_size]
        while True:
            try:
                pending = []
                for r in batch:
                    pending.append(client.publish(topic, json.dumps(r), qos=1))
                    time.sleep(1 / rate)
                for info in pending:
                    info.wait_for_publish(timeout=30)
                    if not info.is_published():
                        raise RuntimeError("broker did not acknowledge in time")
                break
            except (RuntimeError, OSError, ValueError) as error:
                print(f"Batch not confirmed ({error}); reconnecting and resending …")
                time.sleep(2)
                try:
                    client.reconnect()
                except OSError:
                    pass
        print(f"  sent {min(start + batch_size, len(readings)):,} / {len(readings):,}")
    return len(readings)


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT publisher for GreenHouseWatch")
    parser.add_argument("--count", type=int, default=0, help="0 = run forever")
    parser.add_argument("--interval", type=float, default=PUBLISH_INTERVAL_SEC)
    parser.add_argument("--broker", default=MQTT_BROKER)
    parser.add_argument("--topic", default=MQTT_TOPIC)
    parser.add_argument('--zone', nargs='+', choices=[*ZONE_PROFILES, 'all'],
                        help="Attach zone metadata; list several zones or use 'all' to publish one reading per zone each interval")
    parser.add_argument("--seed", type=int, help="seed the random generator so simulated values are reproducible")
    parser.add_argument("--replay-history", action="store_true",
                        help="send the weather-driven modelled history (what the charts show) instead of live simulation")
    parser.add_argument("--days", type=int, default=7, help="with --replay-history: last N days, 0 = the whole year (default 7; the year is ~78,000 messages, ~52 min)")
    parser.add_argument("--rate", type=float, default=25.0,
                        help="with --replay-history: messages per second (default 25; the subscriber stores about 40/s)")
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    zones = list(ZONE_PROFILES) if args.zone and 'all' in args.zone else args.zone

    # A per-process client ID lets several publishers share the broker without disconnecting each other.
    client = make_client(f"{MQTT_CLIENT_PUB}-{os.getpid()}")
    print(f"Connecting to {args.broker}:{MQTT_PORT} …")
    client.connect(args.broker, MQTT_PORT, MQTT_KEEPALIVE)
    client.loop_start()

    if args.replay_history:
        from build_history import DEFAULT_SEED
        try:
            replay_history(client, args.topic, args.days, args.seed if args.seed is not None else DEFAULT_SEED, args.rate)
        finally:
            client.loop_stop()
            client.disconnect()
        return

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
