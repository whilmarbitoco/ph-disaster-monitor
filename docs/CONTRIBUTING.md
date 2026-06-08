# Contributing

Thank you for your interest in improving the Philippines Disaster Monitor.

## How to Contribute

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes with tests
4. Run the test suite: `make test`
5. Run linting: `make lint`
6. Submit a pull request

## Code Style

- Python 3.11+ with type hints
- Google-style docstrings
- Line length: 100 characters
- Use `ruff` for linting and formatting
- Use `mypy --strict` for type checking

## Testing

```bash
# Run all tests
make test

# Run with coverage
pytest --cov=ph_disaster_monitor tests/
```

Tests use only stdlib (`unittest.mock`) — no network calls in test suite.

## Adding a New Data Source

1. Add a `check_<source>()` function returning `tuple[list[Alert], set[str]]`
2. Call it in `run()` and extend `all_alerts`
3. Add dedup rules in `deduplicate()` if needed
4. Add tests in `tests/test_sources.py`
5. Update this doc and `README.md`

## Reporting Issues

Open a GitHub issue with:
- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS
