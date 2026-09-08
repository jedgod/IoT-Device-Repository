# Phase 5 — What the data shows

Four charts were generated from the 80-row SQLite repository (`outputs/`). Together they describe roughly 20 hours of greenhouse activity at 15-minute steps.

## 1. Temperature over time

Temperature moves with the day: it sits in the high teens around midnight, climbs through the morning, and peaks near **29 °C** in the early afternoon. That peak stays inside the 16–32 °C safe band, so the greenhouse did **not** overheat in this series. One night-side dip reaches **13.4 °C**, which is below the 16 °C floor and is flagged as `low_temperature`. Practically, that is the kind of reading that would justify a cheap heating mat or closing vents before dawn.

## 2. Humidity over time

Humidity is the mirror image of temperature: it is highest at night (~78–80 %) and lowest when the house is warmest (~55 %). Three readings drift just above the 80 % ceiling (`high_humidity`). Persistent saturation at night is a common greenhouse problem — it raises fungal risk even when the daytime climate looks fine. The chart therefore supports a simple operational rule: ventilate or run a dehumidifier when overnight humidity hugs 80 %.

## 3. Soil moisture and light

Light traces a clean day/night curve (near 0 lux at night, ~7,500 lux at midday), which confirms the time axis is behaving like a real clock rather than random noise.

Soil moisture slowly declines as the crop “uses” water, then three consecutive mid-day readings fall to **~20 %** (`dry_soil`) — well under the 30 % limit. Shortly after that cluster the series shows an irrigation recovery (moisture jumps back into the 60–70 % range). The story is: the house went through a short drought event at the hottest, brightest part of the day, then water was restored. That is exactly the pattern a farmer would want an IoT repository to catch.

## 4. Alert summary

Of 80 stored records, **7 are alerts** and 73 are normal. The alert mix is:

- 3 × `dry_soil`
- 3 × `high_humidity`
- 1 × `low_temperature`

The scatter of temperature vs humidity shows the expected inverse relationship (warmer air, drier air). Alert points sit on the edges of that cloud, not in the middle — the thresholds are doing useful work rather than firing at random.

## Bottom line

The repository is healthy enough to run a greenhouse by: the climate is mostly inside the safe band, the dangerous moments are brief and explainable (dry soil at noon, damp air at night, one cold snap), and they line up with light and time of day. That is the insight an IoT digital repository is supposed to produce — not just a pile of numbers, but a reason to irrigate, vent, or heat at a specific hour.
