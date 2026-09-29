# Live dashboard connection

The dashboard reads `data/iot_data.db` every five seconds. Overview, Zones,
Analytics, and Data use the same repository. The sidebar system clock updates
every second in the server's local time zone. It describes dashboard availability;
sensor freshness is reported separately. Measurements older than two minutes
are labelled stale. Empty time windows stay empty rather than showing fabricated
readings. Select **All stored data** to inspect historical measurements.

OpenWeatherMap remains the configured external API. Open Forecast, enter a city
and country code, and choose the matching location. Outdoor temperature, humidity,
wind, and five-day forecasts come from the API; outdoor weather is not an indoor
sensor measurement. The API key stays in ignored `.streamlit/secrets.toml`.

## Start from the repository root (PowerShell)

Dashboard terminal:

```powershell
.venv\Scripts\python.exe -m streamlit run src/dashboard.py
```

Subscriber terminal:

```powershell
.venv\Scripts\python.exe -u src/subscriber.py
```

Restart an existing Streamlit server and subscriber once after installing these
changes so their imported modules are reloaded. Refresh the browser afterward.

Connect physical sensors to the broker/topic in `src/config.py`, or use this
explicitly simulated publisher for an integration demonstration:

```powershell
.venv\Scripts\python.exe src/publisher.py --zone tomato-zone --interval 2
```

The simulator is labelled `simulator` in SQLite. This command does not produce
physical sensor observations. Stop either long-running process with Ctrl+C.

## MQTT payload contract

Required keys: `timestamp` (Unix seconds), `iso_time` (ISO 8601), `device_id`,
`temperature_c`, `humidity_pct`, `soil_moisture_pct`, and `light_lux`.
For zone telemetry include `zone_id`, such as `tomato-zone`. Nutrient-aware zone
publishers may also provide `nutrient_level` (percentage) and `ph_scale` (soil
solution pH); both fields are optional for backward compatibility and are stored
when present. Use a stable unique
`message_id` and increasing `sequence_number`; optional `sensor_id` identifies
the probe. The subscriber supplies receipt time and fallback identifiers when
omitted. Unknown zone IDs must be configured with thresholds before use.
Provide `source` to declare provenance (for example `physical sensor` or
`simulator`). This is a publisher declaration, not hardware attestation.

Legacy payloads appear as their own device, rather than being assigned to a crop
without evidence. Zoned payloads go to `zone_telemetry`, preserving zone metadata.
Redelivery of a zone message ID replaces that message rather than double-counting
it. Latest values are selected by measurement time, including out-of-order arrivals.

Existing records are preserved. Missing provenance is displayed as `unverified`;
known seed records are displayed as `seeded sample`. An additive `source` column
is initialized by `db.init_db`. The pre-migration database backup is
`data/iot_data.before_live_20260918.db`.

The dashboard loads up to 50,000 latest records per telemetry table. Large charts
are sampled; exports retain the loaded, filtered records. `GREENHOUSE_DB_PATH`
can select a separate database for testing. The tests use isolated databases.

Controls save requests with status `pending_controller`. There is no actuator
adapter or confirmed water/valve telemetry; the app never reports a request as
executed. A controller integration is needed before operating physical irrigation.
