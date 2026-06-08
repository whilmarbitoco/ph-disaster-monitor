# Architecture

## Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  USGS API   │     │  GDACS RSS  │     │ ReliefWeb API│
│ (earthquake)│     │(multi-type) │     │  (reports)   │
└──────┬──────┘     └──────┬──────┘     └──────┬───────┘
       │                   │                    │
       ▼                   ▼                    ▼
┌──────────────────────────────────────────────────────┐
│                  Fetch Layer                          │
│  fetch_json() / fetch_text() — HTTP with UA header   │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│               Source Checkers                         │
│  check_usgs() / check_gdacs() / check_reliefweb()    │
│  — Filter by geography, time, Philippines relevance   │
│  — Return list[Alert] + update known_ids              │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│              Deduplication (deduplicate)              │
│  1. Title-based dedup (first 60 chars)               │
│  2. Earthquake cross-source: USGS authoritative       │
│     — Suppress GDACS quakes matching USGS magnitude   │
│  3. Sort by magnitude desc, then source priority      │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│              Output Formatting                        │
│  format_text() — Telegram/markdown                    │
│  format_json() — Machine-readable JSON                │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
                  stdout (cron picks up)
```

## State Management

- **State file**: JSON array of event IDs (`.disaster_state.json`)
- **Load**: At start of each `run()` call
- **Save**: After all sources are checked, before formatting
- **Purpose**: Prevents re-alerting on the same event across cron ticks

## Source Priority for Earthquakes

1. **USGS** — Authoritative. Always kept.
2. **GDACS** — Suppressed if magnitude matches a USGS event.
3. **ReliefWeb** — Kept (usually reports, not raw seismic data).

## Alert Data Model

```
Alert
├── source: str          # "usgs" | "gdacs" | "reliefweb"
├── alert_type: str      # "earthquake" | "typhoon" | "flood" | ...
├── severity: str        # "🔴 MAJOR" | "🟠 STRONG" | "🟡 MODERATE" | ...
├── title: str           # Human-readable headline
├── detail: str          # Depth, time, description
├── event_id: str        # Unique ID from source
├── magnitude: float?    # For earthquakes
└── is_near_target: bool # True if within focus bounds
```

## Region System

Regions are defined as `BoundingBox` presets:

| Preset | Coverage |
|--------|----------|
| philippines | Entire country (4.5–21°N, 116–127.5°E) |
| davao | Davao Region (6–9°N, 124.5–127.5°E) |
| mindanao | Mindanao island group |
| luzon | Luzon island group |
| visayas | Visayas island group |

The `focus` bounds (defaults to same as `bounds`) control the
"📍 NEAR TARGET" tag on earthquake alerts.
