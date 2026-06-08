# Setup Guide

## Requirements

- Python 3.11+
- Internet access (outbound HTTPS to USGS, GDACS, ReliefWeb)

## Installation

```bash
git clone https://github.com/youruser/ph-disaster-monitor.git
cd ph-disaster-monitor

# Optional: create a venv
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode (no external dependencies needed)
pip install -e ".[dev]"
```

## Configuration

### Region Presets

Edit `src/ph_disaster_monitor/__init__.py` to add custom regions:

```python
REGIONS["my_region"] = BoundingBox(
    minlat=7.0, maxlat=8.5,
    minlon=125.0, maxlon=126.5,
)
```

### State File

The state file tracks already-reported events to prevent duplicates.
Default location: `.disaster_state.json` in the project root.

For production, specify an explicit path:

```bash
python -m ph_disaster_monitor --state /var/lib/ph-monitor/state.json
```

### Environment Variables

None required. All configuration is via CLI flags.

## Running

```bash
# Basic run
python -m ph_disaster_monitor

# With options
python -m ph_disaster_monitor --region davao --min-mag 3.5 --hours 6

# JSON output
python -m ph_disaster_monitor --json

# Dry run (no state saved)
python -m ph_disaster_monitor --dry-run
```

## Cron Integration

Add to crontab (`crontab -e`):

```cron
# Check every 5 minutes, only output when new events exist
*/5 * * * * cd /path/to/ph-disaster-monitor && python -m ph_disaster_monitor --state /var/lib/ph-monitor/state.json 2>/dev/null
```

The script exits silently (no output) when there are no new events,
making it safe for cron — only new alerts produce output.

## Telegram Delivery

Pair with a bot or delivery script:

```bash
*/5 * * * * OUTPUT=$(python -m ph_disaster_monitor --state /var/lib/ph-monitor/state.json 2>/dev/null) && [ -n "$OUTPUT" ] && curl -s "https://api.telegram.org/bot<TOKEN>/sendMessage" -d "chat_id=<CHAT_ID>" -d "text=$OUTPUT" -d "parse_mode=Markdown"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No output | Normal — no new events in the lookback window |
| `fetch failed` | Check internet connectivity; USGS/GDACS may be down |
| Duplicate alerts | Delete the state file to reset: `rm .disaster_state.json` |
| Wrong region | Verify `--region` value matches a preset key |
