"""Compatible paho-mqtt client factory (v1 and v2 APIs)."""

from __future__ import annotations

import paho.mqtt.client as mqtt


def make_client(client_id: str) -> mqtt.Client:
    try:
        # paho-mqtt 2.x
        return mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
        )
    except (AttributeError, TypeError):
        return mqtt.Client(client_id=client_id)
