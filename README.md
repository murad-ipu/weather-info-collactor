# Morioka Weather Collector (Phase 1)

Every 10 minutes, this fetches the current weather for Morioka, Japan from JMA AMeDAS and Open-Meteo. It combines both into one JSON object, prints it to the terminal, and appends it to `data/weather.jsonl`.

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

## Output notes

If a source fails, its section is `null` and a short message is added to `errors`. The job keeps running and tries again at the next interval.

### `amedas`

| Field | Meaning |
| --- | --- |
| `observed_at` | Time of the JMA record used |
| `pressure_hpa` | Sea-level pressure (JMA `normalPressure`), comparable with Open-Meteo's value |
| `wind_direction` | 16-point compass code: 1 = NNE, 4 = E, 8 = S, 12 = W, 16 = N, 0 = calm |
| `sunshine_min` | Minutes of sunshine in the last 10 minutes (0 to 10) |
| `snow_depth_cm` | Newest hourly value, because JMA only reports snow depth on the hour. It can be up to 50 minutes older than `observed_at` |
| `quality_flags` | JMA's quality flag for each field; `0` is normal, and `null` means the field was absent |

### `open_meteo`

| Field | Meaning |
| --- | --- |
| `time` | Start of the 15-minute period the values belong to, so it can repeat between fetches |
| `precip_next_1h_15min_mm` | Four 15-minute values. The first is the current period, so they don't start strictly in the future |
