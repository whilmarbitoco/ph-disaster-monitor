.PHONY: install lint typecheck test test-verbose check clean run dry-run

install:
	pip install -e ".[dev]"

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

typecheck:
	mypy src/

test:
	pytest tests/ -q

test-verbose:
	pytest tests/ -v

check: lint typecheck test

clean:
	rm -rf .mypy_cache .pytest_cache __pycache__ .disaster_state.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

run:
	python -m ph_disaster_monitor

dry-run:
	python -m ph_disaster_monitor --dry-run

json:
	python -m ph_disaster_monitor --json --dry-run

davao:
	python -m ph_disaster_monitor --region davao --dry-run
