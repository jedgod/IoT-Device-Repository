# System architecture

See the diagram at `diagrams/architecture.png`.

```
┌─────────────────┐    JSON/MQTT     ┌──────────────────┐
│ 1. Sensor       │ ───────────────► │ 2. MQTT Broker   │
│    Simulator    │                  │    HiveMQ public │
│    (Python)     │                  │    :1883         │
└─────────────────┘                  └────────┬─────────┘
                                              │ subscribe
                                              ▼
                                     ┌──────────────────┐
                                     │ 3. Subscriber    │
                                     │    paho-mqtt     │
                                     └────────┬─────────┘
                                              │ INSERT
                                              ▼
                                     ┌──────────────────┐
                                     │ 4. SQLite        │
                                     │    iot_data.db   │
                                     └────────┬─────────┘
                                              │ SELECT
                                              ▼
                                     ┌──────────────────┐
                                     │ 5. Visualization │
                                     │ Matplotlib /     │
                                     │ Streamlit / CSV  │
                                     └──────────────────┘
```

Topic used by this project: `ctec651/greenhousewatch/ipmcbit`  
(Change it in `src/config.py` if another student is publishing to the same name.)
