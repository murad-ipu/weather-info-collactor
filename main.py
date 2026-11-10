"""Fetch Morioka weather on a fixed interval, print it, and append it to a file."""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml

from sources import HEADERS, JST, TIMEOUT_SECONDS, fetch_amedas, fetch_open_meteo

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
OUTPUT_PATH = BASE_DIR / "data" / "weather.jsonl"
SEND_LOG_PATH = BASE_DIR / "data" / "send_failures.log"

DEFAULT_CONFIG = {
    "interval_minutes": 10,
    "ai_endpoint_url": "",
    "location": {
        "name": "Morioka",
        "amedas_code": "33431",
        "latitude": 39.6983,
        "longitude": 141.1650,
    },
}


def load_config(path=CONFIG_PATH):
    """Read the config file; anything missing falls back to the defaults."""
    file_config = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            file_config = yaml.safe_load(f) or {}
    return {
        "interval_minutes": file_config.get(
            "interval_minutes", DEFAULT_CONFIG["interval_minutes"]
        ),
        "ai_endpoint_url": file_config.get(
            "ai_endpoint_url", DEFAULT_CONFIG["ai_endpoint_url"]
        ),
        "location": {**DEFAULT_CONFIG["location"], **(file_config.get("location") or {})},
    }


def describe_error(source, error):
    """Turn an exception into one short line for the "errors" list."""
    if isinstance(error, requests.Timeout):  # Check first: some are also ConnectionError.
        detail = "request timed out"
    elif isinstance(error, requests.ConnectionError):
        detail = "connection failed"
    elif isinstance(error, requests.HTTPError):
        detail = f"HTTP {error.response.status_code}"
    else:
        detail = f"{type(error).__name__}: {error}"
    return f"{source}: {detail}"


def collect(config):
    """Fetch both sources. A failed source becomes null plus an error message."""
    location = config["location"]
    fetchers = {
        "amedas": lambda: fetch_amedas(location["amedas_code"]),
        "open_meteo": lambda: fetch_open_meteo(location["latitude"], location["longitude"]),
    }

    record = {
        "fetched_at": datetime.now(JST).isoformat(timespec="seconds"),
        "location": location["name"],
    }
    errors = []
    for source, fetch in fetchers.items():
        try:
            record[source] = fetch()
        except Exception as error:  # A bad response must never stop the loop.
            record[source] = None
            errors.append(describe_error(source, error))
    record["errors"] = errors
    return record


def append_line(path, line):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def save(record, path=OUTPUT_PATH):
    append_line(path, json.dumps(record, ensure_ascii=False))


def log_send_failure(record, reason, path=SEND_LOG_PATH):
    """Report a failed send on the terminal and in the send log."""
    line = f"{record['fetched_at']} data could not be sent: {reason}"
    print(line, file=sys.stderr, flush=True)
    try:
        append_line(path, line)
    except OSError as error:
        print(f"Could not write {path}: {error}", file=sys.stderr, flush=True)


def send_to_ai(record, url):
    """POST the record once. A failure is logged and never retried."""
    try:
        response = requests.post(url, json=record, headers=HEADERS, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except Exception as error:  # A failed send must never stop the loop.
        log_send_failure(record, describe_error("ai_endpoint", error))


def run_once(config):
    record = collect(config)
    print(json.dumps(record, indent=2, ensure_ascii=False), flush=True)
    try:
        save(record)
    except OSError as error:
        print(f"Could not write {OUTPUT_PATH}: {error}", file=sys.stderr, flush=True)
    if config["ai_endpoint_url"]:
        send_to_ai(record, config["ai_endpoint_url"])


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--interval",
        type=float,
        metavar="MINUTES",
        help="minutes between fetches (overrides config.yaml)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        config = load_config()
    except (OSError, yaml.YAMLError) as error:
        sys.exit(f"Could not read {CONFIG_PATH}: {error}")

    interval = args.interval if args.interval is not None else config["interval_minutes"]
    if not isinstance(interval, (int, float)) or interval <= 0:
        sys.exit(f"Interval must be a number above 0, got: {interval!r}")
    interval_seconds = interval * 60

    print(f"Fetching every {interval:g} minute(s). Press Ctrl+C to stop.", file=sys.stderr, flush=True)
    if not config["ai_endpoint_url"]:
        print("ai_endpoint_url is not set, so data will not be sent.", file=sys.stderr, flush=True)
    try:
        next_run = time.monotonic()
        while True:
            run_once(config)
            # Schedule from the previous start so request time doesn't add drift.
            next_run += interval_seconds
            now = time.monotonic()
            if next_run < now:  # Fell behind (e.g. the PC slept): skip the missed runs.
                next_run = now + interval_seconds
            time.sleep(next_run - now)
    except KeyboardInterrupt:
        print("Stopped.", file=sys.stderr)


if __name__ == "__main__":
    main()
