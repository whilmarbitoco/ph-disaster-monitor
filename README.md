# 🌋 Philippines Disaster Monitor

Real-time disaster and hazard monitoring for the Philippines. Polls multiple
authoritative APIs and delivers formatted alerts via stdout (cron-compatible)
or JSON.

## Features

- **Multi-source**: USGS (earthquakes), GDACS (cyclones, floods, volcanoes, droughts),
  ReliefWeb (official NDRRMC/PAGASA reports)
- **Smart deduplication**: USGS is authoritative for earthquakes; cross-source
  duplicates are automatically suppressed
- **Region presets**: Philippines-wide, Luzon, Visayas, Mindanao, Davao
- **Dual output**: Human-readable text (Telegram/markdown) or machine-readable JSON
- **Cron-friendly**: Silent exit (no output) when no new events; state tracking
  prevents duplicate alerts
- **Zero dependencies**: Pure Python 3.11+ stdlib

## Quick Start

```bash
# Clone and enter the repo
git clone https://github.com/whilmarbitoco/ph-disaster-monitor.git
cd ph-disaster-monitor

# Run with defaults (Philippines-wide, text output)
python -m ph_disaster_monitor

# Davao Region focus, lower magnitude threshold
python -m ph_disaster_monitor --region davao --min-mag 3.5

# JSON output for programmatic use
python -m ph_disaster_monitor --json

# Dry run (print without saving state)
python -m ph_disaster_monitor --dry-run
```

## Cron Setup

Check every 5 minutes and forward output to Telegram via your bot:

```cron
*/5 * * * * cd /opt/ph-disaster-monitor && python -m ph_disaster_monitor 2>/dev/null | your-delivery-script
```

Or use the built-in state tracking to only emit new events:

```cron
*/5 * * * * python -m ph_disaster_monitor --state /var/lib/ph-monitor/state.json
```

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--region` | `philippines` | Region preset: philippines, luzon, visayas, mindanao, davao |
| `--min-mag` | `4.0` | Minimum earthquake magnitude (USGS) |
| `--hours` | `3` | Lookback window in hours |
| `--state` | auto | Path to state file (prevents duplicate alerts) |
| `--json` | false | Output as JSON instead of text |
| `--dry-run` | false | Run without saving state |
| `--version` | | Print version and exit |

## Output Example

```
🚨 DISASTER ALERT — Philippines 🚨

🌋 🟡 MODERATE M5.7 Earthquake — 54 km SSW of Sarangani, Philippines
└ Depth: 35 km | Jun 08, 2026 12:46 PM PHT

🌀 🟠 SEVERE Typhoon MAYMAK — Category 2, approaching Luzon
└ Wind: 155 km/h | Jun 08, 2026 02:00 PM PHT

───────────────────────────────────────────────────────

Stay alert. Follow local authorities' advisories.
Data: USGS · GDACS · ReliefWeb
```

## Project Structure

```
ph-disaster-monitor/
├── src/ph_disaster_monitor/   # Main package
│   ├── __init__.py            # Core module (all logic)
│   └── __main__.py            # CLI entry point
├── tests/                     # Unit tests
│   ├── conftest.py
│   ├── test_dedup.py
│   ├── test_classify.py
│   └── fixtures/              # Sample API responses
├── docs/
│   ├── SETUP.md               # Installation & configuration
│   ├── ARCHITECTURE.md        # Design & data flow
│   └── CONTRIBUTING.md        # How to contribute
├── .github/workflows/ci.yml   # CI: lint, type-check, test
├── pyproject.toml             # Project metadata & tool config
├── Makefile                   # Common tasks
├── LICENSE                    # MIT
└── README.md                  # This file
```

## Data Sources

| Source | Events | URL |
|--------|--------|-----|
| USGS | Earthquakes | https://earthquake.usgs.gov |
| GDACS | Cyclones, floods, volcanoes, droughts, earthquakes | https://www.gdacs.org |
| ReliefWeb | Official disaster reports (NDRRMC, PAGASA) | https://reliefweb.int |

## License

MIT — see [LICENSE](LICENSE).
