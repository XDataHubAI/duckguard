# CLI Reference

DuckGuard provides a full-featured command-line interface powered by Typer and Rich.

## Installation

```bash
pip install duckguard
```

## Commands

### `duckguard check`

Run data quality checks on a data source.

```bash
duckguard check <source> [options]
```

| Option | Description |
|--------|-------------|
| `--config`, `-c` | Path to duckguard.yaml rules file |
| `--table`, `-t` | Table name (for databases) |
| `--not-null`, `-n` | Columns that must not be null (repeatable) |
| `--unique`, `-u` | Columns that must be unique (repeatable) |
| `--output`, `-o` | Output file (JSON) |
| `--verbose`, `-V` | Verbose output |

```bash
# Quick checks
duckguard check data.csv
duckguard check data.csv --not-null id --unique email

# YAML rules
duckguard check data.csv --config duckguard.yaml

# Database
duckguard check postgres://localhost/db --table orders

# Save results
duckguard check data.csv --output results.json
```

Exit code: `0` if all checks pass, `1` if any fail.

---

### `duckguard discover`

Analyze data and auto-generate validation rules.

```bash
duckguard discover <source> [options]
```

| Option | Description |
|--------|-------------|
| `--table`, `-t` | Table name |
| `--output`, `-o` | Output file for rules (YAML) |
| `--format`, `-f` | Output format: yaml, python |

```bash
duckguard discover data.csv
duckguard discover data.csv --output duckguard.yaml
```

---

### `duckguard profile`

Profile a dataset — statistics, patterns, quality scores.

```bash
duckguard profile <source> [options]
```

| Option | Description |
|--------|-------------|
| `--table`, `-t` | Table name |
| `--deep`, `-d` | Enable deep profiling (distributions, outliers) |
| `--format`, `-f` | Output format: table (default), json |
| `--output`, `-o` | Output file (JSON) |

```bash
duckguard profile data.csv
duckguard profile data.csv --deep
duckguard profile data.csv --format json -o profile.json
```

---

### `duckguard contract`

Manage data contracts.

```bash
duckguard contract <action> <source> [options]
```

**Actions:** `generate`, `validate`, `diff`

| Option | Description |
|--------|-------------|
| `--contract`, `-c` | Contract file path |
| `--output`, `-o` | Output file |
| `--strict` | Strict validation mode |

```bash
# Generate from data
duckguard contract generate data.csv --output orders.contract.yaml

# Validate data against contract
duckguard contract validate data.csv --contract orders.contract.yaml

# Compare two versions
duckguard contract diff old.contract.yaml new.contract.yaml
```

---

### `duckguard anomaly`

Detect anomalies in data.

```bash
duckguard anomaly <source> [options]
```

| Option | Description |
|--------|-------------|
| `--method`, `-m` | Method: zscore (default), iqr, percent_change, baseline, ks_test |
| `--threshold` | Detection threshold |
| `--column`, `-c` | Specific columns (repeatable) |
| `--learn-baseline`, `-L` | Learn and store baseline |

```bash
duckguard anomaly data.csv
duckguard anomaly data.csv --method iqr --threshold 2.0
duckguard anomaly data.csv --column amount --column quantity
duckguard anomaly data.csv --learn-baseline
duckguard anomaly data.csv --method baseline
```

---

### `duckguard report`

Generate HTML or PDF quality reports.

```bash
duckguard report <source> [options]
```

| Option | Description |
|--------|-------------|
| `--config`, `-c` | YAML rules file |
| `--format`, `-f` | html (default), pdf |
| `--output`, `-o` | Output file |
| `--title` | Report title |
| `--store`, `-s` | Store results in history |
| `--trends` | Include trend charts |
| `--dark-mode` | auto, light, dark |
| `--logo` | Logo URL for header |

```bash
duckguard report data.csv --output report.html
duckguard report data.csv --format pdf --output report.pdf
duckguard report data.csv --store --trends --title "Daily Report"
```

---

### `duckguard freshness`

Check data freshness.

```bash
duckguard freshness <source> [options]
```

| Option | Description |
|--------|-------------|
| `--column`, `-c` | Timestamp column |
| `--max-age`, `-m` | Max age: 1h, 6h, 24h, 7d (default: 24h) |
| `--format`, `-f` | table (default), json |

```bash
duckguard freshness data.csv
duckguard freshness data.csv --max-age 6h
duckguard freshness data.csv --column updated_at
```

---

### `duckguard schema`

Track schema evolution.

```bash
duckguard schema <source> [options]
```

| Option | Description |
|--------|-------------|
| `--action`, `-a` | show, capture, history, changes |
| `--format`, `-f` | table, json |
| `--limit`, `-l` | Number of results |

```bash
duckguard schema data.csv
duckguard schema data.csv --action capture
duckguard schema data.csv --action history
duckguard schema data.csv --action changes
```

---

### `duckguard history`

Query historical validation results.

```bash
duckguard history [source] [options]
```

| Option | Description |
|--------|-------------|
| `--last`, `-l` | Time period: 7d, 30d, 90d |
| `--format`, `-f` | table, json |
| `--trend`, `-t` | Show trend analysis |

```bash
duckguard history
duckguard history data.csv --last 7d
duckguard history data.csv --trend
```

---

### `duckguard info`

Display information about a data source.

```bash
duckguard info <source> [--table TABLE]
```

```bash
duckguard info data.csv
duckguard info postgres://localhost/db --table users
```

---

### Global Options

| Option | Description |
|--------|-------------|
| `--version`, `-v` | Show version |
| `--help` | Show help |
