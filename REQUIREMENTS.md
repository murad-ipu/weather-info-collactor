# Project: Morioka Weather Collector (Phase 1)

## Instructions for Claude Code

Build a **small, simple** Python application from this spec. Keep it minimal: no database, no ML, no exports, no web server. Those come in later phases.

Before writing code, make one real request to each endpoint in §3 and check the actual response format (field names, units, timestamps). If something differs from this spec, tell me and adjust.

---

## 1. Goal

A background job that, every **10 minutes** (configurable), fetches current weather for **Morioka City, Japan** from two sources, **JMA AMeDAS** and **Open-Meteo**, combines them into **one JSON object**, and **prints it to the terminal** so I can check the data.

## 2. Configuration

A single `config.yaml`:

```yaml
interval_minutes: 10        # how often to fetch

location:
  name: Morioka
  amedas_code: "33431"      # JMA AMeDAS station for Morioka
  latitude: 39.6986         # verify against JMA station table
  longitude: 141.1650
```

- If the file is missing, use these defaults.
- `interval_minutes` can also be overridden from the command line: `python main.py --interval 5`.

## 3. Data sources

### 3.1 JMA AMeDAS (station 33431, Morioka)

- Latest observation time: `https://www.jma.go.jp/bosai/amedas/data/latest_time.txt`
- Station data (3-hour blocks): `https://www.jma.go.jp/bosai/amedas/data/point/33431/{YYYYMMDD}_{HH}.json`
  - `HH` is the 3-hour block start (00, 03, 06, …, 21) in JST that contains the latest time.
- Values come as `[value, quality_flag]`. Take the value and keep the flag.
- Fields to extract (if present): temperature, humidity, precipitation (10 min and 1 hour), wind speed, wind direction, sunshine, pressure, snow depth.

### 3.2 Open-Meteo

- `https://api.open-meteo.com/v1/forecast` with `latitude`, `longitude`, `timezone=Asia/Tokyo`
- Request `current` values: temperature_2m, relative_humidity_2m, precipitation, rain, weather_code, cloud_cover, pressure_msl, wind_speed_10m, wind_direction_10m.
- Request `minutely_15` precipitation for the next 1 hour (`forecast_minutely_15=4`).
- Free, no API key needed.

## 4. Output

Each run prints one combined JSON object (pretty-printed) to the terminal, for example:

```json
{
  "fetched_at": "2026-11-05T12:30:05+09:00",
  "location": "Morioka",
  "amedas": {
    "observed_at": "2026-11-05T12:20:00+09:00",
    "temperature_c": 12.4,
    "humidity_pct": 68,
    "precip_10min_mm": 0.0,
    "precip_1h_mm": 0.0,
    "wind_speed_ms": 2.1,
    "wind_direction": 8,
    "sunshine_min": 10,
    "pressure_hpa": 1015.2,
    "snow_depth_cm": null
  },
  "open_meteo": {
    "time": "2026-11-05T12:30",
    "temperature_c": 12.1,
    "humidity_pct": 70,
    "precipitation_mm": 0.0,
    "rain_mm": 0.0,
    "weather_code": 3,
    "cloud_cover_pct": 90,
    "pressure_hpa": 1014.8,
    "wind_speed_ms": 2.5,
    "wind_direction_deg": 140,
    "precip_next_1h_15min_mm": [0.0, 0.0, 0.1, 0.2]
  },
  "errors": []
}
```

- Use units in field names; ask Open-Meteo for wind in m/s (`wind_speed_unit=ms`).
- Missing values are `null`.
- Also append each JSON object as one line to `data/weather.jsonl`, so the output is kept for the next phase.

## 5. Behaviour

- Fetch once immediately on start, then every `interval_minutes`.
- If one source fails, still print the other and add a short message to `errors`. Never crash the loop.
- Use a 10-second timeout per request and a simple User-Agent (no personal info).
- Stop cleanly with Ctrl+C.

## 6. Tech

- Python 3.11+
- Libraries: `requests` (or `httpx`) and `PyYAML` only. A simple `while True` + `time.sleep` loop is fine; no scheduler library needed.
- Files:
  ```
  main.py            # loop + printing
  sources.py         # fetch_amedas(), fetch_open_meteo()
  config.yaml
  requirements.txt
  README.md          # how to install and run
  ```

## 7. Done when

- `python main.py` prints a combined JSON object right away and then every `interval_minutes`.
- `python main.py --interval 1` changes the interval without editing code.
- Turning off the network briefly shows errors in the output, and the job keeps running and recovers.
