# Changelog

## [1.0.0] — 2026-06-08

### Added
- Initial release
- USGS earthquake monitoring (M4.0+ Philippines)
- GDACS multi-hazard monitoring (cyclones, floods, volcanoes, droughts)
- ReliefWeb official disaster report integration
- Smart deduplication (title-based + cross-source earthquake suppression)
- Region presets: philippines, luzon, visayas, mindanao, davao
- Dual output: Telegram/markdown text and JSON
- State file for cron-compatible duplicate prevention
- CLI with argparse (`--region`, `--min-mag`, `--hours`, `--json`, `--dry-run`)
- Full type hints and docstrings
- Unit tests with mock fixtures
- CI workflow (ruff, mypy, pytest)
- Makefile for common tasks
