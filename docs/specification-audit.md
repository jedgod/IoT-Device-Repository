GreenHouseWatch specification and objectives audit

Reviewed: 8 September 2026. Source: `Digital Repository Project 1 due 28 September 2026.pdf`, all seven pages. Scope: assignment compliance, application behavior, data integrity, proposal, charts, presentation, and demo evidence.

Verdict: The core application meets the required architecture and implements the required simulation, MQTT, SQLite, and visualization functions. The optional dashboard also works with the current dataset. The submission needs corrections before it should be called fully ready: invalid sensor values can break the dashboard, documentation and slides describe an older dataset, some interpretations misstate what the simulated data establishes, and the final presentation/demo still needs to be delivered. This is an evidence-based review, not an instructor grade.

Source interpretation:

- Page 1's title says 21 September 2026, but its Due Date field says 28 September 2026. Phases 4, 5, and 7 also explicitly say 28 September. Phase 3 is due 21 September. Confirm the title discrepancy against course instructions; do not assume an extension for earlier phases.
- Phase 1 is due 7 September; Phase 2 is due 14 September. Files on disk do not establish timely submission.
- Phase 3 accepts a screenshot OR output showing transmission. A screenshot is not mandatory.
- Phase 7 recommends 8-15 slides; it requires a live or recorded demo. A slide containing demo commands is not itself a delivered demo.
- Phase 6 and the AI/multiple-sensor/anomaly-detection extensions are optional. Missing AI is not a core compliance failure.
- The optional project-report bullet on page 7 is visibly struck through. A report is present, but should not be treated as a mandatory missing requirement.
- Example field names and example MQTT topics illustrate the task; the assignment does not require copying them exactly. The richer greenhouse schema and custom topic satisfy the intended design.

Requirement-by-requirement findings:

| Requirement | Evidence | Assessment |
| --- | --- | --- |
| Free tools: Python, HiveMQ, SQLite, Matplotlib or Sheets | requirements.txt; src/config.py; imports and earlier live broker run | Meets required stack; no paid service is needed to run the project. |
| Simulator -> broker -> subscriber -> database -> visualization | src/simulator.py, publisher.py, subscriber.py, db.py, visualize.py; diagrams/architecture.png | Meets. Live publisher imports the simulator's reading generator. |
| Phase 1: one-page proposal with problem, use case, data fields | docs/PHASE1_Project_Proposal.docx | Meets content and length. LibreOffice rendering confirmed exactly one page. Student identity still needs replacement. |
| Phase 1: architecture diagram | diagrams/architecture.png; proposal and slide 3 | Meets. Diagram was visually inspected. |
| Phase 2: Python simulation | src/simulator.py | Meets. Four simulated measurement channels, JSON, timestamps, configurable count/interval. Live soil behavior differs from the historical dry-down model; see below. |
| Phase 2: at least 10-20 sample records | samples/phase2_sample_output.txt | Meets: 20 parseable JSON records. Saved sample uses interval 0; an earlier run in this session separately completed 20 readings at two-second intervals. |
| Phase 3: publisher and subscriber using HiveMQ | src/publisher.py; src/subscriber.py | Meets on valid project-generated messages. Earlier live run sent and stored all 20 records. |
| Phase 3: transmission screenshot or output | samples/subscriber_run.log | Meets as output: broker connection, subscription, received payloads, and inserts for 20 messages. All 20 logged payloads match database rows. samples/phase3_mqtt_transmission.txt is only a labeled example and should not be the primary evidence. |
| Phase 4: SQLite file | data/iot_data.db | Meets: integrity_check returned ok. |
| Phase 4: schema and >=50 stored records | docs/table_schema.md; src/db.py; database inspection | Meets: 100 rows, with timestamp index, device ID, four measurements, and alert metadata. Schema documentation's count is stale. |
| Phase 5: >=2 visualizations | outputs/01_temperature_over_time.png through 04_alert_summary.png | Meets quantity: four readable PNGs inspected. Time labels and gaps can be clearer. |
| Phase 5: short written interpretation | docs/visualization_interpretation.md | Present, but needs corrections to dataset size, time coverage, and cold-event description. |
| Phase 6: simple dashboard or integrated script | src/dashboard.py; src/offline_pipeline.py | Meets optional functionality on valid data. Streamlit AppTest completed without exceptions and displayed 100 readings and seven alerts. |
| Phase 7: slides including problem, architecture, insights, demo | presentation/GreenHouseWatch_Slides.pptx | Ten slides meet recommended length and include all required topics. Slides were rendered and inspected. Counts, some claims, and student identity need corrections. |
| Phase 7: live or recorded demo | Earlier successful live session; slide 9 demo instructions; run-process.txt | Technically demonstrated in this session. No video was found in the repository; the classroom live demo or submitted recording cannot be certified as delivered. A recording is optional if a live demo is given. |
| Submission package | src/, data/, outputs/, presentation/, docs/, samples/ | Required artifact types exist. Final submission and deadlines cannot be verified from the local files. |

Verified current dataset:

- 100 records: 80 historical seed records plus 20 live MQTT records from the earlier assisted run.
- 93 normal records and seven alerts: three high_humidity, three dry_soil, one low_temperature.
- All stored alert flags/reasons match recomputation with the current threshold logic.
- Temperature range: 13.37-28.96 C. Humidity: 55.27-80.42%. Soil moisture: 20.12-73.36%. Light: 0-7863.2 lux.
- Time coverage: 2026-09-07 00:31:21 UTC to 2026-09-08 05:56:22 UTC, approximately 29 hours 25 minutes.
- The first 80 readings are 15 minutes apart; the last 20 are approximately two seconds apart. The intervening gap is approximately 9 hours 39 minutes.
- CSV has 100 rows, and every exported field matches the ordered database results.
- Every stored ISO timestamp agrees with its numeric timestamp to within one millisecond.

Findings to address, in priority order:

1. Validate incoming sensor values before storage. In src/subscriber.py:45-50, required-key checks do not validate numeric types, finite values, physical ranges, timestamp agreement, or supplied alert metadata. An isolated callback test stored temperature_c='not-a-number' and humidity_pct=150.0. An isolated dashboard test with that temperature as the latest reading raised ValueError at src/dashboard.py:40. This is a reproduced error path, not corruption found in the current database. SQLite's REAL declaration alone does not prevent that insertion. Reject malformed readings, calculate alerts from validated measurements, and ensure bad input cannot crash the dashboard.

2. Reconcile the submission with one identified dataset snapshot. docs/visualization_interpretation.md still reports 80 total / 73 normal; the current database, CSV, dashboard, and regenerated summary chart show 100 total / 93 normal. docs/Project_Report.md and docs/table_schema.md also describe 80 as the current total. Slides 6, 8, and 10 still report 80; slide 7 contains the earlier charts. It is acceptable to discuss the 80-row historical subset if it is explicitly identified and its charts are clearly labeled. Do not mix that subset with full-dataset totals. README references to the original 80 seed records remain historically true but should distinguish seed count from current total.

3. Correct interpretation and simulation claims. The cold alert is row 69 at 2026-09-07 17:31:21 UTC, not dawn as slide 8 states. Its 13.37 C reading is an injected anomaly in simulated data. The light pattern reflects the programmed model; it does not independently prove the clock is correct or that a real greenhouse behaves safely. The interpretation's claim that the repository is sufficient to operate a greenhouse is not established by this classroom simulation. Explain what the simulated scenario demonstrates, and use the actual event timestamps.

4. Distinguish live and historical sensor behavior. generate_series() provides progressive soil drying, irrigation, and scheduled anomalies. The live simulator and publisher call generate_reading() with its default soil_base=55 and no anomaly argument, so those historical events are not scheduled in the live run. Slides and proposal should make that distinction. The cold anomaly is scheduled by series index, not by time of day. Regenerating data also uses randomness and a moving start time; it will not guarantee the same seven alerts or extrema described in the current prose.

5. Improve time display. The dashboard computes labels but plots lists against sample index at src/dashboard.py:52-66. This makes 15-minute historical intervals and two-second live intervals appear equally spaced. Use actual timestamps on chart axes. The PNG charts correctly use timestamps, but format them only as HH:MM across multiple dates and draw continuous lines across the long gap. Include dates and visibly mark or break missing-data periods. These are interpretation improvements; the existing PNGs satisfy the minimum chart requirement.

6. Finalize presentation identity and demo evidence. Replace the IPMC BIT placeholder in the proposal footer, Markdown proposal, and slides with the correct student/team identity. Use samples/subscriber_run.log as real Phase 3 evidence. Give a live end-to-end presentation or make a recording of it. If using the offline fallback, disclose that it bypasses MQTT and show the genuine MQTT evidence separately. No instructor acceptance of an offline-only presentation is assumed.

7. Improve demo resilience after the above fixes. Publisher uses QoS 0 and does not check the return value/status after wait_for_publish; its printed counter should not be interpreted as subscriber delivery confirmation. Current transmission is independently verified by subscriber logs and SQLite. Initial broker connection exceptions are not handled with a friendly fallback, and fixed MQTT client IDs can conflict with another instance. Connection closure in dashboard/visualization reads should be explicit. The installed Streamlit version also emits a use_container_width deprecation warning; this did not fail the valid-data dashboard test. These are reliability improvements beyond the assignment's minimal examples.

Learning objectives and evidence:

| PDF learning objective | Evidence and remaining work |
| --- | --- |
| Understand IoT architecture | Proposal, architecture image, slide 3, and working five-stage implementation provide evidence. The student's own explanation must be demonstrated during presentation. |
| Simulate real-world sensor data | Four measurements and modeled day/night behavior are implemented. Clearly identify simulated data and historical-only events. |
| Implement MQTT communication | Twenty messages traveled through HiveMQ and were matched to stored rows. |
| Store and manage time-series data | SQLite, time index, schema, CSV export, and 100 consistent records are verified. Strengthen incoming-value validation. |
| Build visualizations for insight | Four PNGs and dashboard exist. Correct stale interpretations and show time gaps accurately. |
| Present an end-to-end system | Ten-slide deck and a successful development demo exist. Correct slides and deliver the required presentation/demo. |

Measurable completion objectives:

1. Data safety: reject nonnumeric, nonfinite, missing, and physically invalid sensor values without inserting a row; a bad message must not break subsequent valid ingestion or dashboard rendering.
2. Consistent evidence: select a dated data snapshot and make database/CSV totals, charts, written interpretation, and slides agree exactly, including the alert denominator and event timestamps.
3. Accurate time-series display: use real date/time axes in the dashboard and PNGs and identify the historical/live sampling change and missing-data gap.
4. Submission identity: remove all student-name placeholders and confirm the correct course deadlines without inferring submission from local file creation.
5. Demonstrable pipeline: show a valid reading being published, received, inserted, and displayed; demonstrate a growing row count; retain real output or a recording. Use the existing 20-message evidence as the verified baseline.
6. Final presentation: retain the ten-slide structure, update counts/claims/images, explain historical simulation versus live MQTT, and deliver the live or recorded demo required by Phase 7.

Validation performed:

- Read all assignment pages and inspected their rendered layout, including the inconsistent date and struck-through optional report line.
- Extracted all ten slide texts; rendered the deck and proposal using LibreOffice; inspected the one-page proposal, deck, architecture image, and four current charts.
- Parsed all 12 source Python files successfully.
- Checked SQLite integrity, row counts, all current alert values, numeric/ISO timestamp agreement, CSV equality, and all 20 live log payloads against stored data.
- Passed 11 threshold boundary cases, historical series length/time spacing, and generated-alert consistency.
- Tested valid and malformed subscriber payloads using an in-memory database. Reproduced invalid numeric storage there, and reproduced the resulting dashboard exception using mocked rows.
- Ran the offline pipeline on isolated scratch paths, verified generation of at least 50 records, CSV and four charts, then reran it and verified preserved row count.
- Ran the current dashboard through Streamlit AppTest successfully on the valid repository dataset.
- Reused the earlier successful 20-message HiveMQ run rather than adding more live records solely for this audit.

Application source, submission documents, slides, and the real dataset were not rewritten to resolve these findings during this review. Scratch checks and renderings are under tmp/. The audit establishes local technical behavior and artifact readiness; it cannot certify an instructor grade, timely submission, or the student's completed presentation.
