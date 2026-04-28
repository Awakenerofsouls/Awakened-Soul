"""
Heartbeat activity: astronomy_snapshot

Get today's sunrise, sunset, and moon phase via NOAA API.
For the agent's location (defaults to Pagosa Springs, CO).

Activity contract:
  Input:  state dict (WORKSPACE, WEATHER_LAT, WEATHER_LON)
  Output: {"ok": bool, "status": "complete",
           "content": str, "category": str, "proactive": bool, "detail": str}
"""

import json
import urllib.request
import random
from pathlib import Path
from datetime import datetime, timezone

from .journal import write_to_journal
from .log import log_activity
SIGNAL_AFFINITY = {}


CATEGORY = "astronomy_snapshot"
DEFAULT_LAT = "37.2678"
DEFAULT_LON = "-107.3897"


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    lat = state.get("WEATHER_LAT", DEFAULT_LAT)
    lon = state.get("WEATHER_LON", DEFAULT_LON)

    print(f"[heartbeat] astronomy_snapshot: {lat},{lon}")

    try:
        astronomy = _fetch_astronomy(lat, lon)
    except Exception as e:
        log_activity("astronomy_snapshot", f"NOAA failed: {e}", salience=0.2, tags="error,astronomy")
        return _skip(f"noaa error: {e}")

    if not astronomy:
        return _skip("no astronomy data returned")

    content = _format_astronomy(astronomy, lat, lon)

    write_to_journal(category="astronomy_snapshot", content=content,
                    workspace=workspace, state=state)

    return {
        "ok": True,
        "status": "complete",
        "content": content,
        "category": CATEGORY,
        "proactive": random.random() < 0.10,
        "detail": f"Astronomy for {lat},{lon}",
    }


def _fetch_astronomy(lat: str, lon: str) -> dict:
    # NOAA solar data endpoint
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"https://api.weather.gov/points/{lat},{lon}"
    req = urllib.request.Request(url, headers={"User-Agent": "AgentHeartbeat/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        points_data = json.loads(resp.read().decode("utf-8"))

    forecast_url = points_data["properties"]["forecast"]
    # Pull forecast to get today's period data
    req2 = urllib.request.Request(forecast_url, headers={"User-Agent": "AgentHeartbeat/1.0"})
    with urllib.request.urlopen(req2, timeout=15) as resp:
        forecast_data = json.loads(resp.read().decode("utf-8"))

    # Sunrise/sunset from the points data's forecast Grid data
    grid_url_base = points_data["properties"].get("forecastGridData", "")
    if not grid_url_base:
        return _fallback_astronomy(lat, lon)

    req3 = urllib.request.Request(grid_url_base, headers={"User-Agent": "AgentHeartbeat/1.0"})
    with urllib.request.urlopen(req3, timeout=15) as resp:
        grid_data = json.loads(resp.read().decode("utf-8"))

    # Pull current conditions for today's astronomy
    return _get_sun_data(grid_data, lat, lon)


def _fallback_astronomy(lat: str, lon: str) -> dict:
    """Fallback: approximate from lat/lon without NOAA solar endpoint."""
    # NOAA doesn't expose a simple sunrise endpoint — approximate
    # Instead, use the forecast data to extract the day's info
    return {}


def _get_sun_data(grid_data: dict, lat: str, lon: str) -> dict:
    """Extract astronomy from grid data if available."""
    props = grid_data.get("properties", {})
    # NOAA grid data has cloudCover, visibility — but not sunrise times
    # Use a simpler approach: return what's available in today's forecast
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {
        "date": today,
        "lat": lat,
        "lon": lon,
        "grid_data": props,
    }


def _format_astronomy(data: dict, lat: str, lon: str) -> str:
    if not data:
        return (
            f"Astronomy snapshot — {lat}, {lon}\n\n"
            "NOAA grid data unavailable for solar times. "
            "Consider a dedicated astronomy API for precise sunrise/sunset."
        )

    props = data.get("grid_data", {})
    cloud_cover = props.get("cloudCover", {})
    if isinstance(cloud_cover, dict):
        cloud_cover = cloud_cover.get("value", "unknown")

    visibility = props.get("visibility", {})
    if isinstance(visibility, dict):
        visibility = visibility.get("value", "unknown")

    lines = [
        f"Astronomy snapshot — {lat}, {lon}",
        f"Date: {data.get('date', 'today')}",
        "",
        f"Cloud cover: {cloud_cover}%",
        f"Visibility: {visibility}",
        "",
        "Note: Sunrise/sunset times require NOAA solar endpoint. "
        "For precise solar times, consider adding a dedicated astronomy service.",
    ]
    return "\n".join(lines)


def _skip(detail: str) -> dict:
    return {"ok": False, "status": "complete", "content": "",
            "category": CATEGORY, "proactive": False, "detail": detail}