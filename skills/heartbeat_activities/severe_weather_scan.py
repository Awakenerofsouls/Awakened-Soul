"""
Heartbeat activity: severe_weather_scan

Check NOAA for active weather alerts in the agent's region.
Defaults to Pagosa Springs, CO. If no alerts, returns a brief "all clear" entry.

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


CATEGORY = "severe_weather_scan"
DEFAULT_LAT = "37.2678"
DEFAULT_LON = "-107.3897"


def run(state: dict) -> dict:
    workspace = Path(state.get("WORKSPACE", "~/.openclaw/workspace"))
    lat = state.get("WEATHER_LAT", DEFAULT_LAT)
    lon = state.get("WEATHER_LON", DEFAULT_LON)

    print(f"[heartbeat] severe_weather_scan: {lat},{lon}")

    try:
        alerts = _fetch_alerts(lat, lon)
    except Exception as e:
        log_activity("severe_weather_scan", f"NOAA failed: {e}", salience=0.3, tags="error,weather")
        return _skip(f"noaa error: {e}")

    content = _format_alerts(alerts, lat, lon)

    write_to_journal(category="severe_weather_scan", content=content,
                    workspace=workspace, state=state)

    has_alerts = bool(alerts)
    return {
        "ok": True,
        "status": "complete",
        "content": content,
        "category": CATEGORY,
        "proactive": has_alerts,
        "detail": f"{len(alerts)} alert(s) found for {lat},{lon}",
    }


def _fetch_alerts(lat: str, lon: str) -> list:
    """Fetch active alerts from NWS API filtered to the point's zone."""
    # First get the zone from points endpoint
    points_url = f"https://api.weather.gov/points/{lat},{lon}"
    req = urllib.request.Request(points_url, headers={"User-Agent": "AgentHeartbeat/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        points_data = json.loads(resp.read().decode("utf-8"))

    zone_id = points_data["properties"]["forecastZone"]  # e.g. " zones/COZ003"
    zone_code = zone_id.split("/")[-1]  # "COZ003"

    alerts_url = f"https://api.weather.gov/alerts/active?zone={zone_code}"
    req2 = urllib.request.Request(alerts_url, headers={"User-Agent": "AgentHeartbeat/1.0"})
    with urllib.request.urlopen(req2, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return data.get("features", [])


def _format_alerts(alerts: list, lat: str, lon: str) -> str:
    if not alerts:
        return f"All clear at {lat},{lon}. No active weather alerts."

    lines = [f"Weather alerts active — {lat},{lon}", ""]
    for a in alerts:
        props = a.get("properties", {})
        event = props.get("event", "Alert")
        headline = props.get("headline", "")
        severity = props.get("severity", "Unknown")
        onset = props.get("onset", "")
        expires = props.get("expires", "")
        description = props.get("description", "")[:400]

        lines.append(f"⚠ {event} — {severity}")
        if headline:
            lines.append(f"  {headline}")
        if onset:
            lines.append(f"  Starts: {onset}")
        if expires:
            lines.append(f"  Expires: {expires}")
        if description:
            lines.append(f"  {description}")
        lines.append("")
    return "\n".join(lines)


def _skip(detail: str) -> dict:
    return {"ok": False, "status": "complete", "content": "",
            "category": CATEGORY, "proactive": False, "detail": detail}