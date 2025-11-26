.PHONY: help install install-dev setup test test-verbose lint format clean run dry-run

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package
	pip install -e .

install-dev:  ## Install the package with development dependencies
	pip install -e ".[dev]"
	playwright install chromium

setup: install-dev  ## Complete setup (install + playwright)
	@echo "Setup complete! Run 'make run' to test."

test:  ## Run tests
	pytest

test-verbose:  ## Run tests with verbose output
	pytest -v

test-coverage:  ## Run tests with coverage report
	pytest --cov=timesheet_bot --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

lint:  ## Run code linting
	flake8 timesheet_bot/ tests/

format:  ## Format code with black
	black timesheet_bot/ tests/

format-check:  ## Check code formatting without modifying
	black --check timesheet_bot/ tests/

clean:  ## Clean up generated files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:  ## Run with example CSV (dry-run)
	python -m timesheet_bot fill --csv data/week48.csv --dry-run

run-headful:  ## Run with example CSV in headful mode
	python -m timesheet_bot fill --csv data/week48.csv

run-headless:  ## Run with example CSV in headless mode
	python -m timesheet_bot fill --csv data/week48.csv --headless

run-verbose:  ## Run with verbose logging
	python -m timesheet_bot fill --csv data/week48.csv --verbose --dry-run

dry-run: run  ## Alias for 'run' (dry-run mode)
