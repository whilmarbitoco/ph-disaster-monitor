"""Disaster & hazard monitoring system for the Philippines.

Polls multiple APIs (USGS, GDACS, ReliefWeb) for earthquakes, typhoons,
floods, volcanic activity, tsunamis, and other natural disasters. Formats
alerts and delivers them via cron-integrated output.

Usage:
    python -m ph_disaster_monitor
    python -m ph_disaster_monitor --region davao --min-mag 3.5 --dry-run
    python -m ph_disaster_monitor --json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

__version__ = "1.0.0"

PHT = timezone(timedelta(hours=8))

# ── Region presets ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BoundingBox:
    """Geographic bounding box for event filtering."""
    minlat: float
    maxlat: float
    minlon: float
    maxlon: float

    def contains(self, lat: float, lon: float) -> bool:
        """Return True if (lat, lon) falls within this box."""
        return (self.minlat <= lat <= self.maxlat and
                self.minlon <= lon <= self.maxlon)

REGIONS: dict[str, BoundingBox] = {
    "philippines": BoundingBox(4.5, 21.0, 116.0, 127.5),
    "davao": BoundingBox(6.0, 9.0, 124.5, 127.5),
    "mindanao": BoundingBox(5.0, 9.5, 122.0, 127.5),
    "luzon": BoundingBox(12.5, 19.5, 119.0, 123.0),
    "visayas": BoundingBox(9.0, 13.0, 122.0, 126.0),
}

# ── Disaster type classification ─────────────────────────────────────────────

TYPE_EMOJI: dict[str, str] = {
    "earthquake": "🌋",
    "typhoon": "🌀",
    "flood": "🌊",
    "volcano": "🌋",
    "tsunami": "🌊",
    "landslide": "⛰️",
    "drought": "☀️",
    "fire": "🔥",
    "disaster": "⚠️",
}

# ── Data model ───────────────────────────────────────────────────────────────

@dataclass
class Alert:
    """Represents a single disaster event alert."""
    source: str
    alert_type: str
    severity: str
    title: str
    detail: str
    event_id: str
    magnitude: Optional[float] = None
    is_near_target: bool = False

    def emoji(self) -> str:
        """Return the emoji icon for this alert type."""
        return TYPE_EMOJI.get(self.alert_type, "⚠️")

# ── HTTP helper ───────────────────────────────────────────────────────────────

def fetch_json(url: str, timeout: int = 20) -> Optional[dict]:
    """Fetch a URL and parse JSON response.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON dict, or None on any error.
    """
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": f"ph-disaster-monitor/{__version__}"
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def fetch_text(url: str, timeout: int = 20) -> Optional[str]:
    """Fetch a URL and return raw text.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Response body string, or None on any error.
    """
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": f"ph-disaster-monitor/{__version__}"
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception:
        return None

# ── USGS Earthquake source ───────────────────────────────────────────────────

def check_usgs(
    bounds: BoundingBox,
    focus: BoundingBox,
    min_mag: float,
    hours: int,
    known_ids: set[str],
) -> tuple[list[Alert], set[str]]:
    """Fetch recent earthquakes from USGS.

    Args:
        bounds: Geographic bounds for the query.
        focus: Smaller bounds for "near you" tagging.
        min_mag: Minimum magnitude threshold.
        hours: Lookback window in hours.
        known_ids: Set of already-reported event IDs.

    Returns:
        Tuple of (new alerts, updated known IDs set).
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query"
        f"?format=geojson&minmag={min_mag}"
        f"&minlat={bounds.minlat}&maxlat={bounds.maxlat}"
        f"&minlon={bounds.minlon}&maxlon={bounds.maxlon}"
        f"&starttime={start.strftime('%Y-%m-%dT%H:%M:%S')}"
        f"&endtime={now.strftime('%Y-%m-%dT%H:%M:%S')}"
    )
    data = fetch_json(url)
    if not data:
        return [], known_ids

    alerts = []
    for feat in data.get("features", []):
        eq_id = feat.get("id", "")
        if eq_id in known_ids:
            continue
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        lon, lat, depth = geom.get("coordinates", [0, 0, 0])
        mag = props.get("mag", 0.0)
        place = props.get("place", "Unknown location")
        time_ms = props.get("time", 0)

        if not bounds.contains(lat, lon) and not _mentions_philippines(place):
            known_ids.add(eq_id)
            continue

        eq_time = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)
        near = " 📍 NEAR TARGET" if focus.contains(lat, lon) else ""
        alerts.append(Alert(
            source="usgs",
            alert_type="earthquake",
            severity=_mag_label(mag),
            title=f"M{mag:.1f} Earthquake — {place}{near}",
            detail=f"Depth: {depth:.0f} km | {_fmt_time(eq_time)}",
            event_id=eq_id,
            magnitude=mag,
            is_near_target=bool(near),
        ))
        known_ids.add(eq_id)
    return alerts, known_ids

def _mentions_philippines(place: str) -> bool:
    """Check if a location string references the Philippines."""
    keywords = ["philippines", "luzon", "visayas", "mindanao",
                "davao", "manila", "cebu", "mindoro", "palawan"]
    return any(k in place.lower() for k in keywords)

def _mag_label(mag: float) -> str:
    """Return a severity label string for a given magnitude."""
    if mag >= 7.0:
        return "🔴 MAJOR"
    if mag >= 6.0:
        return "🟠 STRONG"
    if mag >= 5.0:
        return "🟡 MODERATE"
    if mag >= 4.0:
        return "🔵 LIGHT"
    return "⚪ MINOR"

# ── GDACS source ──────────────────────────────────────────────────────────────

def check_gdacs(
    known_ids: set[str],
    hours: int,
) -> tuple[list[Alert], set[str]]:
    """Fetch global disaster alerts from GDACS RSS.

    Covers earthquakes, tropical cyclones, floods, volcanic eruptions,
    droughts, and landslides.

    Args:
        known_ids: Set of already-reported GUIDs.
        hours: Lookback window (used to filter by date in RSS).

    Returns:
        Tuple of (new alerts, updated known IDs set).
    """
    url = "https://www.gdacs.org/xml/rss.xml"
    raw = fetch_text(url)
    if not raw:
        return [], known_ids

    alerts = []
    items = re.findall(r"<item>(.*?)</item>", raw, re.DOTALL)
    for item in items[:30]:
        title_m = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
        link_m = re.search(r"<link>(.*?)</link>", item, re.DOTALL)
        desc_m = re.search(r"<description>(.*?)</description>", item, re.DOTALL)
        guid_m = re.search(r"<guid>(.*?)</guid>", item, re.DOTALL)
        date_m = re.search(r"<pubDate>(.*?)</pubDate>", item, re.DOTALL)

        title = _xml_unescape(title_m.group(1).strip()) if title_m else ""
        link = link_m.group(1).strip() if link_m else ""
        desc = _xml_unescape(desc_m.group(1).strip()) if desc_m else ""
        guid = (guid_m.group(1).strip() if guid_m else link)

        if not guid or guid in known_ids:
            continue

        combined = (title + " " + desc).lower()
        if not any(k in combined for k in [
            "philippines", "luzon", "visayas", "mindanao",
            "davao", "manila", "cebu", "philippine", "mindoro",
        ]):
            known_ids.add(guid)
            continue

        alert_type = _classify_gdacs(title)
        if alert_type is None:
            known_ids.add(guid)
            continue

        # Skip if too old
        if date_m:
            pub_date = _parse_rfc822(date_m.group(1).strip())
            if pub_date and (datetime.now(timezone.utc) - pub_date) > timedelta(hours=hours):
                known_ids.add(guid)
                continue

        alerts.append(Alert(
            source="gdacs",
            alert_type=alert_type,
            severity=_gdacs_severity(title, desc),
            title=title,
            detail=desc[:250],
            event_id=guid,
        ))
        known_ids.add(guid)

    return alerts, known_ids


def _xml_unescape(s: str) -> str:
    """Unescape basic XML entities."""
    return (s.replace("&amp;", "&").replace("&lt;", "<")
             .replace("&gt;", ">").replace("&quot;", '"')
             .replace("&#39;", "'"))


def _classify_gdacs(title: str) -> Optional[str]:
    """Classify disaster type from GDACS title. Returns None to skip."""
    t = title.lower()
    if "cyclone" in t or "typhoon" in t or "tropical" in t:
        return "typhoon"
    if "flood" in t:
        return "flood"
    if "volcan" in t:
        return "volcano"
    if "earthquake" in t:
        return "earthquake"
    if "tsunami" in t:
        return "tsunami"
    if "drought" in t:
        return "drought"
    if "landslide" in t:
        return "landslide"
    return None


def _gdacs_severity(title: str, desc: str) -> str:
    """Map GDACS alert level to severity label."""
    combined = (title + " " + desc).lower()
    if "red" in combined:
        return "🔴 EXTREME"
    if "orange" in combined:
        return "🟠 SEVERE"
    if "green" in combined:
        return "🟡 ALERT"
    return "🔵 ALERT"


def _parse_rfc822(date_str: str) -> Optional[datetime]:
    """Parse an RFC 822 date string. Returns None on failure."""
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return None

# ── ReliefWeb source ─────────────────────────────────────────────────────────

def check_reliefweb(
    known_ids: set[str],
) -> tuple[list[Alert], set[str]]:
    """Fetch recent Philippines disaster reports from ReliefWeb API.

    Args:
        known_ids: Set of already-reported report IDs.

    Returns:
        Tuple of (new alerts, updated known IDs set).
    """
    url = (
        "https://api.reliefweb.int/v1/reports"
        "?appname=ph-disaster-monitor&limit=15&sort[]:created:desc"
        "&filter[field]=country&filter[value]=philippines"
    )
    data = fetch_json(url)
    if not data:
        return [], known_ids

    alerts = []
    for item in data.get("data", []):
        fid = str(item.get("id", ""))
        if not fid or fid in known_ids:
            continue
        fields = item.get("fields", {})
        title = fields.get("title", "Unknown event")
        date = fields.get("created", "")
        body = fields.get("body", "")[:250]

        alerts.append(Alert(
            source="reliefweb",
            alert_type=_classify_reliefweb(title + " " + body),
            severity="🔵 ALERT",
            title=title,
            detail=f"{_fmt_time_str(date)} | {body}",
            event_id=fid,
        ))
        known_ids.add(fid)

    return alerts, known_ids


def _classify_reliefweb(text: str) -> str:
    """Classify disaster type from ReliefWeb text."""
    t = text.lower()
    if "typhoon" in t or "cyclone" in t or "tropical" in t or "storm surge" in t:
        return "typhoon"
    if "flood" in t or "flooding" in t:
        return "flood"
    if "earthquake" in t:
        return "earthquake"
    if "volcan" in t or "eruption" in t:
        return "volcano"
    if "tsunami" in t:
        return "tsunami"
    if "landslide" in t or "mudslide" in t:
        return "landslide"
    if "fire" in t or "explosion" in t:
        return "fire"
    return "disaster"

# ── Deduplication ────────────────────────────────────────────────────────────

def deduplicate(alerts: list[Alert]) -> list[Alert]:
    """Remove duplicate alerts across sources.

    Strategy:
        1. Title-based dedup (first 60 chars).
        2. For earthquakes: USGS is authoritative. Suppress non-USGS
           entries whose magnitude matches a USGS event (±0.0 to ±0.1).

    Args:
        alerts: Raw combined alerts from all sources.

    Returns:
        Deduplicated alert list, sorted by magnitude (highest first) then
        by source priority (usgs > gdacs > reliefweb).
    """
    # Step 1: Title dedup
    seen: set[str] = set()
    deduped = []
    for a in alerts:
        key = a.title[:60].lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(a)

    # Step 2: Suppress non-USGS earthquake duplicates
    usgs_mags: set[float] = set()
    for a in deduped:
        if a.alert_type == "earthquake" and a.source == "usgs" and a.magnitude is not None:
            usgs_mags.add(round(a.magnitude, 1))

    SOURCE_PRIORITY = {"usgs": 0, "gdacs": 1, "reliefweb": 2}
    final = []
    for a in deduped:
        if a.alert_type == "earthquake" and a.source != "usgs":
            mag_match = re.search(r"Magnitude\s+(\d+\.\d+)M", a.title)
            if not mag_match:
                mag_match = re.search(r"\bM(\d+\.\d+)", a.title)
            if mag_match and round(float(mag_match.group(1)), 1) in usgs_mags:
                continue
        final.append(a)

    final.sort(key=lambda a: (
        -(a.magnitude or 0.0),
        SOURCE_PRIORITY.get(a.source, 9),
    ))
    return final

# ── Output formatting ────────────────────────────────────────────────────────

SEPARATOR = "─" * 55

def format_text(alerts: list[Alert]) -> str:
    """Format alerts as Telegram-compatible markdown text.

    Args:
        alerts: Deduplicated list of alerts.

    Returns:
        Formatted multi-line string ready for delivery.
    """
    lines = ["🚨 **DISASTER ALERT — Philippines** 🚨", ""]
    for a in alerts:
        lines.append(f"{a.emoji()} {a.severity} **{a.title}**")
        if a.detail:
            lines.append(f"└ {a.detail}")
        lines.append("")
    lines.append(SEPARATOR)
    lines.append("")
    lines.append("_Stay alert. Follow local authorities' advisories._")
    lines.append("_Data: USGS · GDACS · ReliefWeb_")
    return "\n".join(lines)


def format_json(alerts: list[Alert]) -> str:
    """Format alerts as a JSON string.

    Args:
        alerts: Deduplicated list of alerts.

    Returns:
        JSON string with alert array and metadata.
    """
    payload = {
        "version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(alerts),
        "alerts": [
            {
                "source": a.source,
                "type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "detail": a.detail,
                "id": a.event_id,
                "magnitude": a.magnitude,
                "near_target": a.is_near_target,
            }
            for a in alerts
        ],
    }
    return json.dumps(payload, indent=2)

# ── State persistence ────────────────────────────────────────────────────────

def load_state(state_file: Path) -> set[str]:
    """Load known event IDs from state file.

    Args:
        state_file: Path to the JSON state file.

    Returns:
        Set of known event ID strings.
    """
    if state_file.exists():
        try:
            return set(json.loads(state_file.read_text()))
        except Exception:
            return set()
    return set()


def save_state(state_file: Path, ids: set[str]) -> None:
    """Persist known event IDs to state file.

    Args:
        state_file: Path to the JSON state file.
        ids: Set of event IDs to persist.
    """
    state_file.write_text(json.dumps(list(ids)))

# ── Time formatting helpers ──────────────────────────────────────────────────

def _fmt_time(utc_dt: datetime) -> str:
    """Format a UTC datetime as PHT string."""
    return utc_dt.astimezone(PHT).strftime("%b %d, %Y %I:%M %p PHT")


def _fmt_time_str(iso_str: str) -> str:
    """Format an ISO date string as PHT string."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone(PHT).strftime("%b %d %I:%M %p PHT")
    except Exception:
        return iso_str[:16]

# ── Main orchestrator ────────────────────────────────────────────────────────

def run(
    bounds: Optional[BoundingBox] = None,
    focus: Optional[BoundingBox] = None,
    min_mag: float = 4.0,
    hours: int = 3,
    state_file: Optional[Path] = None,
    json_output: bool = False,
) -> str:
    """Execute the full monitoring pipeline.

    Fetches from all sources, deduplicates, and formats output.

    Args:
        bounds: Geographic bounds (defaults to Philippines).
        focus: "Near target" bounds (defaults to same as bounds).
        min_mag: Minimum earthquake magnitude.
        hours: Lookback window in hours.
        state_file: Path to state file (auto-generated if None).
        json_output: If True, return JSON instead of text.

    Returns:
        Formatted alert string, or empty string if no new events.
    """
    if bounds is None:
        bounds = REGIONS["philippines"]
    if focus is None:
        focus = bounds
    if state_file is None:
        state_file = Path(__file__).resolve().parent.parent / ".disaster_state.json"

    known_ids = load_state(state_file)
    all_alerts: list[Alert] = []

    # Fetch from all sources
    usgs_alerts, known_ids = check_usgs(bounds, focus, min_mag, hours, known_ids)
    all_alerts.extend(usgs_alerts)

    gdacs_alerts, known_ids = check_gdacs(known_ids, hours)
    all_alerts.extend(gdacs_alerts)

    rw_alerts, known_ids = check_reliefweb(known_ids)
    all_alerts.extend(rw_alerts)

    save_state(state_file, known_ids)

    # Deduplicate and format
    alerts = deduplicate(all_alerts)

    if not alerts:
        return ""

    if json_output:
        return format_json(alerts)
    return format_text(alerts)


# ── CLI entry point ──────────────────────────────────────────────────────────

def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        prog="ph-disaster-monitor",
        description="Disaster & hazard monitor for the Philippines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s                           # Default: Philippines-wide, text output
  %(prog)s --region davao            # Davao Region focus
  %(prog)s --min-mag 3.5 --hours 6   # Lower threshold, wider window
  %(prog)s --dry-run                 # Print output, skip state update
  %(prog)s --json                    # Machine-readable JSON output
  %(prog)s --region mindanao --json --state /tmp/test_state.json
        """,
    )
    parser.add_argument(
        "--region", choices=sorted(REGIONS.keys()),
        default="philippines",
        help="Geographic region preset (default: philippines)",
    )
    parser.add_argument(
        "--min-mag", type=float, default=4.0,
        help="Minimum earthquake magnitude (default: 4.0)",
    )
    parser.add_argument(
        "--hours", type=int, default=3,
        help="Lookback window in hours (default: 3)",
    )
    parser.add_argument(
        "--state", type=Path, default=None,
        help="Path to state file (default: .disaster_state.json near project root)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON instead of formatted text",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run and print output without saving state",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point. Returns exit code 0 (success/silent) or 1 (error)."""
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    bounds = REGIONS[args.region]
    # Only set focus for sub-national regions; country-wide has no "near" tag
    focus = bounds if args.region != "philippines" else BoundingBox(0, 0, 0, 0)
    state_file = args.state

    if args.dry_run:
        # In dry-run, use a temp state file that gets discarded
        import tempfile
        state_file = Path(tempfile.mktemp(suffix=".json"))

    try:
        output = run(
            bounds=bounds,
            focus=focus,
            min_mag=args.min_mag,
            hours=args.hours,
            state_file=state_file,
            json_output=args.json,
        )
    except Exception:
        logging.exception("Pipeline failed")
        return 1

    if not output:
        return 0

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
