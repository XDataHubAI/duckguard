# Installation

## Requirements

- Python 3.10 or higher
- No system dependencies required

## Basic Install

```bash
pip install duckguard
```

This installs DuckGuard with its core dependencies: DuckDB, Typer, Rich, PyArrow, Pydantic, and PyYAML.

## Optional Features

Install additional features as needed:

=== "Statistical Tests"
    ```bash
    pip install 'duckguard[statistics]'
    ```
    Adds scipy for distributional checks (normality tests, KS test, chi-square).

=== "Reports"
    ```bash
    pip install 'duckguard[reports]'
    ```
    Adds Jinja2 and WeasyPrint for HTML/PDF report generation.

=== "Database Connectors"
    ```bash
    # Individual databases
    pip install 'duckguard[postgres]'
    pip install 'duckguard[snowflake]'
    pip install 'duckguard[bigquery]'
    pip install 'duckguard[databricks]'
    pip install 'duckguard[mysql]'
    pip install 'duckguard[redshift]'
    pip install 'duckguard[oracle]'
    pip install 'duckguard[mongodb]'
    pip install 'duckguard[kafka]'

    # All databases at once
    pip install 'duckguard[databases]'
    ```

=== "Airflow"
    ```bash
    pip install 'duckguard[airflow]'
    ```

=== "Everything"
    ```bash
    pip install 'duckguard[all]'
    ```

## Development Install

```bash
git clone https://github.com/XDataHubAI/duckguard.git
cd duckguard
pip install -e ".[dev]"
```

## Verify Installation

```bash
duckguard --version
```

```python
import duckguard
print(duckguard.__version__)
```

## Next Steps

- [Quickstart →](quickstart.md) — Validate your first dataset
- [Why DuckGuard →](why-duckguard.md) — See how it compares
