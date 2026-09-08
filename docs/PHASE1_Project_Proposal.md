# Phase 1 — Project Proposal
**GreenHouseWatch: A Local IoT Digital Repository for Smart Greenhouse Monitoring**

**Course:** CTEC 651 – Internet Technologies Discovery  
**Instructor:** Prof. F. Njeh  
**Student / Team:** IPMC BIT *(replace with your name)*  
**Due:** 7 September 2026

---

## Problem statement

Small greenhouse and urban-farm operators lose plants when temperature, humidity, or soil moisture drift outside a narrow safe band — often overnight or during mid-day heat, when nobody is watching a thermometer. Commercial IoT platforms exist, but they are paid, cloud-locked, and heavier than a class-scale or hobby greenhouse needs. The problem this project addresses is: **how can we capture, store, and inspect greenhouse sensor data locally, with only free tools, so that out-of-range conditions are visible instead of silent?**

## Use case description

GreenHouseWatch simulates a single greenhouse node (`GH-SENSOR-01`) that behaves like a real multi-sensor pack:

- air temperature (°C)
- relative humidity (%)
- soil moisture (%)
- ambient light (lux)

The node publishes a JSON reading every two seconds over **MQTT** to the free HiveMQ public broker (`broker.hivemq.com:1883`). A Python subscriber receives each message and writes it into a local **SQLite** digital repository (`iot_data.db`). Matplotlib (and an optional Streamlit dashboard) then turn that repository into time-series charts and an alert summary.

The simulator is not pure random noise. It follows a day/night solar curve (light and temperature rise after dawn and fall after dusk; humidity moves in the opposite direction). Soil moisture slowly dries and is restored by a mid-series “irrigation” event. A few injected anomalies (dry soil, night-time cold, humidity drift) give the visualizations something real to explain.

This pattern matches production IoT systems used in smart agriculture: sensor → message bus → store → dashboard.

## Data fields

| Field | Example | Role |
|---|---|---|
| `timestamp` | `1788741081.58` | Unix time for sorting / plotting |
| `iso_time` | `2026-09-07T12:46:21+00:00` | Human-readable UTC clock |
| `device_id` | `GH-SENSOR-01` | Which node sent the reading |
| `temperature_c` | `28.13` | Air temperature |
| `humidity_pct` | `56.07` | Relative humidity |
| `soil_moisture_pct` | `21.56` | Root-zone moisture |
| `light_lux` | `7693.4` | Day/night indicator |
| `alert_flag` | `1` | 1 = at least one threshold broken |
| `alert_reason` | `dry_soil` | Why the alert fired |

Safe operating band used by the alert logic: temperature **16–32 °C**, humidity **40–80 %**, soil moisture **≥ 30 %**.

## System architecture

```
Sensor Simulator (Python)
        ↓  JSON over MQTT
HiveMQ Public Broker  (broker.hivemq.com:1883)
        ↓  topic ctec651/greenhousewatch/ipmcbit
Subscriber (Python / paho-mqtt)
        ↓  INSERT
SQLite  iot_data.db  →  Matplotlib / Streamlit / CSV
```

The full diagram is `diagrams/architecture.png`.

## Tools (free only)

Python · paho-mqtt · HiveMQ public broker · SQLite · Matplotlib · (optional) Streamlit · Google Sheets/Excel via CSV export.
