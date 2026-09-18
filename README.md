# GreenHouseWatch-Local IoT Digital Repository

**Course:** CTEC 651 – Internet Technologies Discovery  
**Instructor:** Prof. F. Njeh  
**Assignment:** Digital Repository Project 1 (due 28 September 2026)  
**Use case:** Smart greenhouse climate and soil monitoring

This folder is a complete, runnable implementation of every required phase:

```
Sensor Simulator → MQTT Broker (HiveMQ) → Subscriber → SQLite → Visualization
```

All tools are free: Python, HiveMQ public broker, SQLite, Matplotlib, optional Streamlit.

---

## Folder map

```
IoT-Digital-Repository/
├── README.md
├── requirements.txt
├── docs/                         Phase 1 proposal, schema, interpretation
├── diagrams/architecture.png     Phase 1 architecture diagram
├── src/                          All Python programs
│   ├── simulator.py              Phase 2
│   ├── publisher.py              Phase 3
│   ├── subscriber.py             Phase 3 + 4 (writes SQLite)
│   ├── db.py / seed_database.py  Phase 4
│   ├── visualize.py / export_csv.py   Phase 5
│   ├── dashboard.py              Phase 6 bonus
│   └── offline_pipeline.py       Full demo without internet
├── data/
│   ├── iot_data.db               Pre-seeded SQLite file (80 records)
│   └── sensor_data.csv           Excel / Google Sheets export
├── outputs/                      Four PNG charts
├── samples/                      Sample console output
└── presentation/                 Phase 7 slides
```

---

## Setup (once)

```bash
cd IoT-Digital-Repository
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`sqlite3` is built into Python — no extra install.

---

## How to run each phase

### Phase 2 — simulate sensors

```bash
cd src
python simulator.py --count 20 --interval 2
python simulator.py --once          # one JSON record
```

Sample console output is saved in `samples/phase2_sample_output.txt`.

### Phase 3 — MQTT transmission

Open **two terminals**. Change the topic in `src/config.py` if the public broker is noisy.

```bash
# Terminal A
cd src
python subscriber.py

# Terminal B
cd src
python publisher.py --count 20 --interval 2
```

Broker: `broker.hivemq.com:1883`  
Topic: `ctec651/greenhousewatch/ipmcbit`

Take a screenshot of both terminals for the Phase 3 deliverable.

### Phase 4 — storage

The subscriber already inserts every valid message into `data/iot_data.db`.

The database in this folder is **already seeded with 80 records** (assignment asks for at least 50).

```bash
cd src
python db.py                  # print schema + row count
python seed_database.py --reset --n 80    # rebuild if needed
```

### Phase 5 — visualization

```bash
cd src
python visualize.py           # writes 4 PNGs into ../outputs/
python export_csv.py          # writes ../data/sensor_data.csv
```

Open the CSV in Google Sheets or Excel for Option B.

Read `docs/visualization_interpretation.md` for the short written analysis.

### Phase 6 — optional dashboard

```bash
# from project root
streamlit run src/dashboard.py
```

### Offline / recorded demo (no broker)

```bash
cd src
python offline_pipeline.py
```

This reseeds if needed, exports CSV, and rebuilds the charts.

---

## Data fields

| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER | Auto-increment primary key |
| `timestamp` | REAL | Unix time |
| `iso_time` | TEXT | UTC ISO-8601 |
| `device_id` | TEXT | Sensor node id (`GH-SENSOR-01`) |
| `temperature_c` | REAL | Air temperature °C |
| `humidity_pct` | REAL | Relative humidity % |
| `soil_moisture_pct` | REAL | Soil moisture % |
| `light_lux` | REAL | Ambient light |
| `alert_flag` | INTEGER | 1 if any threshold is broken |
| `alert_reason` | TEXT | `high_temperature`, `dry_soil`, … |

Safe bands used by the alert logic: temperature 16–32 °C, humidity 40–80 %, soil moisture ≥ 30 %.

---

## Deliverable checklist

| Phase | Due | What to submit from this folder |
|---|---|---|
| 1 Design | 7 Sep 2026 | `docs/PHASE1_Project_Proposal.md` (or `.docx`) + `diagrams/architecture.png` |
| 2 Simulation | 14 Sep 2026 | `src/simulator.py` + `samples/phase2_sample_output.txt` |
| 3 MQTT | 21 Sep 2026 | `src/publisher.py`, `src/subscriber.py` + live screenshot |
| 4 Storage | 28 Sep 2026 | `data/iot_data.db` + schema in `docs/table_schema.md` |
| 5 Viz | 28 Sep 2026 | `outputs/*.png` + `docs/visualization_interpretation.md` |
| 6 Bonus | 28 Sep 2026 | `src/dashboard.py` |
| 7 Presentation | 28 Sep 2026 | `presentation/GreenHouseWatch_Slides.pptx` + live/recorded demo |

---

## Notes

- Use **only free tools** (assignment rule). This project does.
- If HiveMQ is blocked on campus Wi-Fi, use `offline_pipeline.py` for the recorded demo and still submit the publisher/subscriber source.
- Edit `src/config.py` to change the MQTT topic, device id, or alert limits.
- Creativity extras already included: four sensors, alert flags, day/night cycle, irrigation event, Streamlit dashboard.
