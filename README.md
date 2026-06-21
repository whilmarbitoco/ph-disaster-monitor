# 🌋 Philippines Disaster Monitor

[![Python](https://img.shields.io/badge/Python.12+-3776AB?logo=python&logoColor=white)](https://python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)](https://github.com/features/actions)

Real-time disaster and hazard monitoring for the Philippines. Polls multiple authoritative APIs and delivers formatted alerts via stdout (cron-compatible) or JSON. Zero external dependencies — pure Python stdlib.

## ✨ Highlights

- **Multi-Source Aggregation** — USGS (earthquakes), GDACS (cyclones, floods, volcanoes, droughts), ReliefWeb (NDRRMC/PAGASA reports)
- **Smart Deduplication** — USGS is authoritative for earthquakes; cross-source duplicates are automatically suppressed
- **Region Presets** — Philippines-wide, Luzon, Visayas, Mindanao, Davao
- **Dual Output** — Human-readable text (Telegram/markdown) or machine-readable JSON
- **Cron-Friendly** — Silent exit when no new events; state tracking prevents duplicate alerts
- **Zero Dependencies** — Pure Python 3.11+ stdlib, no pip install needed

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| APIs | USGS, GDACS, ReliefWeb |
| Output | stdout (text), JSON |
| Dependencies | None (stdlib only) |
| CI | GitHub Actions (lint, type-check, test) |

## 🚀 Quick Start

```bash
git clone https://github.com/whilmarbitoco/ph-disaster-monitor.git
cd ph-disaster-monitor

# Run with defaults (Philippines-wide, text output)
python -m ph_disaster_monitor

# Davao Region focus, lower magnitude threshold
python -m ph_disaster_monitor --region davao --min-mag 3.5

# JSON output for programmatic use
python -m ph_disaster_monitor --json
```

### Cron Setup

```cron
*/5 * * * * cd /opt/ph-disaster-monitor && python -m ph_disaster_monitor 2>/dev/null | your-delivery-script
```

## 📊 Data Sources

| Source | Events | URL |
|--------|--------|-----|
| USGS | Earthquakes | https://earthquake.usgs.gov |
| GDACS | Cyclones, floods, volcanoes, droughts | https://www.gdacs.org |
| ReliefWeb | Official disaster reports (NDRRMC, PAGASA) | https://reliefweb.int |

## 📄 License

MIT © [Whilmar Bitoco](https://github.com/whilmarbitoco)
