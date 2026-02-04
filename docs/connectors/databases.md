# Database Connectors

Connect to PostgreSQL, MySQL, SQLite, Snowflake, BigQuery, and more.

## Quick Start

```python
from duckguard import connect

# PostgreSQL
data = connect("postgres://user:pass@host:5432/mydb", table="orders")

# MySQL
data = connect("mysql://user:pass@host:3306/mydb", table="users")

# SQLite
data = connect("sqlite:///local.db", table="events")
data = connect("local.db", table="events")  # .db extension auto-detected
```

## PostgreSQL

```bash
pip install 'duckguard[postgres]'
```

```python
data = connect(
    "postgres://user:password@localhost:5432/mydb",
    table="orders",
    schema="public"
)

assert data.row_count > 0
assert data.order_id.null_percent == 0
```

## MySQL

```bash
pip install 'duckguard[mysql]'
```

```python
data = connect(
    "mysql://user:password@localhost:3306/mydb",
    table="users"
)
```

## SQLite

No extra dependencies needed — SQLite is built-in:

```python
data = connect("sqlite:///path/to/database.db", table="events")

# Auto-detected by file extension
data = connect("database.db", table="events")
data = connect("database.sqlite", table="events")
data = connect("database.sqlite3", table="events")
```

## Snowflake

```bash
pip install 'duckguard[snowflake]'
```

```python
data = connect(
    "snowflake://account/database",
    table="orders",
    schema="public"
)
```

## BigQuery

```bash
pip install 'duckguard[bigquery]'
```

```python
data = connect(
    "bigquery://project-id",
    table="orders",
    schema="dataset_name"
)
```

## Redshift

```bash
pip install 'duckguard[postgres]'
```

```python
data = connect(
    "redshift://cluster.redshift.amazonaws.com:5439/mydb",
    table="orders"
)
```

## SQL Server

```bash
pip install 'duckguard[sqlserver]'
```

```python
data = connect(
    "mssql://user:pass@host:1433/mydb",
    table="orders"
)
```

## Databricks

```bash
pip install 'duckguard[databricks]'
```

```python
data = connect(
    "databricks://workspace.databricks.com",
    table="orders"
)
```

## Microsoft Fabric

```bash
pip install 'duckguard[fabric]'
```

```python
# OneLake (Parquet/Delta in Lakehouse)
data = connect(
    "fabric://workspace/lakehouse/Tables/orders",
    token="eyJ..."
)

# SQL endpoint
data = connect(
    "fabric+sql://workspace-guid.datawarehouse.fabric.microsoft.com",
    table="orders",
    database="my_lakehouse",
    token="eyJ..."
)
```

## Oracle

```bash
pip install 'duckguard[oracle]'
```

```python
data = connect("oracle://user:pass@host:1521/mydb", table="orders")
```

## MongoDB

```bash
pip install 'duckguard[mongodb]'
```

```python
data = connect("mongodb://localhost:27017/mydb", table="orders")
data = connect("mongodb+srv://user:pass@cluster.mongodb.net/mydb", table="orders")
```

## Kafka

```bash
pip install 'duckguard[kafka]'
```

```python
data = connect("kafka://localhost:9092", table="orders-topic")
```

## Common Parameters

All database connectors support:

| Parameter | Description |
|-----------|-------------|
| `table` | Table name (required) |
| `schema` | Schema/namespace |
| `database` | Database name |

```python
data = connect(
    "postgres://localhost/mydb",
    table="orders",
    schema="analytics",
    database="warehouse"
)
```

## Install All

```bash
pip install 'duckguard[all]'
```

This installs drivers for all supported databases.
