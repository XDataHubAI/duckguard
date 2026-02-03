# File Connectors

Connect to CSV, Parquet, JSON, and Excel files.

## Quick Start

```python
from duckguard import connect

# CSV
orders = connect("data/orders.csv")

# Parquet
orders = connect("data/orders.parquet")

# JSON / JSONL
events = connect("data/events.json")
logs = connect("data/logs.jsonl")

# Excel
report = connect("data/report.xlsx")
```

## CSV

DuckGuard uses DuckDB's CSV reader, which auto-detects delimiters, headers, and types.

```python
# Standard CSV
data = connect("data.csv")

# Tab-separated
data = connect("data.tsv")

# Custom options via DuckDB
data = connect("data.csv")
assert data.row_count > 0
```

**Auto-detected:** delimiter, header row, column types, quoting, encoding.

## Parquet

Parquet is the recommended format — it's fastest and preserves types.

```python
data = connect("data.parquet")

# Partitioned parquet (directory of files)
data = connect("data/year=2024/month=01/")
```

Parquet preserves exact types (integers, decimals, timestamps) without any parsing overhead.

## JSON

Supports standard JSON arrays and newline-delimited JSON (JSONL/NDJSON):

```python
# JSON array: [{"id": 1, ...}, {"id": 2, ...}]
data = connect("data.json")

# Newline-delimited JSON (one object per line)
data = connect("logs.jsonl")
data = connect("events.ndjson")
```

## Excel

```python
data = connect("report.xlsx")
data = connect("legacy.xls")
```

!!! note
    Excel support uses DuckDB's `spatial` extension. Large Excel files may be slower than CSV/Parquet.

## File Paths

DuckGuard accepts relative and absolute paths:

```python
# Relative to current directory
data = connect("data/orders.csv")

# Absolute path
data = connect("/home/user/data/orders.csv")

# Glob patterns (via DuckDB)
data = connect("data/*.parquet")
```

## Working with the Dataset

All file connectors return the same `Dataset` object:

```python
data = connect("orders.csv")

# Basic info
print(data.row_count)       # 10000
print(data.columns)         # ['id', 'amount', 'status', ...]
print(data.column_count)    # 5

# Access columns
print(data.amount.null_percent)
print(data.amount.min)
print(data.amount.max)

# Sample data
rows = data.head(5)
print(rows)

# Run validations
assert data.order_id.null_percent == 0
assert data.amount.between(0, 10000)
```

## Performance Tips

| Format | Read Speed | File Size | Type Safety |
|--------|-----------|-----------|-------------|
| **Parquet** | ⚡ Fastest | Small | Full |
| **CSV** | Fast | Large | Inferred |
| **JSON** | Moderate | Large | Inferred |
| **Excel** | Slowest | Medium | Inferred |

**Recommendation:** Convert CSV/JSON to Parquet for repeated validation runs.
