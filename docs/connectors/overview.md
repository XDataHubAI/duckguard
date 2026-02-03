# Connectors Overview

DuckGuard connects to anything through a single `connect()` function. It auto-detects the source type.

## Quick Start

```python
from duckguard import connect

# Local files
data = connect("orders.csv")
data = connect("data/orders.parquet")
data = connect("reports/data.json")
data = connect("sheet.xlsx")

# Cloud storage
data = connect("s3://bucket/orders.parquet")
data = connect("gs://bucket/data.csv")
data = connect("az://container/data.parquet")

# Databases
data = connect("postgres://localhost/mydb", table="orders")
data = connect("mysql://localhost/mydb", table="users")
data = connect("sqlite:///local.db", table="events")
data = connect("snowflake://account/db", table="orders")

# DataFrames (pandas, polars, pyarrow)
data = connect(df)
```

## Supported Sources

### Files

| Format | Extensions | Guide |
|--------|-----------|-------|
| CSV | `.csv`, `.tsv` | [Files](files.md) |
| Parquet | `.parquet` | [Files](files.md) |
| JSON | `.json`, `.jsonl`, `.ndjson` | [Files](files.md) |
| Excel | `.xlsx`, `.xls` | [Files](files.md) |

### Cloud Storage

| Provider | Prefix | Guide |
|----------|--------|-------|
| AWS S3 | `s3://` | [Cloud Storage](cloud-storage.md) |
| Google Cloud Storage | `gs://` | [Cloud Storage](cloud-storage.md) |
| Azure Blob Storage | `az://`, `abfss://` | [Cloud Storage](cloud-storage.md) |

### Databases

| Database | Prefix | Extra |
|----------|--------|-------|
| PostgreSQL | `postgres://` | `pip install duckguard[postgres]` |
| MySQL | `mysql://` | `pip install duckguard[mysql]` |
| SQLite | `sqlite://` or `.db` | Built-in |
| Snowflake | `snowflake://` | `pip install duckguard[snowflake]` |
| BigQuery | `bigquery://` | `pip install duckguard[bigquery]` |
| Redshift | `redshift://` | `pip install duckguard[postgres]` |
| SQL Server | `mssql://` | `pip install duckguard[sqlserver]` |
| Databricks | `databricks://` | `pip install duckguard[databricks]` |
| Oracle | `oracle://` | `pip install duckguard[oracle]` |
| MongoDB | `mongodb://` | `pip install duckguard[mongodb]` |
| Kafka | `kafka://` | `pip install duckguard[kafka]` |

### Modern Formats

| Format | Guide |
|--------|-------|
| Delta Lake | [Modern Formats](modern-formats.md) |
| Apache Iceberg | [Modern Formats](modern-formats.md) |

### DataFrames

| Library | Detection |
|---------|-----------|
| pandas | Has `.shape` and `.columns` |
| polars | Has `__dataframe__` |
| pyarrow | Has `to_pandas` |

## Common Options

```python
# Database connections
data = connect("postgres://host/db", table="orders", schema="public")

# All connectors return a Dataset
print(data.row_count)
print(data.columns)
print(data.column_count)
```

## Custom Connectors

Register your own connector:

```python
from duckguard.connectors import register_connector, Connector

class MyConnector(Connector):
    @classmethod
    def can_handle(cls, source) -> bool:
        return str(source).startswith("mydb://")

    def connect(self, config):
        # Return a Dataset
        ...

register_connector(MyConnector)
```
