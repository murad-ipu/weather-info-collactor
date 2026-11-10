# Morioka Weather Collector (Phase 1)

Every 10 minutes by default, this fetches the current weather for Morioka, Japan from JMA AMeDAS and Open-Meteo. It combines both into one JSON object, prints it to the terminal, appends it to `data/weather.jsonl`, and can send it to an AI application.

## Install

Requires Python 3.11 or newer.

```
pip install -r requirements.txt
```

## Run

```
python main.py              # use the interval from config.yaml
python main.py --interval 5 # fetch every 5 minutes instead
```

It fetches once right away, then repeats on the interval. Press Ctrl+C to stop.

## Configure

Settings are in `config.yaml`. If the file or a setting is missing, the built-in defaults are used.

## Send data to an AI application

Set `ai_endpoint_url` in `config.yaml`, for example `http://localhost:8000/weather`. After each fetch, the record is sent there once as an HTTP POST with a `Content-Type: application/json` body, using the format described below. Leave the setting empty to turn sending off.

Each attempt has a 10-second timeout and any 2xx response counts as success. A failed send is not retried. It is printed to the terminal and added to `data/send_failures.log`, and the record is still kept in `data/weather.jsonl`.

## Output format

Each fetch produces one JSON object. This is a real record:

```json
{
  "fetched_at": "2026-11-10T12:54:56+09:00",
  "location": "Morioka",
  "amedas": {
    "observed_at": "2026-11-10T12:40:00+09:00",
    "temperature_c": 5.5,
    "humidity_pct": 49,
    "precip_10min_mm": 0.0,
    "precip_1h_mm": 0.0,
    "wind_speed_ms": 2.8,
    "wind_direction": 1,
    "sunshine_min": 4,
    "pressure_hpa": 1021.5,
    "snow_depth_cm": null,
    "quality_flags": {
      "temperature_c": 0,
      "humidity_pct": 0,
      "precip_10min_mm": 0,
      "precip_1h_mm": 0,
      "wind_speed_ms": 0,
      "wind_direction": 0,
      "sunshine_min": 0,
      "pressure_hpa": 0,
      "snow_depth_cm": 5
    }
  },
  "open_meteo": {
    "time": "2026-11-10T12:45",
    "temperature_c": 7.2,
    "humidity_pct": 45,
    "precipitation_mm": 0.0,
    "rain_mm": 0.0,
    "weather_code": 0,
    "cloud_cover_pct": 19,
    "pressure_hpa": 1020.2,
    "wind_speed_ms": 1.92,
    "wind_direction_deg": 309,
    "precip_next_1h_15min_mm": [0.0, 0.0, 0.0, 0.0]
  },
  "errors": []
}
```

All times are Japan Standard Time (UTC+9). Any measurement can be `null` when no value is available.

### Top-level fields

| Field | Type | Description |
| --- | --- | --- |
| `fetched_at` | string (ISO 8601 with offset) | When the collector started this fetch. |
| `location` | string | Location name from `config.yaml`. |
| `amedas` | object or `null` | Measurements from the JMA AMeDAS station. `null` if this source failed. |
| `open_meteo` | object or `null` | Weather model values from Open-Meteo. `null` if this source failed. |
| `errors` | array of strings | One message per failed source, such as `"amedas: connection failed"` or `"open_meteo: HTTP 503"`. Empty when both sources worked. The text is for people to read and may change, so check whether `amedas` or `open_meteo` is `null` instead of parsing it. |

### `amedas`: station measurements

These are measured at JMA station 33431 in Morioka (39.6983 N, 141.1650 E, 155 m above sea level).

| Field | Type | Unit | Description |
| --- | --- | --- | --- |
| `observed_at` | string (ISO 8601 with offset) | | Time of the observation. JMA publishes every 10 minutes, usually 10 to 20 minutes late. |
| `temperature_c` | number or `null` | °C | Air temperature. |
| `humidity_pct` | number or `null` | % | Relative humidity. |
| `precip_10min_mm` | number or `null` | mm | Precipitation in the 10 minutes ending at `observed_at`. |
| `precip_1h_mm` | number or `null` | mm | Precipitation in the 60 minutes ending at `observed_at`. |
| `wind_speed_ms` | number or `null` | m/s | Wind speed. |
| `wind_direction` | integer or `null` | 16-point code | Direction the wind blows from, as a compass code: 1 = NNE, 2 = NE, 3 = ENE, 4 = E, 5 = ESE, 6 = SE, 7 = SSE, 8 = S, 9 = SSW, 10 = SW, 11 = WSW, 12 = W, 13 = WNW, 14 = NW, 15 = NNW, 16 = N, 0 = calm. Multiply by 22.5 for degrees. This is not in degrees, unlike `open_meteo.wind_direction_deg`. |
| `sunshine_min` | number or `null` | minutes | Minutes of sunshine in the 10 minutes ending at `observed_at` (0 to 10). |
| `pressure_hpa` | number or `null` | hPa | Sea-level pressure (JMA `normalPressure`). Comparable with `open_meteo.pressure_hpa`. |
| `snow_depth_cm` | number or `null` | cm | Snow depth on the ground. JMA only reports it on the hour, so this is the newest hourly value and can be up to 50 minutes older than `observed_at`. |
| `quality_flags` | object | | JMA's quality flag for each of the 9 measurements above, under the same field names. |

Flag values, based on what JMA's live data contains:

| Flag | Meaning |
| --- | --- |
| `0` | Normal. |
| `1`, `4` | A value is present but not flagged as normal, so use it with care. |
| `5`, `6` | No valid observation; the value is `null`. |
| `null` | JMA did not include this field in the record, so the value is also `null`. |

### `open_meteo`: weather model values

These are model estimates, not measurements, for the model grid point nearest Morioka (39.7 N, 141.1875 E, about 134 m above sea level).

| Field | Type | Unit | Description |
| --- | --- | --- | --- |
| `time` | string (ISO 8601, no offset, JST) | | The 15-minute step the values are valid for: the latest quarter-hour at or before the fetch. It repeats until the next step. |
| `temperature_c` | number or `null` | °C | Air temperature at 2 m, at `time`. |
| `humidity_pct` | number or `null` | % | Relative humidity at 2 m, at `time`. |
| `precipitation_mm` | number or `null` | mm | Total precipitation (rain, showers and snow) in the 15 minutes ending at `time`. |
| `rain_mm` | number or `null` | mm | Rain in the 15 minutes ending at `time`. |
| `weather_code` | integer or `null` | WMO code | Weather condition; see the table below. |
| `cloud_cover_pct` | number or `null` | % | Total cloud cover. |
| `pressure_hpa` | number or `null` | hPa | Sea-level pressure. |
| `wind_speed_ms` | number or `null` | m/s | Wind speed at 10 m. |
| `wind_direction_deg` | number or `null` | degrees | Direction the wind blows from at 10 m (0 to 360). |
| `precip_next_1h_15min_mm` | array of 4 numbers, or `null` | mm | Precipitation for the four 15-minute steps starting at `time`. Each value is the total for the 15 minutes ending at that step, so together they cover from 15 minutes before `time` to 45 minutes after it. |

Weather codes:

| Code | Condition |
| --- | --- |
| 0 | Clear sky |
| 1, 2, 3 | Mainly clear, partly cloudy, overcast |
| 45, 48 | Fog, depositing rime fog |
| 51, 53, 55 | Drizzle: light, moderate, dense |
| 56, 57 | Freezing drizzle: light, dense |
| 61, 63, 65 | Rain: slight, moderate, heavy |
| 66, 67 | Freezing rain: light, heavy |
| 71, 73, 75 | Snowfall: slight, moderate, heavy |
| 77 | Snow grains |
| 80, 81, 82 | Rain showers: slight, moderate, violent |
| 85, 86 | Snow showers: slight, heavy |
| 95, 97 | Thunderstorm, heavy thunderstorm |
| 96, 99 | Thunderstorm with slight hail, with heavy hail |

### Using the data

- **Repeated values:** JMA updates every 10 minutes and Open-Meteo every 15. If the collector runs more often, records repeat the same data. Use `amedas.observed_at` and `open_meteo.time` to detect new values.
- **Comparing sources:** the two sources are for different times and places. Compare `observed_at` with `time` before treating them as the same moment.
- **15-minute forecasts:** Open-Meteo interpolates 15-minute data from hourly data for Japan, so `precip_next_1h_15min_mm` won't show changes shorter than an hour.
- **Gaps:** records aren't resent, so an outage on either side leaves gaps in what the AI application receives.
