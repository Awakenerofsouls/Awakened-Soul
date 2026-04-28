"""
Heartbeat activity: weather_today

Pull current weather conditions via NOAA API for the agent's location.
Defaults to Pagosa Springs, CO (37.2678, -107.3897) unless state specifies LAT/LON.

No key required for basic NOAA API (api.weather.gov). API key from keys.json
is used for premium endpoints if available.

Activity contract:
  Input:  state dict (WORKSPACE, LAT, LON, etc.)
  Output: {"ok": bool, "status": "complete",
           "content": str, "category": str, "proactive": bool, "detail": str}
"""

import json
import urllib.request
import urllib.error
import random
from pathlib import Path
from datetime import datetime, timezone

from .keys import get_api_key
from .journal import write_to_journal
from .log import log_activity
SIGNAL_AFFINITY = {}


CATEGORY = "weather_today"

# Default: Pagosa Springs, CO
DEFAULT_LAT = "37.2678"
DEFAULT_LON = "-107.3897"


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    lat = state.get("WEATHER_LAT", DEFAULT_LAT)
    lon = state.get("WEATHER_LON", DEFAULT_LON)

    print(f"[heartbeat] weather_today: lat={lat}, lon={lon}")

    try:
        current = _get_current_conditions(lat, lon)
    except Exception as e:
        log_activity("weather_today", f"NOAA API failed: {e}", salience=0.3, tags="error,weather")
        return _skip(f"noaa api error: {e}")

    if not current:
        return _skip("no current conditions returned")

    content = _format_current(current, lat, lon)

    write_to_journal(category="weather_today", content=content,
                    workspace=workspace, state=state)

    return {
        "ok": True,
        "status": "complete",
        "content": content,
        "category": CATEGORY,
        "proactive": random.random() < 0.15,
        "detail": f"{current.get('properties', {}).get('temperature', '?')}°F at {lat},{lon}",
    }


def _get_current_conditions(lat: str, lon: str) -> dict:
    """Two-step: points → grid data → current observations."""
    points_url = f"https://api.weather.gov/points/{lat},{lon}"
    req = urllib.request.Request(points_url, headers={"User-Agent": "AgentHeartbeat/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        points_data = json.loads(resp.read().decode("utf-8"))

    grid_url = points_data["properties"]["forecastHourly"]
    req2 = urllib.request.Request(grid_url, headers={"User-Agent": "AgentHeartbeat/1.0"})
    with urllib.request.urlopen(req2, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _format_current(data: dict, lat: str, lon: str) -> str:
    props = data.get("properties", {})
    periods = props.get("periods", [])
    now = periods[0] if periods else {}

    temp = now.get("temperature", "unknown")
    unit = now.get("temperatureUnit", "F")
    wind = now.get("windSpeed", "unknown")
    condition = now.get("shortForecast", "unknown")
    humidity = now.get("relativeHumidity", {}).get("value", "unknown")
    if isinstance(humidity, int):
        humidity = f"{humidity}%"

    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"Weather at {lat},{lon} — {now_ts}",
        "",
        f"Condition: {condition}",
        f"Temperature: {temp}°{unit}",
        f"Wind: {wind}",
        f"Humidity: {humidity}",
        "",
    ]
    if len(periods) > 1:
        lines.append("Next periods:")
        for p in periods[1:6]:
            lines.append(
                f"  {p.get('name', '')}: {p.get('temperature', '?')}°{p.get('temperatureUnit','F')} — {p.get('shortForecast', '')}"
            )

    return "\n".join(lines)


def _skip(detail: str) -> dict:
    return {"ok": False, "status": "complete", "content": "",
            "category": CATEGORY, "proactive": False, "detail": detail}