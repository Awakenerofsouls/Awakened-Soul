"""
Heartbeat activity: weather_forecast

Pull 7-day forecast from NOAA API.
Agent's location from state (WEATHER_LAT, WEATHER_LON) or default Pagosa Springs, CO.

Activity contract:
  Input:  state dict (WORKSPACE, WEATHER_LAT, WEATHER_LON)
  Output: {"ok": bool, "status": "complete",
           "content": str, "category": str, "proactive": bool, "detail": str}
"""

import json
import urllib.request
import random
from pathlib import Path

from .journal import write_to_journal
from .log import log_activity
SIGNAL_AFFINITY = {}


CATEGORY = "weather_forecast"
DEFAULT_LAT = "37.2678"
DEFAULT_LON = "-107.3897"


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    lat = state.get("WEATHER_LAT", DEFAULT_LAT)
    lon = state.get("WEATHER_LON", DEFAULT_LON)

    print(f"[heartbeat] weather_forecast: lat={lat}, lon={lon}")

    try:
        forecast = _get_forecast(lat, lon)
    except Exception as e:
        log_activity("weather_forecast", f"NOAA failed: {e}", salience=0.3, tags="error,weather")
        return _skip(f"noaa error: {e}")

    if not forecast:
        return _skip("no forecast returned")

    content = _format_forecast(forecast, lat, lon)

    write_to_journal(category="weather_forecast", content=content,
                    workspace=workspace, state=state)

    return {
        "ok": True,
        "status": "complete",
        "content": content,
        "category": CATEGORY,
        "proactive": random.random() < 0.12,
        "detail": f"7-day forecast for {lat},{lon}",
    }


def _get_forecast(lat: str, lon: str) -> dict:
    points_url = f"https://api.weather.gov/points/{lat},{lon}"
    req = urllib.request.Request(points_url, headers={"User-Agent": "AgentHeartbeat/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        points_data = json.loads(resp.read().decode("utf-8"))

    forecast_url = points_data["properties"]["forecast"]
    req2 = urllib.request.Request(forecast_url, headers={"User-Agent": "AgentHeartbeat/1.0"})
    with urllib.request.urlopen(req2, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _format_forecast(data: dict, lat: str, lon: str) -> str:
    props = data.get("properties", {})
    periods = props.get("periods", [])

    lines = [f"7-Day Forecast — {lat}, {lon}", ""]

    # Group by day (take day periods only, skip night)
    seen_days = set()
    count = 0
    for p in periods:
        name = p.get("name", "")
        # Skip night periods for cleaner output
        if "Night" in name:
            continue
        if count >= 7:
            break

        temp = p.get("temperature", "?")
        unit = p.get("temperatureUnit", "F")
        detail = p.get("detailedForecast", "")
        wind = p.get("windSpeed", "")
        condition = p.get("shortForecast", "")

        lines.append(f"{name}: {temp}°{unit} — {condition}")
        lines.append(f"  Wind: {wind}")
        lines.append(f"  {detail[:150]}")
        lines.append("")
        count += 1

    return "\n".join(lines)


def _skip(detail: str) -> dict:
    return {"ok": False, "status": "complete", "content": "",
            "category": CATEGORY, "proactive": False, "detail": detail}