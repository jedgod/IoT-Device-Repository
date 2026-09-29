# GreenHouseWatch-Local IoT Digital Repository

### Reference dashboard preview

The operations overview follows the supplied green greenhouse design. Its layout
adapts to laptop, standard desktop, and ultrawide windows: metric cards wrap and
larger panels stack as space decreases. Smaller windows scroll vertically.

Run from this folder with `.venv\Scripts\python.exe -m streamlit run src/dashboard.py`.
Install `requirements.txt` first; the dashboard uses Streamlit 1.63 or newer.
Restart an already-running server once after this update to reload shared UI modules.

The dashboard now reads the actual SQLite repository every five seconds. Overview,
Zones, Analytics, and Data share real stored measurements and filtered CSV exports.
Overview focuses on the three primary zones and core environmental trend modes:
temperature and humidity, soil moisture, nutrient level, and pH scale. The Zones
page contains the full configured crop catalog, including Tomato, Lettuce, Cucumber,
Carrot, Corn, Onion, Watermelon, and Seedlings. Analytics provides selectable
metric charts, zone comparison, overall averages, and light analysis.

Freshness and provenance labels distinguish recent, stale, seeded, and simulated
readings. The dashboard treats readings older than two minutes as stale. The sidebar
clock updates every second, and collapsing the sidebar expands the main page.
OpenWeatherMap supplies the Forecast page, which defaults to Bowie, Maryland,
and includes current-weather cards, daily summaries, greenhouse impact
recommendations, indoor/outdoor comparisons, risk indicators, and CSV export.
Irrigation is visibly marked
`SIMULATION MODE` and disabled until water supply, valve, and controller checks
are available; no physical actuator is configured.

See [Live dashboard setup and data contract](docs/live_dashboard.md) for startup,
sensor integration, freshness rules, and current limits.

**Course:** CTEC 651-Internet Technologies Discovery  
**Instructor:** Prof. F. Njeh  
**Project:** Digital Repository Project 1 (due 28 September 2026)  
**Use case:** Smart greenhouse climate and soil monitoring

This folder is a complete, runnable implementation of every required phase:

```
Sensor Simulator → MQTT Broker (HiveMQ) → Subscriber → SQLite → Visualization
```

The project also includes a live SQLite-backed Streamlit dashboard and an OpenWeatherMap five-day outdoor forecast.

## Project highlights

GreenHouseWatch combines a simulated greenhouse sensor pipeline with an interactive dashboard for monitoring temperature, humidity, soil moisture, nutrient level, pH, and light. The dashboard includes stored telemetry trends, target bands, crop-specific zone health, source freshness, CSV export, and a five-day outdoor forecast. This makes the repository useful both as an assignment deliverable and as a practical climate-monitoring prototype.

All tools are free: Python, HiveMQ public broker, SQLite, Matplotlib, optional Streamlit.

---

## Dashboard preview

> Placeholder screenshots to be added when the live dashboard is captured for the final submission.

- Figure 1: GreenHouseWatch dashboard overview showing live readings and environmental metrics.
- Figure 2: Monthly temperature summary table for September, October, November, and December.
- Figure 3: Forecast month-ahead view with current temperature, expected temperature, and safe-range band.
- Figure 4: Alert and condition summary panel for greenhouse threshold monitoring.

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
│   ├── build_history.py          Phase 5: a year of history from real Bowie weather
│   ├── visualize.py / export_csv.py   Phase 5
│   ├── dashboard.py              Phase 6 bonus
│   └── offline_pipeline.py       Full demo without internet
├── data/
│   ├── iot_data.db               Pre-seeded SQLite file (80 records)
│   ├── sensor_data.csv           Excel / Google Sheets export
│   └── weather_history_bowie.json  Cached hourly Bowie weather (Open-Meteo)
├── outputs/                      Seven PNG charts + monthly/quarterly CSV summaries
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

### Phase 2: simulate sensors

```bash
cd src
python simulator.py --count 20 --interval 2
python simulator.py --once          # one JSON record
```

Sample console output is saved in `samples/phase2_sample_output.txt`.

### Phase 3: MQTT transmission

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

The publisher retries and reconnects automatically after a transient broker
disconnect. For a continuous demo, one publisher can cover every zone, or list
specific zones. Each publisher uses its own client ID, so several can run at once:

```bash
python src/publisher.py --zone all --interval 10
python src/publisher.py --zone tomato-zone lettuce-zone seedling-zone --interval 10
```

The Overview status counts sources that reported in the last 24 hours. It shows
"Sensors offline" until a publisher is running and the subscriber is storing readings.

Take a screenshot of both terminals for the Phase 3 deliverable.

### Phase 4: storage

The subscriber already inserts every valid message into `data/iot_data.db`.

The database in this folder is **already seeded with 80 records** (assignment asks for at least 50).

```bash
cd src
python db.py                  # print schema + row count
python seed_database.py --reset --n 80    # rebuild if needed
```

### Phase 5: visualization

The charts cover a full year so they can be read by day, month, quarter and year.
Outdoor weather is **real**: hourly Bowie, MD data from the free Open-Meteo archive.
Indoor conditions for the Tomato, Lettuce and Seedling zones are **modelled** from
that weather (heating, shading, venting with pad cooling, fogging, irrigation), and
stored with `source = 'weather model'` so they are never mistaken for sensor readings.

```bash
cd src
python build_history.py       # download a year of weather and model each zone (needs internet once)
python build_history.py --offline   # rebuild from the cached weather file
python visualize.py           # writes 7 PNGs + 2 CSV summaries into ../outputs/
python export_csv.py          # writes ../data/sensor_data.csv
```

| Chart | Time scale | Question it answers |
|---|---|---|
| `01_last_7_days_hourly.png` | Days | What happens hour by hour: heating, venting, the daily irrigation cycle |
| `02_daily_cycle_by_season.png` | Days | What an average day looks like in each season |
| `03_daily_temperature_year.png` | Days | Every day's low, mean and high against each crop's target band |
| `04_monthly_summary.png` | Months | Monthly temperatures and the share of hours outside target |
| `05_quarterly_summary.png` | Quarters | Which targets fail in which quarter, per zone |
| `06_year_calendar.png` | Year | Which days of the year had problems |
| `07_indoor_vs_outdoor.png` | Year | At what outdoor temperature the controls stop coping |

Open the CSVs in Google Sheets or Excel for Option B. The dashboard's
**Analytics → Long-term trends** section shows the same data interactively,
grouped by day, week, month, quarter or year.

Read `docs/visualization_interpretation.md` for the written analysis.

### Phase 6: optional dashboard

```bash
# from project root
streamlit run src/dashboard.py
```

The dashboard includes:

- Overview cards for temperature, humidity, soil moisture, and active alerts
- Environmental trend modes for temperature and humidity, soil moisture, nutrient level, and pH scale
- Interactive zoom, hover tooltips, target-range bands, and overall trend readings
- Primary Tomato, Lettuce, and Seedling zone health cards on Overview
- Full crop-zone directory with matching local images on Zones
- Analytics charts for zone comparison, overall averages, nutrient level, pH scale, light, and other stored metrics
- Long-term trends grouped by day, week, month, quarter or year, filterable by zone and data source, with a table view and CSV export
- Time ranges from the last 24 hours up to the last 12 months
- Freshness warnings when a source has not reported within two minutes
- Explicit Online, Demo data, Degraded, and Sensors offline system states
- Fresh-only chart filtering, alert markers, event-focused activity filters, and data-quality summaries
- monthly temperature summary table for September, October, November, and December
- a filtered month view for the current selected month
- a forecast month-ahead comparison showing current vs expected temperature
- a safe-band range overlay and note explaining expected operating conditions for the next month ahead

### Offline / recorded demo (no broker)

```bash
cd src
python offline_pipeline.py
```

This reseeds if needed, builds the modelled history from the cached weather file,
exports CSV, and rebuilds the charts.

---

## Data fields

| Field               | Type    | Meaning                           |
| ------------------- | ------- | --------------------------------- |
| `id`                | INTEGER | Auto-increment primary key        |
| `timestamp`         | REAL    | Unix time                         |
| `iso_time`          | TEXT    | UTC ISO-8601                      |
| `device_id`         | TEXT    | Sensor node id (`GH-SENSOR-01`)   |
| `temperature_c`     | REAL    | Air temperature °C                |
| `humidity_pct`      | REAL    | Relative humidity %               |
| `soil_moisture_pct` | REAL    | Soil moisture %                   |
| `light_lux`         | REAL    | Ambient light                     |
| `nutrient_level`    | REAL    | Simulated nutrient level %        |
| `ph_scale`          | REAL    | Soil solution pH                  |
| `alert_flag`        | INTEGER | 1 if any threshold is broken      |
| `alert_reason`      | TEXT    | `high_temperature`, `dry_soil`, … |

Safe bands used by the alert logic: temperature 16–32 °C, humidity 40–80 %, soil moisture ≥ 30 %.

Monthly temperature ranges used in the dashboard and forecast view:

| Month     | Target temperature range |
| --------- | -----------------------: |
| September |             18.0–30.0 °C |
| October   |             16.0–28.0 °C |
| November  |             13.0–24.0 °C |
| December  |             10.0–22.0 °C |

The dashboard uses these bands to compare actual monthly average temperature with the expected operating range for the next month ahead.

---

## Deliverable checklist

| Phase          | Due         | What to submit from this folder                                              |
| -------------- | ----------- | ---------------------------------------------------------------------------- |
| 1 Design       | 7 Sep 2026  | `docs/PHASE1_Project_Proposal.md` (or `.docx`) + `diagrams/architecture.png` |
| 2 Simulation   | 14 Sep 2026 | `src/simulator.py` + `samples/phase2_sample_output.txt`                      |
| 3 MQTT         | 21 Sep 2026 | `src/publisher.py`, `src/subscriber.py` + live screenshot                    |
| 4 Storage      | 28 Sep 2026 | `data/iot_data.db` + schema in `docs/table_schema.md`                        |
| 5 Viz          | 28 Sep 2026 | `outputs/*.png` + `docs/visualization_interpretation.md`                     |
| 6 Bonus        | 28 Sep 2026 | `src/dashboard.py`                                                           |
| 7 Presentation | 28 Sep 2026 | `presentation/GreenHouseWatch_Slides.pptx` + live/recorded demo              |

---

## Notes

### Real outdoor weather

Open **Forecast**, enter your city and two-letter country code, click **Find location**, and select the matching location. The page shows current outdoor weather and a five-day forecast in three-hour intervals, with local timestamps, Celsius temperatures, rain probability, and CSV export. It refreshes every ten minutes while open; **Refresh weather** requests a fresh result immediately.

Set `OPENWEATHER_API_KEY` in the environment, or put `api_key = "YOUR_KEY"` under `[openweather]` in `.streamlit/secrets.toml`. Restart Streamlit after configuring secrets. The secrets file is excluded from Git; do not commit or share it. The supplied key is configured locally. Weather service errors appear on the page without exposing credentials. Overview reads SQLite and displays each source's recorded provenance; outdoor weather does not measure indoor conditions or control irrigation.

- Use **Applicable tools**. This project does.
- If HiveMQ is blocked on campus Wi-Fi, use `offline_pipeline.py` for the recorded demo and still submit the publisher/subscriber source.
- Edit `src/config.py` to change the MQTT topic, device id, or alert limits.
- Creativity extras already included: multi-zone sensors, alert flags, day/night cycle, nutrient and pH telemetry, irrigation events, Streamlit dashboard, monthly forecast table, and month-ahead temperature range analysis.

---

All rights reserved.

---
Jerry Diabor | Department of Computer Science | Bowie State University | Bowie, MD

---
An Initiative for A Smarter Greenhouses Healthier Harvests 

---
