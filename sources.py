"""Fetch current weather from JMA AMeDAS and Open-Meteo."""

from datetime import datetime, timedelta, timezone

import requests

JST = timezone(timedelta(hours=9))
TIMEOUT_SECONDS = 10
HEADERS = {"User-Agent": "morioka-weather-collector/0.1"}

AMEDAS_BASE = "https://www.jma.go.jp/bosai/amedas/data"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Output field -> JMA field. "normalPressure" is sea-level pressure, which is
# comparable with Open-Meteo's pressure_msl ("pressure" is at station height).
AMEDAS_FIELDS = {
    "temperature_c": "temp",
    "humidity_pct": "humidity",
    "precip_10min_mm": "precipitation10m",
    "precip_1h_mm": "precipitation1h",
    "wind_speed_ms": "wind",
    "wind_direction": "windDirection",
    "sunshine_min": "sun10m",
    "pressure_hpa": "normalPressure",
    "snow_depth_cm": "snow",
}

# Output field -> Open-Meteo "current" variable.
OPEN_METEO_FIELDS = {
    "temperature_c": "temperature_2m",
    "humidity_pct": "relative_humidity_2m",
    "precipitation_mm": "precipitation",
    "rain_mm": "rain",
    "weather_code": "weather_code",
    "cloud_cover_pct": "cloud_cover",
    "pressure_hpa": "pressure_msl",
    "wind_speed_ms": "wind_speed_10m",
    "wind_direction_deg": "wind_direction_10m",
}


def _get(url, **kwargs):
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS, **kwargs)
    response.raise_for_status()
    return response


def fetch_amedas(station_code):
    """Return the latest observation for an AMeDAS station."""
    latest_text = _get(f"{AMEDAS_BASE}/latest_time.txt").text.strip()
    latest = datetime.fromisoformat(latest_text).astimezone(JST)

    block_hour = latest.hour // 3 * 3
    url = f"{AMEDAS_BASE}/point/{station_code}/{latest:%Y%m%d}_{block_hour:02d}.json"
    records = _get(url).json()

    # Keys are JST timestamps, so sorting them sorts by time. The station file
    # can lag behind latest_time.txt, so use its newest record.
    times = sorted(records, reverse=True)
    if not times:
        raise ValueError("station file has no records")
    newest = records[times[0]]

    result = {
        "observed_at": datetime.strptime(times[0], "%Y%m%d%H%M%S")
        .replace(tzinfo=JST)
        .isoformat()
    }
    flags = {}
    for name, jma_name in AMEDAS_FIELDS.items():
        # Each value is [value, quality_flag]; the field may be absent.
        value, flag = newest.get(jma_name) or (None, None)
        result[name] = value
        flags[name] = flag

    # JMA only reports snow depth on the hour. Every block starts on the hour,
    # so an hourly record is always available.
    for time_key in times:
        if "snow" in records[time_key]:
            result["snow_depth_cm"], flags["snow_depth_cm"] = records[time_key]["snow"]
            break

    result["quality_flags"] = flags
    return result


def fetch_open_meteo(latitude, longitude):
    """Return current conditions and precipitation for the next hour."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "Asia/Tokyo",
        "wind_speed_unit": "ms",
        "current": ",".join(OPEN_METEO_FIELDS.values()),
        "minutely_15": "precipitation",
        "forecast_minutely_15": 4,
    }
    data = _get(OPEN_METEO_URL, params=params).json()

    current = data["current"]
    result = {"time": current.get("time")}
    for name, api_name in OPEN_METEO_FIELDS.items():
        result[name] = current.get(api_name)
    result["precip_next_1h_15min_mm"] = data.get("minutely_15", {}).get("precipitation")
    return result
