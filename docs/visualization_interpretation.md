# Phase 5: What the data shows

## Where the data comes from

The charts in `outputs/` cover **1 October 2025 to 26 September 2026** (361 whole days, local Bowie, MD time).

- **Outdoor weather is real.** Hourly temperature, humidity and solar radiation for Bowie, MD come from the Open-Meteo historical archive (`src/build_history.py`, cached in `data/weather_history_bowie.json`).
- **Indoor conditions are modelled** from that weather, hour by hour, for the Tomato, Lettuce and Seedling zones. The model applies the controls a typical greenhouse has: solar gain, a heater held just above each crop's minimum, a 40% shade cloth on hot days, vents with evaporative pad cooling, fogging for dry air, morning irrigation with an afternoon top-up, and a weekly nutrient change. These rows are stored with `source = 'weather model'`, so they are never confused with sensor readings.
- Each zone is judged against its own crop targets (Tomatoes 20–28 °C, Lettuce 15–22 °C, Seedlings 18–24 °C, plus humidity and soil-moisture limits). "Outside target" means at least one of temperature, humidity or soil moisture is out of range in that hour.

The monthly and quarterly numbers behind the charts are in `outputs/monthly_summary.csv` and `outputs/quarterly_summary.csv`.

## Days

**Chart 01 (last 7 days, hourly).** Each day has the same shape: the air warms after sunrise, and the vents open once a zone reaches its cooling setpoint. Soil moisture falls steadily through the day and jumps back at 06:00 when irrigation runs. When outdoor air drops to about 11 °C at night, the zones stay at 15–21 °C because the heaters hold them there.

**Chart 02 (average day by season).** In winter the indoor lines are almost flat. The outdoor mean runs from −2 °C to 4 °C, but heating holds each zone just above its minimum all day. In summer the picture reverses: outdoor air peaks near 29 °C in mid-afternoon, and every zone rises with it. Afternoons are the problem period. Between 15:00 and 16:00, Lettuce is outside its temperature target in 48% of hours and Seedlings in 45%, compared with 14% and 3% at 03:00.

**Chart 03 (every day of the year).** From November to March every zone's daily mean sits on the lower edge of its grey target band. That shows heating doing its job, even through the coldest hour of the year (−17.7 °C outdoors at 06:00 on 30 January 2026). From June to September the daily highs break above the band. On the hottest day (37.4 °C outdoors on 4 July 2026), all three zones peak above 29 °C (Tomatoes 30.5 °C).

## Months

**Chart 04 (monthly summary).** Monthly mean outdoor temperature ranges from −1 °C (January) to 25 °C (July). Indoors, Tomatoes stay between 21 °C and 26 °C in every month. Hours outside target follow two separate seasonal causes:

| Month | Tomatoes | Lettuce | Seedlings | Main cause |
|---|---|---|---|---|
| January 2026 | 23% | 16% | 51% | Heated winter air is too dry (humidity below target) |
| July 2026 | 42% | 82% | 65% | Heat; pad cooling cannot pull humid summer air low enough |
| August 2026 | 38% | 85% | 60% | Heat and high humidity |
| November 2025 | 1% | 2% | 13% | Mild weather; the easiest month |

## Quarters

**Chart 05 (quarterly summary).** Share of hours outside target:

| Quarter | Tomatoes | Lettuce | Seedlings |
|---|---|---|---|
| Q4 2025 (Oct–Dec) | 4% | 6% | 18% |
| Q1 2026 (Jan–Mar) | 13% | 12% | 32% |
| Q2 2026 (Apr–Jun) | 17% | 38% | 28% |
| Q3 2026 (Jul–Sep 26) | 35% | 76% | 56% |

Soil moisture was within target in effectively every hour (four dry hours in the whole year, all in the Seedling zone after missed irrigation cycles). So irrigation is not the constraint; air temperature and humidity are.

## Year

**Chart 06 (calendar).** Out of 361 days, Tomatoes had 136 days fully within target in every hour, Lettuce 103 and Seedlings 76. The dark blocks sit in two places: late January to February (dry air, mostly Seedlings) and June to early September (heat, mostly Lettuce).

**Chart 07 (indoor vs outdoor).** Each dot is one day. When the outdoor daily mean is below about 15 °C, indoor temperature is flat, so the heating fully decouples the house from the weather. Above an outdoor daily mean of about 20 °C, indoor temperature starts to track outdoor, because venting can only cool towards outside air and pad cooling is limited by humidity. Lettuce's band (15–22 °C) sits below typical Bowie summer days, so its dots leave the band first.

## What this means for the greenhouse

1. **Lettuce is a cool-season crop here.** It is within target 94% of hours in Q4 but only 24% in Q3. Growing it from October to April and replacing it with a heat-tolerant crop over summer would remove most of its alert hours.
2. **Seedlings need more humidity in winter.** A third of Q1 hours are too dry because heating dries the air. Added fogging capacity, or propagation covers, is the cheapest fix.
3. **Tomatoes suit this house best.** They are outside target 17% of the year, and mostly on summer afternoons. Stronger shading or cooling in July and August would help most.
4. **Heating is adequate except in the deepest cold.** At −17.7 °C outdoors (06:00, 30 January 2026), Seedlings dipped to 17.7 °C, 0.3 °C under their 18 °C minimum, and Tomatoes fell to 17.7 °C, 2.3 °C under their 20 °C minimum. That cold snap is where the heater ran out of capacity. A backup heater, or a thermal screen for the coldest nights, would close that gap.

## Limits of this analysis

The indoor values are a model, not measurements: they show how a typical greenhouse with these controls would respond to the weather Bowie actually had. Live readings from the MQTT pipeline (`source = 'simulator'`, or a physical sensor) are stored alongside and can be compared in the dashboard's **Analytics → Long-term trends** section, filtered by source.
