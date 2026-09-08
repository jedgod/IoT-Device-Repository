# GreenHouseWatch — Project Report (optional)

CTEC 651 Digital Repository Project 1  
Instructor: Prof. F. Njeh  
Due: 28 September 2026

## 1. What was built

An end-to-end local IoT digital repository for a smart greenhouse:

1. A Python simulator produces realistic multi-sensor JSON.
2. A publisher sends that JSON to HiveMQ (`broker.hivemq.com`).
3. A subscriber writes every valid payload into SQLite.
4. Matplotlib (and Streamlit) read the same database and draw charts.

The pipeline matches the architecture required by the assignment:
`Sensor Simulator → MQTT Broker → Subscriber → Database → Visualization`.

## 2. Design choices

- **SQLite instead of a server database.** The assignment specifies SQLite. It is file-based, needs no install, and is enough for thousands of sensor rows.
- **Four measurements, not one.** Temperature alone would satisfy the letter of the example code. Adding humidity, soil moisture, and light makes the repository look like a real greenhouse node and gives the charts something to compare.
- **Alerts as data, not as a separate system.** Thresholds are evaluated when a reading is created and stored as `alert_flag` / `alert_reason`. Visualization and the dashboard can filter on those columns without recomputing rules.
- **Offline fallback.** Public MQTT brokers can be blocked or noisy. `offline_pipeline.py` produces the same database and charts without a network so a recorded demo always works.

## 3. How to reproduce the demo

See the README. Short version:

```bash
pip install -r requirements.txt
cd src
python seed_database.py --reset --n 80
python visualize.py
# live MQTT
python subscriber.py          # terminal A
python publisher.py --count 20
# bonus
streamlit run dashboard.py    # from project root: streamlit run src/dashboard.py
```

## 4. Results

- 80 rows stored in `data/iot_data.db` (minimum required: 50).
- 7 alerts: dry soil at mid-day, high humidity at night, one cold reading.
- Temperature stayed under the 32 °C heat limit; the risk in this series is drought and overnight dampness, not overheating.
- Full interpretation: `docs/visualization_interpretation.md`.

## 5. Limitations and extensions

- The HiveMQ public broker is shared and unauthenticated. A private Mosquitto broker would be the next step for anything beyond class demo.
- One device only. `device_id` is already a column, so a second publisher is a small change.
- No model yet. The bonus list mentions basic AI; a next step is a simple threshold-or-forecast check on the last N rows.
